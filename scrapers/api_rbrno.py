import requests
import json
import re
from bs4 import BeautifulSoup
import time

def scrape_and_save_listings(base_search_url, output_filename):
    """
    Fetches all pages of a search result, scrapes property listings, 
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
    base_url = "https://www.reality-brno.net"

    try:
        # --- 1. Determine Total Number of Pages ---
        print(f"🔎 Accessing first page to determine total number of pages...")
        # Try with longer timeout and retry logic
        for attempt in range(3):
            try:
                first_page_response = requests.get(base_search_url, headers=headers, timeout=30)
                break
            except requests.exceptions.Timeout:
                print(f"⏱️ Timeout on attempt {attempt + 1}/3, retrying...")
                if attempt == 2:
                    raise
                time.sleep(5)
        first_page_response.raise_for_status()
        soup = BeautifulSoup(first_page_response.content, 'html.parser')

        last_page_number = 1
        pagination_links = soup.select('div.pagination a.paginationLink')
        if pagination_links:
            # Find the highest page number from the pagination links
            page_numbers = [int(re.search(r'strana=(\d+)', link['href']).group(1)) for link in pagination_links if re.search(r'strana=(\d+)', link['href'])]
            if page_numbers:
                last_page_number = max(page_numbers)
        
        print(f"✅ Found {last_page_number} pages to scrape.")

        # --- 2. Loop Through All Pages ---
        for page_num in range(1, last_page_number + 1):
            # Construct the URL for the current page
            page_url = f"{base_search_url}&strana={page_num}"
            print(f" Scraping page {page_num} of {last_page_number}...")

            response = requests.get(page_url, headers=headers, timeout=30)
            response.raise_for_status()
            page_soup = BeautifulSoup(response.content, 'html.parser')

            # Find all 'div' elements with the class 'estate'
            listings = page_soup.find_all('div', class_='estate')

            if not listings and page_num == 1:
                print("ℹ️ No listings were found on the first page. Exiting.")
                return

            for listing in listings:
                # --- Extract Data for Each Listing ---
                link_tag = listing.select_one('div.estateImage > a')
                relative_link = link_tag['href'] if link_tag else 'N/A'
                link = f"{base_url}{relative_link}" if relative_link != 'N/A' else 'N/A'

                image_tag = listing.select_one('picture > source[type="image/webp"]')
                image = image_tag['srcset'] if image_tag and 'srcset' in image_tag.attrs else 'N/A'

                locality_tag = listing.select_one('p.adress')
                locality = locality_tag.get_text(strip=True) if locality_tag else 'N/A'

                price_tag = listing.select_one('span.big.text-blue')
                if price_tag:
                    price_digits = re.sub(r'\D', '', price_tag.get_text())
                    price = int(price_digits) if price_digits else None
                else:
                    price = None

                headline_tag = listing.select_one('h3 > a')
                headline_text = headline_tag.get_text(strip=True) if headline_tag else ""
                
                size_match = re.search(r'(\d+)\s*m', headline_text)
                size = size_match.group(1) if size_match else 'N/A'
                
                # Extract just the flat type (e.g., "2+kk", "3+1") from text like "Prodej bytu 2+kk"
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
                    "source": "reality-brno.net"
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

def scrape_api_rbrno():
    """Wrapper function for pipeline integration."""
    target_url = "https://www.reality-brno.net/prodej/byty/byty-2-kk/obec-brno/do-8000000/?d_subtyp=205,206,207"
    scrape_and_save_listings(target_url, "api_rbrno.json")

if __name__ == "__main__":
    # The URL for the first page of listings
    target_url = "https://www.reality-brno.net/prodej/byty/byty-2-kk/obec-brno/do-8000000/?d_subtyp=205,206,207"
    json_output_filename = "rbrno.json"
    # Run the scraping and saving function
    scrape_and_save_listings(target_url, json_output_filename)