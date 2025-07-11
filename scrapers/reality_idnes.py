import requests
from bs4 import BeautifulSoup
import pandas as pd
import re
import time
import json

def scrape_reality_idnes():
    """
    Scrapes real estate listings from reality.idnes.cz for apartments in Brno from all pages.
    """
    base_url = "https://reality.idnes.cz/s/prodej/byty/cena-do-8000000/brno/?s-qc%5BsubtypeFlat%5D%5B0%5D=2k&s-qc%5BsubtypeFlat%5D%5B1%5D=21&s-qc%5BsubtypeFlat%5D%5B2%5D=3k&s-qc%5BsubtypeFlat%5D%5B3%5D=31&s-qc%5BusableAreaMin%5D=50&s-qc%5BusableAreaMax%5D=80&s-qc%5BarticleAge%5D=31"
    
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
    paginator = soup.find('p', class_='paginator')
    if paginator:
        page_numbers = [int(tag.text) for tag in paginator.find_all('span', class_='btn__text') if tag.text.isdigit()]
        if page_numbers:
            num_pages = max(page_numbers)
    
    print(f"Found {num_pages} pages to scrape.")

    all_data = []

    for page_num in range(1, num_pages + 1):
        if page_num == 1:
            url = base_url
        else:
            url = f"{base_url}&page={page_num - 1}"

        print(f"Scraping page {page_num}: {url}")

        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            print(f"Error fetching page {page_num}: {e}")
            continue

        soup = BeautifulSoup(response.content, 'html.parser')
        
        listings = soup.find_all('div', class_='c-products__item')
        
        if not listings:
            print(f"No listings found on page {page_num}. The website structure might have changed.")
            continue

        for listing in listings:
            try:
                price_tag = listing.find('p', class_='c-products__price')
                if not price_tag:
                    continue

                link_tag = listing.find('a', class_='c-products__link')
                link_href = link_tag['href'] if link_tag else 'N/A'
                if link_href.startswith('/'):
                    link = f"https://reality.idnes.cz{link_href}"
                else:
                    link = link_href

                img_tag = listing.find('img')
                image_url = 'N/A'
                if img_tag:
                    if 'data-src' in img_tag.attrs:
                        image_url = img_tag['data-src']
                    elif 'src' in img_tag.attrs:
                        image_url = img_tag['src']

                locality_tag = listing.find('p', class_='c-products__info')
                locality = locality_tag.text.strip() if locality_tag else 'N/A'
                
                price_text = price_tag.text.strip() if price_tag else '0'
                price = ''.join(re.findall(r'\d+', price_text))

                title_tag = listing.find('h2', class_='c-products__title')
                title_text = title_tag.text.replace('\xa0', ' ').strip() if title_tag else ''

                flat_type = 'N/A'
                size = 'N/A'

                type_match = re.search(r'(\d\+\w{1,2})', title_text)
                if type_match:
                    flat_type = type_match.group(1)

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
    
    print("\nScraped Data:")
    print(df)
    
    json_filename = 'reality_idnes.json'
    records = df.to_dict(orient='records')
    # Add UID (1-indexed) and source identifier
    for idx, rec in enumerate(records, start=1):
        rec['uid'] = idx
        rec['source'] = 'reality_idnes'
    with open(json_filename, 'w', encoding='utf-8') as f:
        json.dump(records, f, ensure_ascii=False, indent=4)
    print(f"\nData from {len(all_data)} listings saved to {json_filename}")

if __name__ == "__main__":
    scrape_reality_idnes() 