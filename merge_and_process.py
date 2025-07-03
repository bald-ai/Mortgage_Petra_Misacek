import json
import glob
import os
from typing import List, Dict, Tuple, Set

ALLOWED_TYPES = {"2+kk", "2+1", "3+kk", "3+1", "N/A"}
PRICE_REQUEST_LABEL = "Price on request (probably)"
PRICE_WEIRD_LABEL = "Something weird"


def load_all_listings(json_files: List[str]) -> List[Dict]:
    """Load listings from all provided JSON files."""
    all_listings: List[Dict] = []
    for file_path in json_files:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    all_listings.extend(data)
                else:
                    print(f"[WARN] File {file_path} does not contain a list. Skipping.")
        except (json.JSONDecodeError, OSError) as e:
            print(f"[ERROR] Could not read {file_path}: {e}")
    return all_listings


def remove_duplicates(listings: List[Dict]) -> Tuple[List[Dict], int]:
    """Remove duplicate listings.

    A duplicate is defined as listing having the same locality/address, flat type,
    size and price.

    Returns
    -------
    Tuple[List[Dict], int]
        A tuple with the deduplicated listings and count of duplicates removed.
    """
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
    """Normalize price field according to rules.

    - If price == 0       -> "Price on request"
    - If 0 < price < 3M   -> "Something weird"

    Returns
    -------
    Tuple[int, int]
        Counts of how many entries were changed to request label and weird label
    """

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
    """Rewrite/assign uid so that every listing has a unique, sequential ID starting at 1."""
    for idx, listing in enumerate(listings, start=1):
        listing["uid"] = idx


def main():
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
    listings = load_all_listings(json_files)
    original_total = len(listings)
    print(f"Loaded {original_total} listings in total.")

    listings, duplicates_removed = remove_duplicates(listings)
    after_dedupe_total = len(listings)
    print(f"Removed {duplicates_removed} duplicate listings. Remaining: {after_dedupe_total}.")

    listings, filtered_out = filter_by_flat_type(listings)
    final_total = len(listings)
    print(f"Filtered out {filtered_out} listings by flat type. Remaining: {final_total}.")

    # Adjust price labels as requested
    price_request_cnt, price_weird_cnt = adjust_prices(listings)

    # Ensure unique, sequential UID values
    assign_sequential_uids(listings)

    # Determine destination: persistent disk at /data when present (Render.com),
    # else default to script directory for local runs.
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


if __name__ == "__main__":
    main() 