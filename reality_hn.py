import requests
from bs4 import BeautifulSoup
import pandas as pd
import re
import time
from urllib.parse import urljoin
import json

def scrape_reality_hn():
    """
    Scrapes real estate listings from reality.hn.cz for apartments in Brno from all pages.
    """
    base_url = "https://reality.hn.cz/vypis-nabidek/?form%5Badresa_kraj_id%5D%5B%5D=116&form%5Badresa_obec_id%5D=&form%5Badresa_region_id%5D%5B116%5D%5B%5D=3702&form%5Badresa_region_id%5D%5B116%5D%5B%5D=3703&form%5Bcena_mena%5D=&form%5Bcena_normalizovana__from%5D=&form%5Bcena_normalizovana__to%5D=8000000&form%5Bdispozice%5D%5B%5D=3&form%5Bdispozice%5D%5B%5D=10&form%5Bdispozice%5D%5B%5D=4&form%5Bdispozice%5D%5B%5D=11&form%5Bexclusive%5D=&form%5Bfk_rk%5D=&form%5Binzerat_typ%5D=1&form%5Bnemovitost_typ%5D%5B%5D=4&form%5Bplocha__from%5D=50&form%5Bplocha__to%5D=80&form%5Bpodlazi_cislo__from%5D=&form%5Bpodlazi_cislo__to%5D=&form%5Bprojekt_id%5D=&form%5Bsearch_in_city%5D=&form%5Bsearch_in_text%5D=&form%5Bstari_inzeratu%5D=&form%5Bstav_objektu%5D=&form%5Btop_nabidky%5D="
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    try:
        response = requests.get(base_url, headers=headers)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching the URL: {e}")
        return

    soup = BeautifulSoup(response.content, 'html.parser')
    
    num_pages = 1
    paginator = soup.find('div', class_='paginator')
    if paginator:
        page_links = paginator.find_all('a')
        page_numbers = [int(a.text) for a in page_links if a.text.isdigit()]
        if page_numbers:
            num_pages = max(page_numbers)
            
    print(f"Found {num_pages} pages to scrape.")

    all_data = []

    for page_num in range(1, num_pages + 1):
        url = f"{base_url}&stranka={page_num}"

        print(f"Scraping page {page_num}: {url}")

        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            print(f"Error fetching page {page_num}: {e}")
            continue

        soup = BeautifulSoup(response.content, 'html.parser')
        
        listings_container = soup.find('ul', class_='rmix-ihned-list')
        if not listings_container:
            print(f"No listings container found on page {page_num}. The website structure might have changed.")
            continue
        
        listings = listings_container.find_all('li', recursive=False)

        if not listings:
            print(f"No listings found on page {page_num}.")
            continue

        for listing in listings:
            try:
                link_tag = listing.find('a')
                link_href = link_tag['href'] if link_tag else 'N/A'
                link = urljoin(base_url, link_href)

                img_tag = listing.find('img')
                image_url = 'N/A'
                if img_tag:
                    image_url = img_tag.get('data-src') or img_tag.get('src')
                
                title_tag = listing.find('h4')
                title_text = title_tag.text.strip() if title_tag else ''

                locality_tag = listing.find('p', class_='address')
                locality = locality_tag.text.strip() if locality_tag else 'N/A'
                
                price_tag = listing.find('p', class_='price')
                price_text = price_tag.text.strip().replace('\xa0', '') if price_tag else '0'
                price = ''.join(re.findall(r'\d+', price_text))

                flat_type = 'N/A'
                size = 'N/A'

                type_match = re.search(r'(\d\s*\+\s*\w{1,2})', title_text)
                if type_match:
                    flat_type = type_match.group(1).replace(' ', '')

                size_match = re.search(r'(\d+)\s*m²', title_text)
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
        
        time.sleep(1)

    df = pd.DataFrame(all_data)
    
    # Filter out developer projects which are often listed without price
    df = df[df['price'] > 0]
    
    print("\nScraped Data:")
    print(df)
    
    json_filename = 'reality_hn.json'
    records = df.to_dict(orient='records')
    # Add UID (1-indexed) and source identifier
    for idx, rec in enumerate(records, start=1):
        rec['uid'] = idx
        rec['source'] = 'reality_hn'
    with open(json_filename, 'w', encoding='utf-8') as f:
        json.dump(records, f, ensure_ascii=False, indent=4)
    print(f"\nData from {len(all_data)} listings saved to {json_filename}")

if __name__ == "__main__":
    scrape_reality_hn() 