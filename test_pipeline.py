#!/usr/bin/env python3
"""
test_pipeline.py

Simple test pipeline that runs bravis and sreality scrapers,
then merges them into MERGED_LISTINGS.json and cleans up individual files.
"""

import subprocess
import sys
from merge_and_process import process_specific_files

def run_scraper(script_name):
    """Run a single scraper script."""
    print(f"Running {script_name}...")
    try:
        result = subprocess.run([sys.executable, script_name], 
                              capture_output=True, text=True, check=True)
        print(f"✅ {script_name} completed successfully")
        if result.stdout:
            print(f"Output: {result.stdout}")
    except subprocess.CalledProcessError as e:
        print(f"❌ {script_name} failed with error: {e}")
        if e.stderr:
            print(f"Error: {e.stderr}")
        raise

def main():
    """Run the test pipeline."""
    print("🚀 Starting test pipeline...")
    
    # Run scrapers
    run_scraper("bravis.py")
    run_scraper("sreality.py")
    
    # Merge and process
    print("📄 Merging JSON files...")
    process_specific_files(["bravis.json", "sreality.json"])
    
    print("✅ Test pipeline completed!")

if __name__ == "__main__":
    main() 