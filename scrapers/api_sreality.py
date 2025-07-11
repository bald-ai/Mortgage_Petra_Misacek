import requests
import json
import math
import time
import re
from urllib.parse import urlparse, urlunparse, quote

def scrape_sreality_listings(output_filename):
    """
    Fetches listings from the Sreality API and formats them
    into the specified JSON structure.
    Now with post-fetch filtering for: min 50m², types 2+kk/2+1/3+kk/3+1.
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    api_url = "https://www.sreality.cz/api/cs/v2/estates"
    
    # Back to your original params + min size (to reduce raw results safely)
    params = {
        'category_main_cb': '1',                  # Apartments
        'category_type_cb': '1',                  # Sale
        'czk_price_summary_order2': '0|8000000',  # Your original price filter
        'locality_district_id': '72',             # Brno district
        'locality_region_id': '14',               # Brno region
        'usable_area_min': '50',                  # Min 50m² (API filter to reduce)
        'per_page': 60,                           # Back to original (fewer pages)
        'tms': int(time.time() * 1000)
    }

    all_listings_data = []
    uid_counter = 1
    skipped_count = 0  # Track skipped for debug

    try:
        # NEW: Print full API URL for debug (paste in browser to check)
        full_url = requests.Request('GET', api_url, params=params).prepare().url
        print(f"🔗 Debug: Full API URL: {full_url}\n   (Paste this in browser/Postman to see raw total.)")

        print("🔎 Accessing Sreality API...")
        response = requests.get(api_url, headers=headers, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        total_listings = data.get('result_size', 0)
        if total_listings == 0:
            print("ℹ️ No listings found for the given criteria.")
            return
            
        total_pages = math.ceil(total_listings / params['per_page'])
        print(f"✅ Found {total_listings} raw ads across {total_pages} pages. (Should be ~10 or less)")

        for page_num in range(1, total_pages + 1):
            print(f"📄 Scraping page {page_num} of {total_pages}...")
            params['page'] = page_num
            params['tms'] = int(time.time() * 1000)

            page_response = requests.get(api_url, headers=headers, params=params, timeout=10)
            page_data = page_response.json()
            
            estates = page_data.get('_embedded', {}).get('estates', [])

            for estate in estates:
                
                title = estate.get('name', 'N/A')

                # Extract type and size (your original regex)
                type_of_flat = 'N/A'
                size = 0  # Default to 0 for comparison
                type_match = re.search(r'(\d\s?\+\s?\w{1,2})', title)
                if type_match:
                    type_of_flat = type_match.group(1).replace(' ', '')
                size_match = re.search(r'(\d+)\s*m²', title)
                if size_match:
                    size = int(size_match.group(1))

                # NEW: Strict post-fetch filter for your exact types + min size
                allowed_types = ['2+kk', '2+1', '3+kk', '3+1']
                if type_of_flat not in allowed_types or size < 50:
                    skipped_count += 1
                    continue  # Skip if doesn't match

                # Build link
                seo_info = estate.get('seo', {})
                locality_slug = seo_info.get('locality', '')
                hash_id = estate.get('hash_id')
                link = (
                    f"https://www.sreality.cz/detail/prodej/byt/{type_of_flat}/{locality_slug}/{hash_id}"
                    if locality_slug and hash_id else 'N/A'
                )
                
                # Append
                all_listings_data.append({
                    "uid": uid_counter,
                    "link": link,
                    "type_of_flat": type_of_flat,
                    "size": size,
                    "price": estate.get('price'),
                    "locality": estate.get('locality', 'N/A'),
                    # Encode pipe characters in image URL so browsers accept it
                    "image": (lambda href: href.replace('|', '%7C') if isinstance(href, str) and '|' in href else href)(
                        estate.get('_links', {}).get('images', [{}])[0].get('href', 'N/A')
                    ),
                    "source": "sreality.cz"
                })
                uid_counter += 1
            
            time.sleep(1) 

        with open(output_filename, 'w', encoding='utf-8') as f:
            json.dump(all_listings_data, f, ensure_ascii=False, indent=4)
        
        print(f"\n🎉 Success! Saved {len(all_listings_data)} filtered listings to '{output_filename}'.")
        print(f"   - Skipped {skipped_count} (wrong type or size <50m²).")
        print("   - If still too many, check the debug URL for raw API total.")

    except requests.exceptions.RequestException as e:
        print(f"❌ Request error: {e}")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")

def scrape_api_sreality():
    """Wrapper function for pipeline integration."""
    scrape_sreality_listings("api_sreality.json")

if __name__ == "__main__":
    # Run the final scraper when executed directly
    scrape_sreality_listings(output_filename="sreality.json")
