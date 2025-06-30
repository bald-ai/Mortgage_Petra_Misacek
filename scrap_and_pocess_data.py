#!/usr/bin/env python3
"""scrap_and_pocess_data.py

Run the full ETL pipeline:
1. Execute every scraper defined in run_all_scrapers.py.
2. Merge and post-process the JSON outputs into MERGED_LISTINGS.json.
"""

from datetime import datetime

from run_all_scrapers import SCRAPER_MODULES, run_scraper
import merge_and_process


def _log(message: str) -> None:
    """Print a timestamped log message (ISO-8601)."""
    print(f"[{datetime.now().isoformat(timespec='seconds')}] {message}")


def run_all_scrapers() -> None:
    """Run every scraper module sequentially."""
    for module_name in SCRAPER_MODULES:
        run_scraper(module_name)
    _log("All scrapers finished.")


def main() -> None:
    """Run scraping stage followed by merge + post-processing stage."""
    _log("Starting full scrape → process pipeline …")

    # 1️⃣ Scrape
    run_all_scrapers()

    # 2️⃣ Merge & post-process
    _log("Launching merge_and_process.main() …")
    merge_and_process.main()

    _log("Pipeline completed ✅")


if __name__ == "__main__":
    main() 