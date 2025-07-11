from flask import Flask, render_template, send_from_directory, jsonify
import json
import re
from pathlib import Path

app = Flask(__name__)

# --------------------------------------------------
# Data loading and preprocessing
# --------------------------------------------------

# Path to the merged listings file. When deployed on Render.com both the web
# service and the worker share a persistent disk mounted at /data, so we place
# the JSON there. Falling back to the local file makes local development
# friction-less (no /data mount on developer machines).

DATA_PATH = Path(__file__).with_name("MERGED_LISTINGS.json")

# All known scraper sources - hardcoded list to always show all sources even if they return 0 listings
ALL_SCRAPER_SOURCES = [
    "reality_idnes",
    "bezrealitky", 
    "reality_brno",
    "reality_hn",
    "bravis",
    "remax",
    "ulov_domov",
    "sreality",
]


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


def _section_list(raw_listings, key):
    filt = SECTION_DEFS[key]

    def _sort(rec):
        price = rec.get("price_int")
        # invalid prices (None) should come last -> mark with 1; valid with 0.
        invalid_flag = 1 if price is None else 0
        # For valid prices, use negative price to get descending order (higher first).
        price_key = -price if price is not None else 0
        return (invalid_flag, price_key)

    return sorted((r for r in raw_listings if filt(r)), key=_sort)


# Compute available price buckets per section (sorted)
def _sorted_buckets(bucket_set: set[str]):
    # Separate numeric buckets (e.g. '7mil') and 'no-price'
    numeric = [b for b in bucket_set if b != "no-price"]
    numeric.sort(key=lambda x: int(x.replace("mil", "")), reverse=True)
    if "no-price" in bucket_set:
        numeric.append("no-price")
    return numeric


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
    # Load fresh data on each request
    raw_listings = _load_listings()
    
    # Build context with listings and bucket lists per section.
    context: dict[str, object] = {
        'title': 'Petra & Michal | Bytový Výběr'
    }

    # Generate section data and buckets from fresh data
    section_cache = {k: _section_list(raw_listings, k) for k in SECTION_DEFS}
    section_buckets = {k: _sorted_buckets({rec["bucket"] for rec in lst}) for k, lst in section_cache.items()}

    # Inject listings and bucket arrays
    for key in SECTION_DEFS:
        context[key] = section_cache[key]
        context[f"{key}_buckets"] = section_buckets[key]

    # Compute per-source counts - always show all known scrapers, even if they have 0 listings
    source_counts: dict[str, int] = {}
    
    # Map new API scraper source names back to old display names
    source_name_mapping = {
        "reality.idnes.cz": "reality_idnes",
        "bezrealitky.cz": "bezrealitky", 
        "reality-brno.net": "reality_brno",
        "reality.hn.cz": "reality_hn",
        "bravis.cz": "bravis",
        "remax-czech.cz": "remax",
        "ulov_domov": "ulov_domov",
        "sreality.cz": "sreality",
    }
    
    # Initialize all known sources with 0
    for source in ALL_SCRAPER_SOURCES:
        source_counts[source] = 0
    
    # Count actual listings per source with mapping
    for rec in raw_listings:
        actual_src = str(rec.get("source", "unknown"))
        # Map new source name to old display name
        display_src = source_name_mapping.get(actual_src, actual_src)
        
        if display_src in source_counts:
            source_counts[display_src] += 1
        else:
            # Handle unknown sources (shouldn't happen with proper scrapers)
            source_counts[display_src] = source_counts.get(display_src, 0) + 1

    # Add overall and per-site stats for footer display
    context["total_listings"] = len(raw_listings)
    context["source_counts"] = source_counts

    return render_template('index.html', **context)


# Name of the placeholder image residing in the assets folder.
_PLACEHOLDER_NAME = "image_did_not_load.png"

# NEW_CODE_START
# Name of the banner image that should be displayed at the top of the page.
_BANNER_NAME = "banner.png"

# Expose a simple endpoint that returns the banner image so the template
# can reference it via an absolute path ("/banner.png").
@app.route(f"/{_BANNER_NAME}")
def banner_img():
    """Serve the local banner image file for the top-of-page banner."""
    return send_from_directory(Path(__file__).parent / "assets", _BANNER_NAME)
# NEW_CODE_END

# Register a simple route that serves the placeholder file so templates can
# reference it via url_for('placeholder_img').
@app.route(f"/{_PLACEHOLDER_NAME}")
def placeholder_img():
    """Serve the local placeholder image file when an image fails to load."""
    return send_from_directory(Path(__file__).parent / "assets", _PLACEHOLDER_NAME)

# NEW_CODE_START
_WAITING_NAME = "waiting_image.png"  # change to GIF if available

@app.route(f"/{_WAITING_NAME}")
def waiting_img():
    """Serve the waiting overlay image (GIF/PNG)."""
    return send_from_directory(Path(__file__).parent / "assets", _WAITING_NAME)
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
        import pipeline  # unified pipeline module

        # Run pipeline
        pipeline.main()

        # After pipeline we can retrieve per-site counts calculated by
        # pipeline.listing_counts (populated during the scrape stage).
        try:
            counts = pipeline.listing_counts
            total = sum(counts.values())
        except Exception:
            counts = {}
            total = 0

        # Data will be fresh on next page load since index() calls _load_listings() each time

        return jsonify({"status": "done", "counts": counts, "total": total})
    except Exception as exc:  # noqa: BLE001 – return error details to client
        return (
            jsonify({"status": "error", "message": str(exc)}),
            500,
        )


if __name__ == '__main__':
    # Enable debug mode for development.
    app.run(debug=True) 