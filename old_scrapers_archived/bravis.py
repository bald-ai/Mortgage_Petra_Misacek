import requests
import json
import re
from bs4 import BeautifulSoup
import time

def scrape_and_save_listings(base_search_url, output_filename):
    """
    Fetches all pages of a bravis.cz search result, scrapes property listings,
    and saves them to a JSON file.

    Args:
        base_search_url (str): The URL of the first page of the real estate listings.
        output_filename (str): The name of the file to save the JSON data to.
    """
    # Set a User-Agent to mimic a browser
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    all_flats_data = []
    uid_counter = 1
    # The base domain is needed to construct absolute URLs from relative links
    base_domain = "https://www.bravis.cz"

    try:
        # --- 1. Determine Total Number of Pages ---
        print("🔎 Accessing first page to determine the total number of pages...")
        first_page_response = requests.get(base_search_url, headers=headers, timeout=10)
        first_page_response.raise_for_status()
        soup = BeautifulSoup(first_page_response.content, 'html.parser')

        last_page_number = 1
        pagination_div = soup.find('div', attrs={'data-maxpages': True})
        if pagination_div:
            last_page_number = int(pagination_div['data-maxpages'])

        print(f"✅ Found {last_page_number} pages to scrape.")

        # --- 2. Loop Through All Pages ---
        for page_num in range(1, last_page_number + 1):
            # Construct the URL for the current page
            if page_num == 1:
                page_url = base_search_url
            else:
                # The URL structure for subsequent pages is different
                page_url = f"https://www.bravis.cz/prodej-bytu?mesto=&typ-nemovitosti-byt+2=&typ-nemovitosti-byt+3=&action=search&mapa=&s={page_num}-order-0"

            print(f" Scraping page {page_num} of {last_page_number}...")

            response = requests.get(page_url, headers=headers, timeout=10)
            response.raise_for_status()
            page_soup = BeautifulSoup(response.content, 'html.parser')

            # Find all 'div' elements with the class 'item'
            listings = page_soup.find_all('div', class_='item')

            if not listings and page_num == 1:
                print("ℹ️ No listings were found on the first page. Exiting.")
                return

            for listing in listings:
                # --- Extract Data for Each Listing ---
                link_tag = listing.find('a')
                if not link_tag:
                    continue
                
                relative_link = link_tag['href']
                # Create a full URL from a relative link
                link = relative_link if relative_link.startswith('http') else f"{base_domain.rstrip('/')}/{relative_link.lstrip('/')}"

                img_tag = listing.find('img')
                image = img_tag['src'] if img_tag and 'src' in img_tag.attrs else 'N/A'

                desc_div = listing.find('div', class_='desc')
                if not desc_div:
                    continue

                locality_tag = desc_div.find('span', class_='location')
                locality = locality_tag.get_text(strip=True) if locality_tag else 'N/A'

                price_tag = desc_div.find('strong', class_='price')
                if price_tag:
                    price_digits = re.sub(r'\D', '', price_tag.get_text())
                    price = int(price_digits) if price_digits else None
                else:
                    price = None
                
                flat_type = 'N/A'
                size = 'N/A'
                
                params_list = desc_div.find('ul', class_='params')
                if params_list:
                    params = params_list.find_all('li')
                    if len(params) > 0:
                        flat_type_text = params[0].get_text(strip=True)
                        # Extract type like '2+kk' or '3+1'
                        type_match = re.search(r'(\d\s?\+\s?\w{1,2})', flat_type_text)
                        if type_match:
                            flat_type = type_match.group(1).replace(' ', '')

                    if len(params) > 1:
                        size_text = params[1].get_text(strip=True)
                        # Extract just the number for the size
                        size_match = re.search(r'(\d+)', size_text)
                        if size_match:
                            size = size_match.group(1)

                all_flats_data.append({
                    "uid": uid_counter,
                    "link": link,
                    "type_of_flat": flat_type,
                    "size": size,
                    "price": price,
                    "locality": locality,
                    "image": image,
                    "source": "bravis.cz"
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

# The URL for the first page of listings
target_url = "https://www.bravis.cz/prodej-bytu?address=&mesto=&typ-nemovitosti-byt+2=&typ-nemovitosti-byt+3=&action=search&mapa="
json_output_filename = "bravis.json"

# Run the scraping and saving function
scrape_and_save_listings(target_url, json_output_filename)