#!/usr/bin/env python3
"""
run_all_scrapers.py

Execute every individual scraper in this project one after another. Each scraper
writes its own JSON file; this orchestrator simply ensures they are launched in
sequence and shows a timestamped log of progress.
"""

import importlib
import time
import traceback
from datetime import datetime

# List the scraper modules in the order we want to run them.
# Each module must expose a function named `scrape_<module>`.
SCRAPER_MODULES = [
    "reality_idnes",
    "bezrealitky",
    "reality_brno",
    "reality_hn",
    "bravis",
    "remax",
    "ulov_domov",
    "sreality",
]

# Hold per-site row counts so we can emit a clean summary at the very end
listing_counts: dict[str, int] = {}

def _log(msg: str) -> None:
    """Print a message with an ISO-8601 timestamp."""
    print(f"[{datetime.now().isoformat(timespec='seconds')}] {msg}")


def run_scraper(module_name: str) -> None:
    """Import `module_name` and invoke its sole scrape_* function."""
    func_name = f"scrape_{module_name}"
    _log(f"Starting {func_name}() …")
    try:
        module = importlib.import_module(module_name)
        scrape_func = getattr(module, func_name)
    except (ImportError, AttributeError):
        _log(f"Could not locate {func_name} in {module_name} — skipping.")
        return

    start_ts = time.time()
    try:
        scrape_func()
    except Exception:  # noqa: BLE001 broad except is fine for orchestration
        _log(f"Exception while running {func_name}():")
        traceback.print_exc()
    else:
        elapsed = time.time() - start_ts
        # After successful scrape attempt to count rows in the freshly
        # produced JSON file. If the file is missing or malformed we record 0.
        json_file = f"{module_name}.json"
        rows = 0
        try:
            import json, os

            if os.path.exists(json_file):
                with open(json_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        rows = len(data)
        except Exception:
            rows = 0

        listing_counts[module_name] = rows

        _log(f"Finished {func_name}() in {elapsed:.1f} s -> {rows} rows.")


if __name__ == "__main__":
    # Fresh start – drop any previous run's stats
    listing_counts.clear()
    for mod in SCRAPER_MODULES:
        run_scraper(mod)

    # Pretty summary -------------------------------------------------------
    _log("\n===== SCRAPE SUMMARY =====")
    total = 0
    for mod in SCRAPER_MODULES:
        cnt = listing_counts.get(mod, 0)
        total += cnt
        print(f"• {mod:12}: {cnt:4} ads")
    print("---------------------------")
    print(f"TOTAL          : {total:4} ads")
    print("===========================\n")

    _log("All scrapers completed.") 