#!/usr/bin/env python3
"""
pipeline.py

Unified pipeline that:
1. Runs all scrapers sequentially
2. Merges and processes the JSON outputs into MERGED_LISTINGS.json
3. Cleans up individual JSON files

This combines the functionality from run_all_scrapers.py, merge_and_process.py, 
and scrap_and_pocess_data.py into one comprehensive script.
"""

import importlib
import time
import traceback
import json
import glob
import os
import sys
from datetime import datetime
from typing import List, Dict, Tuple, Set
from collections import defaultdict
from pathlib import Path

# Configuration
SCRAPER_MODULES = [
    "api_idnes",
    "api_bezrealitky", 
    "api_rbrno",
    "api_rhn",
    "api_bravis",
    "api_remax",
    "api_ud",
    "api_sreality",
]

ALLOWED_TYPES = {"2+kk", "2+1", "3+kk", "3+1", "N/A"}
PRICE_REQUEST_LABEL = "Price on request (probably)"
PRICE_WEIRD_LABEL = "Something weird"

# Global variables
listing_counts: dict[str, int] = {}


def _log(msg: str) -> None:
    """Print a message with an ISO-8601 timestamp."""
    print(f"[{datetime.now().isoformat(timespec='seconds')}] {msg}")


# =============================================================================
# SCRAPING FUNCTIONS
# =============================================================================

def run_scraper(module_name: str) -> None:
    """Import `module_name` and invoke its sole scrape_* function."""
    func_name = f"scrape_{module_name}"
    _log(f"Starting {func_name}() …")
    
    try:
        # Import from scrapers subdirectory where new API scrapers are located
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'scrapers'))
        module = importlib.import_module(module_name)
        scrape_func = getattr(module, func_name)
    except (ImportError, AttributeError):
        _log(f"Could not locate {func_name} in scrapers/{module_name} — skipping.")
        return
    finally:
        # Clean up path
        if os.path.join(os.path.dirname(__file__), 'scrapers') in sys.path:
            sys.path.remove(os.path.join(os.path.dirname(__file__), 'scrapers'))

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
            if os.path.exists(json_file):
                with open(json_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        rows = len(data)
        except Exception:
            rows = 0

        listing_counts[module_name] = rows
        _log(f"Finished {func_name}() in {elapsed:.1f} s -> {rows} rows.")


def run_all_scrapers() -> None:
    """Run every scraper module sequentially."""
    # Ensure per-site stats start from scratch on every pipeline run.
    listing_counts.clear()

    for module_name in SCRAPER_MODULES:
        run_scraper(module_name)
    
    # Pretty summary
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


# =============================================================================
# DATA PROCESSING FUNCTIONS
# =============================================================================

def load_all_listings_with_stats(json_files: List[str]) -> Tuple[List[Dict], Dict[str, int]]:
    """Load listings from all provided JSON files and track per-site counts."""
    all_listings: List[Dict] = []
    site_counts: Dict[str, int] = {}
    
    for file_path in json_files:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    # Extract site name from filename (e.g., "reality_idnes.json" -> "reality_idnes")
                    site_name = os.path.splitext(os.path.basename(file_path))[0]
                    site_counts[site_name] = len(data)
                    all_listings.extend(data)
                else:
                    print(f"[WARN] File {file_path} does not contain a list. Skipping.")
        except (json.JSONDecodeError, OSError) as e:
            print(f"[ERROR] Could not read {file_path}: {e}")
    
    return all_listings, site_counts


def count_listings_by_site(listings: List[Dict]) -> Dict[str, int]:
    """Count listings grouped by their source site."""
    counts = defaultdict(int)
    for listing in listings:
        source = listing.get("source", "unknown")
        counts[source] += 1
    return dict(counts)


def print_site_statistics(title: str, site_counts: Dict[str, int]) -> None:
    """Print formatted statistics for each site."""
    total = sum(site_counts.values())
    print(f"\n===== {title} =====")
    print(f"Total listings: {total}")
    print("Per-site breakdown:")
    
    # Sort sites by count (descending) for better readability
    sorted_sites = sorted(site_counts.items(), key=lambda x: x[1], reverse=True)
    
    for site, count in sorted_sites:
        print(f"  {site:15} : {count:4d} listings")
    
    if not site_counts:
        print("  (No listings found)")
    print("=" * (len(title) + 12))


def remove_duplicates(listings: List[Dict]) -> Tuple[List[Dict], int]:
    """Remove duplicate listings based on locality, flat type, size and price."""
    seen: Set[Tuple[str, str, str, str]] = set()
    deduped: List[Dict] = []
    dup_count: int = 0

    for listing in listings:
        key = (
            str(listing.get("locality", "")).strip().lower(),
            str(listing.get("type_of_flat", "")).strip().lower(),
            str(listing.get("size", "")).strip(),
            str(listing.get("price", "")).strip(),
        )

        if key in seen:
            dup_count += 1
            continue  # Skip duplicates
        seen.add(key)
        deduped.append(listing)

    return deduped, dup_count


def filter_by_flat_type(listings: List[Dict]) -> Tuple[List[Dict], int]:
    """Filter out listings whose flat type is not in ALLOWED_TYPES."""
    filtered: List[Dict] = []
    removed: int = 0

    for listing in listings:
        if listing.get("type_of_flat") in ALLOWED_TYPES:
            filtered.append(listing)
        else:
            removed += 1
    return filtered, removed


def adjust_prices(listings: List[Dict]) -> Tuple[int, int]:
    """Normalize price field according to rules."""
    cnt_request = 0
    cnt_weird = 0

    for listing in listings:
        price = listing.get("price")

        # Try to get numeric value
        price_num: int | None = None
        if isinstance(price, (int, float)):
            price_num = int(price)
        elif isinstance(price, str) and price.isdigit():
            price_num = int(price)

        if price_num is None:
            # Cannot interpret as number -> skip
            continue

        if price_num == 0:
            listing["price"] = PRICE_REQUEST_LABEL
            cnt_request += 1
        elif 0 < price_num < 3_000_000:
            listing["price"] = PRICE_WEIRD_LABEL
            cnt_weird += 1

    return cnt_request, cnt_weird


def assign_sequential_uids(listings: List[Dict]) -> None:
    """Assign unique, sequential UID values starting at 1."""
    for idx, listing in enumerate(listings, start=1):
        listing["uid"] = idx


def merge_and_process() -> None:
    """Merge all JSON files and process the data."""
    script_dir = os.path.dirname(os.path.abspath(__file__))

    # Gather all JSON files in the project directory except the output file
    json_files = [
        fp for fp in glob.glob(os.path.join(script_dir, "*.json"))
        if os.path.basename(fp) != "MERGED_LISTINGS.json"
    ]

    if not json_files:
        print("No JSON files found to merge.")
        return

    print(f"Found {len(json_files)} JSON files. Loading listings ...")
    listings, site_counts = load_all_listings_with_stats(json_files)
    original_total = len(listings)
    print(f"Loaded {original_total} listings in total.")

    print_site_statistics("Before Deduplication", site_counts)
    listings, duplicates_removed = remove_duplicates(listings)
    after_dedupe_total = len(listings)
    print(f"Removed {duplicates_removed} duplicate listings. Remaining: {after_dedupe_total}.")

    print_site_statistics("After Deduplication", count_listings_by_site(listings))
    listings, filtered_out = filter_by_flat_type(listings)
    final_total = len(listings)
    print(f"Filtered out {filtered_out} listings by flat type. Remaining: {final_total}.")

    # Adjust price labels as requested
    price_request_cnt, price_weird_cnt = adjust_prices(listings)

    # Ensure unique, sequential UID values
    assign_sequential_uids(listings)

    print_site_statistics("Final Results (After All Filtering)", count_listings_by_site(listings))

    # Write merged results
    output_path = os.path.join(script_dir, "MERGED_LISTINGS.json")

    try:
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(listings, f, ensure_ascii=False, indent=4)
    except OSError as e:
        print(f"[ERROR] Failed to write merged listings: {e}")

    # Print clean summary
    print("\n===== MERGE SUMMARY =====")
    print(f"Original listings: {original_total}")
    print(f"Listings after merge: {final_total}")
    print()
    print(f"Duplicates removed: {duplicates_removed}")
    print(f"Filtered out by flat type: {filtered_out}")
    print(f"Price set to '{PRICE_REQUEST_LABEL}': {price_request_cnt}")
    print(f"Price set to '{PRICE_WEIRD_LABEL}': {price_weird_cnt}")

    integrity_ok = original_total == (final_total + duplicates_removed + filtered_out)
    status = "OK ✅" if integrity_ok else "Mismatch ⚠️ (files deleted anyway)"
    print(f"Integrity check: {status}")
    if not integrity_ok:
        print(
            f"(orig={original_total}, merged={final_total}, dupes={duplicates_removed}, filtered={filtered_out})"
        )

    # Always remove individual JSON files to keep workspace clean
    deleted_files = 0
    for fp in json_files:
        try:
            os.remove(fp)
            deleted_files += 1
        except OSError as e:
            print(f"[ERROR] Failed to delete {fp}: {e}")
    print(f"Deleted {deleted_files} source JSON file(s).")

    print("=========================\n")


# =============================================================================
# MAIN PIPELINE
# =============================================================================

def main() -> None:
    """Run the complete scraping and processing pipeline."""
    # Ensure working directory = project root
    os.chdir(Path(__file__).resolve().parent)

    _log("Starting full scrape → process pipeline …")

    # Step 1: Run all scrapers
    run_all_scrapers()

    # Step 2: Merge & post-process
    _log("Launching merge and processing …")
    merge_and_process()

    _log("Pipeline completed ✅")


if __name__ == "__main__":
    main() 