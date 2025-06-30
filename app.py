from flask import Flask, render_template, send_from_directory, jsonify
import json
import re
from pathlib import Path

app = Flask(__name__)

# --------------------------------------------------
# Data loading and preprocessing
# --------------------------------------------------

DATA_PATH = Path(__file__).with_name("MERGED_LISTINGS.json")


def _parse_size(val):
    """Return integer square-meter value or None."""
    try:
        return int(re.findall(r"\d+", str(val))[0])
    except (IndexError, ValueError):
        return None


def _parse_price(val):
    """Return integer CZK price or None if not parseable."""
    # Accept ints/floats directly
    if isinstance(val, (int, float)):
        return int(val)
    # Try to strip non-digit characters from strings like "4 500 000 Kč"
    if isinstance(val, str):
        digits = re.sub(r"[^0-9]", "", val)
        return int(digits) if digits else None
    return None


def _load_listings():
    if not DATA_PATH.exists():
        return []
    with DATA_PATH.open(encoding="utf-8") as fh:
        data = json.load(fh)
    for rec in data:
        rec["size_int"] = _parse_size(rec.get("size")) or 0
        rec["price_int"] = _parse_price(rec.get("price"))  # may be None if unknown
        # Determine bucket label (e.g. "7mil" or "no-price") used for filtering.
        if rec["price_int"] is None:
            rec["bucket"] = "no-price"
        else:
            mil_value = round(rec["price_int"] / 1_000_000, 1)
            rec["bucket"] = f"{int(mil_value)}mil"
        # Normalize location string to lowercase once for quick checks
        rec["_locality_lower"] = str(rec.get("locality", "")).lower()
    return data


RAW_LISTINGS = _load_listings()


# Section filters -----------------------------------------------------------

def _in_reckovice_medlanky(rec):
    loc = rec["_locality_lower"]
    return any(k in loc for k in ["řečkovice", "reckovice", "medlánky", "medlanky"])


def _by_type(type_str):
    return lambda r: r.get("type_of_flat") == type_str


SECTION_DEFS = {
    "reckovice_medlanky": _in_reckovice_medlanky,
    "flats_2kk": _by_type("2+kk"),
    "flats_2plus1": _by_type("2+1"),
    "flats_3kk": _by_type("3+kk"),
    "flats_3plus1": _by_type("3+1"),
}


def _section_list(key):
    filt = SECTION_DEFS[key]

    def _sort(rec):
        price = rec.get("price_int")
        # invalid prices (None) should come last -> mark with 1; valid with 0.
        invalid_flag = 1 if price is None else 0
        # For valid prices, use negative price to get descending order (higher first).
        price_key = -price if price is not None else 0
        return (invalid_flag, price_key)

    return sorted((r for r in RAW_LISTINGS if filt(r)), key=_sort)


# Pre-compute section data for faster rendering
SECTION_CACHE = {k: _section_list(k) for k in SECTION_DEFS}

# Compute available price buckets per section (sorted)
def _sorted_buckets(bucket_set: set[str]):
    # Separate numeric buckets (e.g. '7mil') and 'no-price'
    numeric = [b for b in bucket_set if b != "no-price"]
    numeric.sort(key=lambda x: int(x.replace("mil", "")), reverse=True)
    if "no-price" in bucket_set:
        numeric.append("no-price")
    return numeric

SECTION_BUCKETS = {k: _sorted_buckets({rec["bucket"] for rec in lst}) for k, lst in SECTION_CACHE.items()}

# -------------------------------------------------------------------------
# Data reloading helper
# -------------------------------------------------------------------------


def _refresh_data() -> None:
    """Reload MERGED_LISTINGS.json into in-memory caches after scraping."""
    global RAW_LISTINGS, SECTION_CACHE, SECTION_BUCKETS

    RAW_LISTINGS = _load_listings()
    SECTION_CACHE = {k: _section_list(k) for k in SECTION_DEFS}
    SECTION_BUCKETS = {
        k: _sorted_buckets({rec["bucket"] for rec in lst}) for k, lst in SECTION_CACHE.items()
    }


# -------------------------------------------------------------------------
# Jinja filters
# -------------------------------------------------------------------------


def _short_price(czk: int) -> str:
    """Return price as X,Y mil (one decimal, comma as decimal separator)."""
    try:
        mil_value = round(czk / 1_000_000, 1)
        # Convert 6.0 -> 6,0 but we may want omit trailing zero? keep 6,0 for consistency.
        formatted = f"{mil_value:.1f}".replace(".", ",")
        return f"{formatted} mil"
    except Exception:
        return str(czk)


# Register filter with Jinja
app.jinja_env.filters["short_price"] = _short_price

# -------------------------------------------------------------------------


@app.route('/')
def index():
    """Render the home page."""
    # Build context with listings and bucket lists per section.
    context: dict[str, object] = {
        'title': 'Petra & Michal | Bytový Výběr'
    }

    # Inject listings and bucket arrays
    for key in SECTION_DEFS:
        context[key] = SECTION_CACHE[key]
        context[f"{key}_buckets"] = SECTION_BUCKETS[key]

    # Add overall number of listings so the template can show it at the bottom.
    context["total_listings"] = len(RAW_LISTINGS)

    return render_template('index.html', **context)


# Name of the placeholder image residing in the project root.
_PLACEHOLDER_NAME = "image_did_not_load.png"

# NEW_CODE_START
# Name of the banner image that should be displayed at the top of the page.
_BANNER_NAME = "banner.png"

# Expose a simple endpoint that returns the banner image so the template
# can reference it via an absolute path ("/banner.png").
@app.route(f"/{_BANNER_NAME}")
def banner_img():
    """Serve the local banner image file for the top-of-page banner."""
    return send_from_directory(Path(__file__).parent, _BANNER_NAME)
# NEW_CODE_END

# Register a simple route that serves the placeholder file so templates can
# reference it via url_for('placeholder_img').
@app.route(f"/{_PLACEHOLDER_NAME}")
def placeholder_img():
    """Serve the local placeholder image file when an image fails to load."""
    return send_from_directory(Path(__file__).parent, _PLACEHOLDER_NAME)

# NEW_CODE_START
_WAITING_NAME = "waiting_image.png"  # change to GIF if available

@app.route(f"/{_WAITING_NAME}")
def waiting_img():
    """Serve the waiting overlay image (GIF/PNG)."""
    return send_from_directory(Path(__file__).parent, _WAITING_NAME)
# NEW_CODE_END

# -------------------------------------------------------------------------
# Data refresh (scraping) endpoint
# -------------------------------------------------------------------------

@app.post("/run-scrape")
def run_scrape_endpoint():
    """Run the full scraping + processing pipeline then return JSON status.

    This blocks until the pipeline finishes (≈60&nbsp;s). The browser can
    poll/await the response and show a notification afterwards.
    """
    try:
        import scrap_and_pocess_data  # local module with `main()` entry-point

        # Launch the full ETL pipeline (scrape → merge/process JSON).
        scrap_and_pocess_data.main()
        # Hot-reload in-memory data so newly merged JSON is served immediately.
        _refresh_data()
        return jsonify({"status": "done"})
    except Exception as exc:  # noqa: BLE001 – return error details to client
        return (
            jsonify({"status": "error", "message": str(exc)}),
            500,
        )


if __name__ == '__main__':
    # Enable debug mode for development.
    app.run(debug=True) 