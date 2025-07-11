import requests
import json
import re
from bs4 import BeautifulSoup
import time
import math

def scrape_and_save_listings(base_search_url, output_filename):
    """
    Fetches all pages of a search result from reality.hn.cz, scrapes property listings,
    and saves them to a JSON file.

    Args:
        base_search_url (str): The URL of the first page of the real estate listings.
        output_filename (str): The name of the file to save the JSON data to.
    """
    # Set a User-Agent to mimic a browser, which can help avoid being blocked.
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    all_flats_data = []
    uid_counter = 1
    base_url = "https://reality.hn.cz"

    try:
        # --- 1. Determine Total Number of Pages ---
        print("🔎 Accessing first page to determine the total number of pages...")
        first_page_response = requests.get(base_search_url, headers=headers, timeout=10)
        first_page_response.raise_for_status()
        soup = BeautifulSoup(first_page_response.content, 'html.parser')

        last_page_number = 1
        # Find the element containing the total number of listings
        total_results_tag = soup.select_one('div.paginator__total')
        if total_results_tag:
            total_results_text = total_results_tag.get_text(strip=True)
            # Use regex to find the total number of listings
            match = re.search(r'celkem (\d+)', total_results_text)
            if match:
                total_listings = int(match.group(1))
                # Calculate the number of pages, assuming 20 listings per page
                last_page_number = math.ceil(total_listings / 20)

        print(f"✅ Found {last_page_number} pages to scrape.")

        # --- 2. Loop Through All Pages ---
        for page_num in range(1, last_page_number + 1):
            # Construct the URL for the current page
            page_url = f"{base_search_url}&stranka={page_num}"
            print(f" Scraping page {page_num} of {last_page_number}...")

            response = requests.get(page_url, headers=headers, timeout=10)
            response.raise_for_status()
            page_soup = BeautifulSoup(response.content, 'html.parser')

            # Find all 'li' elements within the specified list class
            listings = page_soup.select('ul.rmix-ihned-list > li')

            if not listings and page_num == 1:
                print("ℹ️ No listings were found on the first page. Exiting.")
                return

            for listing in listings:
                # --- Extract Data for Each Listing ---
                headline_tag = listing.select_one('h4 > a')
                if not headline_tag:
                    continue # Skip if no headline/link is found

                link = headline_tag['href']
                headline_text = headline_tag.get_text(strip=True)

                image_tag = listing.select_one('img.lazy')
                image = image_tag['data-src'] if image_tag and 'data-src' in image_tag.attrs else 'N/A'

                locality_tag = listing.select_one('p.address')
                locality = locality_tag.get_text(strip=True) if locality_tag else 'N/A'

                price_tag = listing.select_one('p.price')
                if price_tag:
                    # Remove non-digit characters to get a clean number string
                    price_digits = re.sub(r'\D', '', price_tag.get_text())
                    price = int(price_digits) if price_digits else None
                else:
                    price = None

                # Extract size and type from the headline
                size_match = re.search(r'([\d,\.]+)\s*m²', headline_text)
                size = size_match.group(1).replace(',', '.') if size_match else 'N/A'
                
                # Extract just the flat type (e.g., "2+1", "3+kk") from text like "Prodej bytu, 2+1"
                type_match = re.search(r'(\d\s*\+\s*\w{1,2})', headline_text)
                type_of_flat = type_match.group(1).replace(' ', '') if type_match else 'N/A'

                all_flats_data.append({
                    "uid": uid_counter,
                    "link": link,
                    "type_of_flat": type_of_flat,
                    "size": size,
                    "price": price,
                    "locality": locality,
                    "image": image,
                    "source": "reality.hn.cz"
                })
                uid_counter += 1

            # Add a small delay to be respectful to the server
            time.sleep(1)

        # --- 3. Save the Final JSON File ---
        if all_flats_data:
            with open(output_filename, 'w', encoding='utf-8') as json_file:
                json.dump(all_flats_data, json_file, ensure_ascii=False, indent=4)
            print(f"\n✅ Success! A total of {len(all_flats_data)} listings have been parsed and saved to '{output_filename}'.")
        else:
            print("\nℹ️ No listings were found after scraping all pages.")

    except requests.exceptions.RequestException as e:
        print(f"❌ An error occurred during the request: {e}")
    except IOError as e:
        print(f"❌ An error occurred while writing to the file: {e}")
    except Exception as e:
        print(f"❌ An unexpected error occurred: {e}")

def scrape_api_rhn():
    """Wrapper function for pipeline integration."""
    target_url = "https://reality.hn.cz/vypis-nabidek/?form%5Badresa_kraj_id%5D%5B%5D=116&form%5Badresa_obec_id%5D=&form%5Badresa_region_id%5D%5B116%5D%5B%5D=3702&form%5Badresa_region_id%5D%5B116%5D%5B%5D=3703&form%5Bcena_mena%5D=&form%5Bcena_normalizovana__from%5D=&form%5Bcena_normalizovana__to%5D=8000000&form%5Bdispozice%5D%5B%5D=3&form%5Bdispozice%5D%5B%5D=10&form%5Bdispozice%5D%5B%5D=4&form%5Bdispozice%5D%5B%5D=11&form%5Bexclusive%5D=&form%5Bfk_rk%5D=&form%5Binzerat_typ%5D=1&form%5Bnemovitost_typ%5D%5B%5D=4&form%5Bplocha__from%5D=50&form%5Bplocha__to%5D=80&form%5Bpodlazi_cislo__from%5D=&form%5Bpodlazi_cislo__to%5D=&form%5Bprojekt_id%5D=&form%5Bsearch_in_city%5D=&form%5Bsearch_in_text%5D=&form%5Bstari_inzeratu%5D=&form%5Bstav_objektu%5D=&form%5Btop_nabidky%5D="
    scrape_and_save_listings(target_url, "api_rhn.json")

if __name__ == "__main__":
    # The URL for the first page of listings from the provided API info
    target_url = "https://reality.hn.cz/vypis-nabidek/?form%5Badresa_kraj_id%5D%5B%5D=116&form%5Badresa_obec_id%5D=&form%5Badresa_region_id%5D%5B116%5D%5B%5D=3702&form%5Badresa_region_id%5D%5B116%5D%5B%5D=3703&form%5Bcena_mena%5D=&form%5Bcena_normalizovana__from%5D=&form%5Bcena_normalizovana__to%5D=8000000&form%5Bdispozice%5D%5B%5D=3&form%5Bdispozice%5D%5B%5D=10&form%5Bdispozice%5D%5B%5D=4&form%5Bdispozice%5D%5B%5D=11&form%5Bexclusive%5D=&form%5Bfk_rk%5D=&form%5Binzerat_typ%5D=1&form%5Bnemovitost_typ%5D%5B%5D=4&form%5Bplocha__from%5D=50&form%5Bplocha__to%5D=80&form%5Bpodlazi_cislo__from%5D=&form%5Bpodlazi_cislo__to%5D=&form%5Bstari_inzeratu%5D=&form%5Bstav_objektu%5D=&form%5Btop_nabidky%5D="
    json_output_filename = "rhn.json"
    # Run the scraping and saving function
    scrape_and_save_listings(target_url, json_output_filename)