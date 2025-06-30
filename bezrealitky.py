import requests
from bs4 import BeautifulSoup
import pandas as pd
import re
import time
from urllib.parse import urljoin, unquote, urlparse, parse_qs
import json

def scrape_bezrealitky():
    """
    Scrapes real estate listings from bezrealitky.cz for apartments in Brno.
    """
    base_url = "https://www.bezrealitky.cz/vyhledat?offerType=PRODEJ&estateType=BYT&disposition=DISP_2_KK&disposition=DISP_2_1&disposition=DISP_3_KK&disposition=DISP_3_1&priceTo=8000000&surfaceFrom=50&surfaceTo=80&regionOsmIds=R438171&osm_value=Brno%2C+okres+Brno-m%C4%9Bsto%2C+Jihomoravsk%C3%BD+kraj%2C+Jihov%C3%BDchod%2C+%C4%8Cesko&location=exact&currency=CZK"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    # First request to get page count
    try:
        print(f"Fetching initial page to determine pagination: {base_url}")
        response = requests.get(base_url, headers=headers)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching the URL: {e}")
        return

    soup = BeautifulSoup(response.content, 'html.parser')
    
    num_pages = 1
    pagination = soup.find('ul', class_='pagination')
    if pagination:
        page_tags = pagination.find_all(['a', 'span'], class_='page-link')
        page_numbers = [int(tag.text) for tag in page_tags if tag.text.isdigit()]
        if page_numbers:
            num_pages = max(page_numbers)
    
    print(f"Found {num_pages} pages to scrape.")

    all_data = []

    for page_num in range(1, num_pages + 1):
        if page_num == 1:
            current_soup = soup
            print("Scraping page 1 (initial page)...")
        else:
            url = f"{base_url}&page={page_num}"
            print(f"Scraping page {page_num}: {url}")
            try:
                response = requests.get(url, headers=headers)
                response.raise_for_status()
                current_soup = BeautifulSoup(response.content, 'html.parser')
                time.sleep(1)
            except requests.exceptions.RequestException as e:
                print(f"Error fetching page {page_num}: {e}")
                continue

        listings = current_soup.find_all('article', class_='propertyCard')
        
        if not listings:
            print(f"No listings found on page {page_num}. The website structure might have changed.")
            continue

        print(f"Found {len(listings)} listings on page {page_num}.")

        for listing in listings:
            try:
                h2_tag = listing.find('h2', class_='PropertyCard_propertyCardHeadline___diKI')
                link_tag = h2_tag.find('a') if h2_tag else None
                
                if not link_tag:
                    continue

                link_href = link_tag['href']
                link = urljoin(base_url, link_href)

                locality_tag = link_tag.find('span', class_='PropertyCard_propertyCardAddress__hNqyR')
                locality = locality_tag.text.strip() if locality_tag else 'N/A'

                price_tag = listing.find('div', class_='PropertyPrice_propertyPrice__lthza')
                price_amount_tag = price_tag.find('span', class_='PropertyPrice_propertyPriceAmount__WdEE1') if price_tag else None
                price_text = price_amount_tag.text.strip() if price_amount_tag else '0'
                price = ''.join(re.findall(r'\d+', price_text))

                img_tag = listing.find('img')
                image_url = 'N/A'
                if img_tag and 'src' in img_tag.attrs:
                    src = img_tag['src']
                    if src.startswith('/_next/image?url='):
                        parsed_url = urlparse(src)
                        query_params = parse_qs(parsed_url.query)
                        if 'url' in query_params:
                            image_url = query_params['url'][0]
                    else:
                        image_url = src

                features_list = listing.find('ul', class_='FeaturesList_featuresList__75Wet')
                features = features_list.find_all('li') if features_list else []
                
                flat_type = 'N/A'
                size = 'N/A'

                if len(features) > 0:
                    flat_type_text = features[0].text.strip()
                    type_match = re.search(r'(\d\+\w{1,2})', flat_type_text)
                    if type_match:
                        flat_type = type_match.group(1)
                    else:
                        flat_type = flat_type_text

                if len(features) > 1:
                    size_text = features[1].text.strip()
                    size_match = re.search(r'(\d+)', size_text)
                    if size_match:
                        size = size_match.group(1)

                all_data.append({
                    'image': image_url,
                    'locality': locality,
                    'type_of_flat': flat_type,
                    'size': size,
                    'price': int(price) if price.isdigit() else 0,
                    'link': link
                })
            except Exception as e:
                print(f"Error parsing a listing: {e}")

    df = pd.DataFrame(all_data)
    
    print("\nScraped Data:")
    print(df)
    
    json_filename = 'bezrealitky.json'
    records = df.to_dict(orient='records')
    # Add UID (1-indexed) and source identifier
    for idx, rec in enumerate(records, start=1):
        rec['uid'] = idx
        rec['source'] = 'bezrealitky'
    with open(json_filename, 'w', encoding='utf-8') as f:
        json.dump(records, f, ensure_ascii=False, indent=4)
    print(f"\nData from {len(all_data)} listings saved to {json_filename}")

if __name__ == "__main__":
    scrape_bezrealitky() 