#!/usr/bin/env python3
"""scrap_and_pocess_data.py

Run the full ETL pipeline:
1. Execute every scraper defined in run_all_scrapers.py.
2. Merge and post-process the JSON outputs into MERGED_LISTINGS.json.
"""

from datetime import datetime
import os
from pathlib import Path

from run_all_scrapers import SCRAPER_MODULES, run_scraper
import merge_and_process


def _log(message: str) -> None:
    """Print a timestamped log message (ISO-8601)."""
    print(f"[{datetime.now().isoformat(timespec='seconds')}] {message}")


def run_all_scrapers() -> None:
    """Run every scraper module sequentially."""
    # Ensure per-site stats start from scratch on every pipeline run.
    try:
        import run_all_scrapers as ras
        ras.listing_counts.clear()
    except Exception:
        pass

    for module_name in SCRAPER_MODULES:
        run_scraper(module_name)
    _log("All scrapers finished.")


def main() -> None:
    """Run scraping stage followed by merge + post-processing stage."""
    # ------------------------------------------------------------------
    # Ensure working directory = project root so that every scraper writes
    # its output JSON next to its source code (repo root).  When the Flask
    # worker runs on a host like Render or PythonAnywhere the CWD can be
    # something like `/home` or the platform-specific app directory, which
    # causes scrapers to scatter their JSON files all over the place.  By
    # switching to the directory where *this* script resides we keep all
    # artefacts together and make merge_and_process find them reliably.
    # ------------------------------------------------------------------
    os.chdir(Path(__file__).resolve().parent)

    _log("Starting full scrape → process pipeline …")

    # 1️⃣ Scrape
    run_all_scrapers()

    # 2️⃣ Merge & post-process
    _log("Launching merge_and_process.main() …")
    merge_and_process.main()

    _log("Pipeline completed ✅")


if __name__ == "__main__":
    main() 