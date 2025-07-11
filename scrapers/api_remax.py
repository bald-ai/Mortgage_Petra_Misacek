import requests
import json
import re
from bs4 import BeautifulSoup
import time

def scrape_remax_listings(base_search_url, output_filename):
    """
    Fetches all pages of a remax-czech.cz search result, scrapes property listings,
    and saves them to a JSON file.
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    all_flats_data = []
    uid_counter = 1
    base_domain = "https://www.remax-czech.cz"

    try:
        print("🔎 Accessing the first page to determine the total number of pages...")
        first_page_response = requests.get(base_search_url, headers=headers, timeout=15)
        first_page_response.raise_for_status()
        soup = BeautifulSoup(first_page_response.content, 'html.parser')

        last_page_number = 1
        paginator = soup.find('div', class_='paginatorWrapper')
        if paginator:
            page_links = paginator.find_all('a')
            page_numbers = [int(link.get_text(strip=True)) for link in page_links if link.get_text(strip=True).isdigit()]
            if page_numbers:
                last_page_number = max(page_numbers)
        
        print(f"✅ Found {last_page_number} pages to scrape.")

        for page_num in range(1, last_page_number + 1):
            # Construct the correct URL for each page
            page_url = f"{base_search_url.split('&page=')[0]}&page={page_num}"
            
            print(f" Scraping page {page_num} of {last_page_number}...")

            response = requests.get(page_url, headers=headers, timeout=10)
            response.raise_for_status()
            page_soup = BeautifulSoup(response.content, 'html.parser')

            # --- THE CORRECT SELECTOR BASED ON YOUR FILE ---
            listings = page_soup.find_all('div', class_='pl-items__item')

            if not listings and page_num == 1:
                print("❌ No listings found! The website structure may have changed.")
                continue

            for listing in listings:
                # Selectors are now targeting the correct elements from your raw HTML file
                title_tag = listing.find('h2', class_='h5')
                title = title_tag.strong.get_text(strip=True) if title_tag and title_tag.strong else 'N/A'

                link_tag = listing.find('a', class_='pl-items__link')
                relative_link = link_tag['href'] if link_tag else ''
                link = f"{base_domain}{relative_link}" if relative_link else 'N/A'

                img_tag = listing.find('img', class_='lazy')
                # The image is in the 'data-src' attribute for lazy loading
                image = img_tag['data-src'] if img_tag and 'data-src' in img_tag.attrs else 'N/A'

                location_tag = listing.find('p')
                if location_tag:
                    raw_loc = location_tag.get_text(separator=' ', strip=True)
                    # Collapse all consecutive whitespace (including NBSP) into a single space
                    locality = re.sub(r'\s+', ' ', raw_loc).strip()
                else:
                    locality = 'N/A'
                
                price_tag = listing.find('div', class_='pl-items__item-price')
                price = None
                if price_tag:
                    price_text = price_tag.strong.get_text(strip=True) if price_tag.strong else ""
                    price_digits = re.sub(r'\D', '', price_text)
                    if price_digits:
                        price = int(price_digits)

                # Extract type and size from the title string using regex
                flat_type = 'N/A'
                size = 'N/A'
                
                type_match = re.search(r'(\d\s?\+\s?\w{1,2})', title)
                if type_match:
                    flat_type = type_match.group(1).replace(' ', '')

                size_match = re.search(r'(\d+)\s*m²', title)
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
                    "source": "remax-czech.cz"
                })
                uid_counter += 1
            
            time.sleep(1)

        # Save the final parsed data to the JSON file
        if all_flats_data:
            with open(output_filename, 'w', encoding='utf-8') as json_file:
                json.dump(all_flats_data, json_file, ensure_ascii=False, indent=4)
            print(f"\n🎉 Success! A total of {len(all_flats_data)} listings have been parsed and saved to '{output_filename}'.")
        else:
            print("\nℹ️ No listings were found after scraping all pages.")

    except requests.exceptions.RequestException as e:
        print(f"❌ An error occurred during the request: {e}")
    except Exception as e:
        print(f"❌ An unexpected error occurred: {e}")

def scrape_api_remax():
    """Wrapper function for pipeline integration."""
    target_url = "https://www.remax-czech.cz/reality/vyhledavani/?area_from=50&area_to=80&desc_text=Brno&hledani=1&price_to=8000000&sale=1"
    scrape_remax_listings(target_url, "api_remax.json")

if __name__ == "__main__":
    # URL for apartments for sale in Brno
    target_url = "https://www.remax-czech.cz/reality/vyhledavani/?area_from=50&area_to=80&desc_text=Brno&hledani=1&price_to=8000000&sale=1"
    json_output_filename = "remax.json"
    # Run the scraper
    scrape_remax_listings(target_url, json_output_filename)