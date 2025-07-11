import requests
import json
import re
from bs4 import BeautifulSoup

def scrape_idnes_listings(json_output_filename):
    """Scrape reality.idnes.cz listings and save to JSON file."""
    # The base URL for apartments in Brno
    base_url = "https://reality.idnes.cz/s/prodej/byty/cena-do-8000000/brno/?s-qc[subtypeFlat][0]=2k&s-qc[subtypeFlat][1]=21&s-qc[subtypeFlat][2]=3k&s-qc[subtypeFlat][3]=31&s-qc[usableAreaMin]=50&s-qc[usableAreaMax]=80&s-qc[articleAge]=31"

    # List to store all the flat data from all pages
    all_flats_data = []
    uid_counter = 1

    # Standard headers to mimic a browser
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    try:
        # --- 1. Dynamically Find the Total Number of Pages ---
        print("🔎 Determining total number of pages...")
        first_page_response = requests.get(base_url, headers=headers, timeout=10)
        first_page_response.raise_for_status()
        soup = BeautifulSoup(first_page_response.text, 'html.parser')
        
        last_page_num = 0
        # Find all elements containing page numbers inside the paginator
        paginator = soup.find('p', class_='paginator')
        if paginator:
            page_items = paginator.find_all(class_='btn__text')
            page_numbers = []
            for item in page_items:
                # Check if the text is a digit, ignoring arrows and "Předchozí"
                if item.get_text(strip=True).isdigit():
                    page_numbers.append(int(item.get_text(strip=True)))
            
            if page_numbers:
                last_page_num = max(page_numbers)
                print(f"✅ Found {last_page_num} pages of results.")
            else:
                last_page_num = 1 # Assume only one page if no paginator is found
                print("⚠️ No pagination found, assuming 1 page.")
        else:
            last_page_num = 1
            print("⚠️ No pagination element found, assuming 1 page.")


        # --- 2. Loop Through All Detected Pages ---
        # Note: The URL parameter 'page' is zero-indexed (page 1 is page=0)
        for page_index in range(last_page_num):
            paginated_url = f"{base_url}&page={page_index}"
            print(f" Scraping page {page_index + 1}/{last_page_num}...")

            response = requests.get(paginated_url, headers=headers, timeout=10)
            response.raise_for_status()
            
            page_soup = BeautifulSoup(response.text, 'html.parser')
            listings = page_soup.select(".c-products__item:not(.c-products__item-advertisment) article")

            if not listings:
                print(f" No more listings found. Ending scrape.")
                break

            for listing in listings:
                # (The rest of the extraction logic is the same as before)
                link_tag = listing.find('a', class_='c-products__link')
                if not link_tag: continue
                
                link = link_tag.get('href', 'N/A')
                image_tag = link_tag.find('img', class_='js-lazyload')
                image = image_tag['data-src'] if image_tag and 'data-src' in image_tag.attrs else 'N/A'
                locality_tag = link_tag.find('p', class_='c-products__info')
                locality = locality_tag.get_text(strip=True) if locality_tag else 'N/A'
                price_tag = link_tag.find('p', class_='c-products__price')
                if price_tag:
                    price_text = "".join(price_tag.get_text(strip=True).split())
                    price_digits = re.sub(r'\D', '', price_text)
                    price = int(price_digits) if price_digits else None
                else:
                    price = None
                title_tag = link_tag.find('h2', class_='c-products__title')
                flat_type, size = 'N/A', 'N/A'

                if title_tag:
                    title_text = title_tag.get_text(strip=True)
                    match = re.search(r'bytu\s+([0-9]\s*\+\s*[0-9kK]{1,2})\s+([0-9]+)\s*m²', title_text)
                    if match:
                        flat_type = match.group(1).replace(" ", "")
                        size = match.group(2)
                
                all_flats_data.append({
                    "uid": uid_counter,
                    "link": link,
                    "type_of_flat": flat_type,
                    "size": size,
                    "price": price,
                    "locality": locality,
                    "image": image,
                    "source": "reality.idnes.cz"
                })
                uid_counter += 1

        # --- 3. Save the Final JSON File ---
        if all_flats_data:
            with open(json_output_filename, 'w', encoding='utf-8') as json_file:
                json.dump(all_flats_data, json_file, ensure_ascii=False, indent=4)
            print(f"\n✅ Success! A total of {len(all_flats_data)} listings have been parsed and saved to '{json_output_filename}'.")
        else:
            print("\nℹ️ No listings were found across any pages.")

    except requests.exceptions.RequestException as e:
        print(f"❌ An error occurred during the request: {e}")
    except IOError as e:
        print(f"❌ An error occurred while writing to a file: {e}")
    except Exception as e:
        print(f"❌ An unexpected error occurred: {e}")

def scrape_api_idnes():
    """Wrapper function for pipeline integration."""
    scrape_idnes_listings("api_idnes.json")

if __name__ == "__main__":
    # Run the scraper when executed directly
    scrape_idnes_listings("idnes.json")