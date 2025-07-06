#!/usr/bin/env python3
"""
test_pipeline.py

Pipeline that runs all scrapers, then merges them into MERGED_LISTINGS.json 
and cleans up individual files.
"""

import subprocess
import sys
from merge_and_process import process_specific_files

# All scraper modules (matching run_all_scrapers.py)
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

def run_scraper(script_name):
    """Run a single scraper script."""
    print(f"Running {script_name}...")
    try:
        result = subprocess.run([sys.executable, f"{script_name}.py"], 
                              capture_output=True, text=True, check=True)
        print(f"✅ {script_name} completed successfully")
        if result.stdout:
            print(f"Output: {result.stdout}")
    except subprocess.CalledProcessError as e:
        print(f"❌ {script_name} failed with error: {e}")
        if e.stderr:
            print(f"Error: {e.stderr}")
        # Don't raise - continue with other scrapers even if one fails

def main():
    """Run the full pipeline."""
    print("🚀 Starting full scraper pipeline...")
    
    # Run all scrapers
    for module in SCRAPER_MODULES:
        run_scraper(module)
    
    # Merge and process all JSON files
    print("📄 Merging all JSON files...")
    json_files = [f"{module}.json" for module in SCRAPER_MODULES]
    process_specific_files(json_files)
    
    print("✅ Full pipeline completed!")

if __name__ == "__main__":
    main() 