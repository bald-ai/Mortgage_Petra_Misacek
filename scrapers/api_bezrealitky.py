import requests
import json
import re
from urllib.parse import urlparse, parse_qs, unquote
from bs4 import BeautifulSoup

def scrape_bezrealitky_listings(json_output_filename):
    """Scrape bezrealitky.cz listings and save to JSON file."""
    # The URL with search parameters for flats in Brno
    base_url = "https://www.bezrealitky.cz/vyhledat"
    params = {
        'offerType': 'PRODEJ',
        'estateType': 'BYT',
        'disposition': ['DISP_2_KK', 'DISP_2_1', 'DISP_3_KK', 'DISP_3_1'],
        'priceTo': '8000000',
        'surfaceFrom': '50',
        'surfaceTo': '80',
        'regionOsmIds': 'R438171',
        'osm_value': 'Brno, okres Brno-město, Jihomoravský kraj, Jihovýchod, Česko',
        'location': 'exact',
        'currency': 'CZK',
        'limit': '15', # Number of listings per page/request
        'offset': '0'  # Starting offset
    }

    # List to store all the flat data
    all_flats_data = []
    uid_counter = 1

    # Standard headers to mimic a browser
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    try:
        # --- 1. Determine Total Number of Listings ---
        print("🔎 Determining total number of listings...")
        response = requests.get(base_url, headers=headers, params=params, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        total_listings = 0
        # Find the count from the text like "(13 nemovitostí)"
        count_text_element = soup.find('p', class_='form-label')
        if count_text_element and "nemovitostí" in count_text_element.text:
            match = re.search(r'\((\d+)\s+nemovitostí\)', count_text_element.text)
            if match:
                total_listings = int(match.group(1))
                print(f"✅ Found a total of {total_listings} listings to scrape.")
        
        if total_listings == 0:
            print("⚠️ Could not determine total listings, or none found on the first page. Exiting.")
            return

        # --- 2. Loop Through All Pages Using Offset ---
        current_offset = 0
        while len(all_flats_data) < total_listings:
            params['offset'] = str(current_offset)
            print(f" Scraping listings {current_offset + 1}-{current_offset + int(params['limit'])} of {total_listings}...")

            page_response = requests.get(base_url, headers=headers, params=params, timeout=10)
            page_response.raise_for_status()
            page_soup = BeautifulSoup(page_response.text, 'html.parser')
            
            # Select all article elements that represent a property card
            listings = page_soup.find_all('article', class_='PropertyCard_propertyCard__moO_5')

            if not listings:
                print(" No more listings found. Ending scrape.")
                break

            for listing in listings:
                # Extract link
                link_tag = listing.select_one('h2.PropertyCard_propertyCardHeadline___diKI > a')
                link = link_tag['href'] if link_tag else 'N/A'

                # Extract image
                image_tag = listing.select_one('div.CardCarousel_cardCarouselSlide__mK880 img')
                raw_src = image_tag['src'] if image_tag and 'src' in image_tag.attrs else 'N/A'

                # --- Clean Next.js optimizer URL to a direct asset link ---
                if isinstance(raw_src, str) and raw_src.startswith('/_next/image'):
                    parsed = urlparse(raw_src)
                    qs = parse_qs(parsed.query)
                    if 'url' in qs and qs['url']:
                        decoded = unquote(qs['url'][0])
                        if decoded.startswith('//'):
                            decoded = 'https:' + decoded
                        image = decoded
                    else:
                        image = raw_src
                else:
                    image = raw_src
                
                # Extract locality
                locality_tag = listing.select_one('span.PropertyCard_propertyCardAddress__hNqyR')
                locality = locality_tag.get_text(strip=True) if locality_tag else 'N/A'

                # Extract and clean price
                price_tag = listing.select_one('span.PropertyPrice_propertyPriceAmount__WdEE1')
                if price_tag:
                    # Remove all whitespace and non-digit characters (including 'Kč')
                    price_text = "".join(price_tag.get_text(strip=True).split())
                    price_digits = re.sub(r'\D', '', price_text)
                    price = int(price_digits) if price_digits else None
                else:
                    price = None

                # Extract type and size from the features list
                flat_type, size = 'N/A', 'N/A'
                features = listing.select('ul.FeaturesList_featuresList__75Wet > li')
                if len(features) >= 2:
                    # The first feature is usually the type, the second is the size
                    flat_type = features[0].get_text(strip=True) if features[0] else 'N/A'
                    size_text = features[1].get_text(strip=True).replace('m²', '').strip()
                    size = size_text

                all_flats_data.append({
                    "uid": uid_counter,
                    "link": link,
                    "type_of_flat": flat_type,
                    "size": size,
                    "price": price,
                    "locality": locality,
                    "image": image,
                    "source": "bezrealitky.cz"
                })
                uid_counter += 1

            current_offset += int(params['limit'])

        # --- 3. Save the Final JSON File ---
        if all_flats_data:
            # Ensure we don't save more than the stated total due to edge cases
            final_listings = all_flats_data[:total_listings]
            with open(json_output_filename, 'w', encoding='utf-8') as json_file:
                json.dump(final_listings, json_file, ensure_ascii=False, indent=4)
            print(f"\n✅ Success! A total of {len(final_listings)} listings have been parsed and saved to '{json_output_filename}'.")
        else:
            print("\nℹ️ No listings were found.")

    except requests.exceptions.RequestException as e:
        print(f"❌ An error occurred during the request: {e}")
    except IOError as e:
        print(f"❌ An error occurred while writing to the file: {e}")
    except Exception as e:
        print(f"❌ An unexpected error occurred: {e}")

def scrape_api_bezrealitky():
    """Wrapper function for pipeline integration."""
    scrape_bezrealitky_listings("api_bezrealitky.json")

if __name__ == "__main__":
    # Run the scraper when executed directly
    scrape_bezrealitky_listings("bezrealitky.json")