import requests
from bs4 import BeautifulSoup
import pandas as pd
import re
import time
import json

def scrape_reality_brno():
    """
    Scrapes real estate listings from reality-brno.net for apartments in Brno from all pages.
    """
    base_url = "https://www.reality-brno.net/prodej/byty/byty-2-kk/obec-brno/do-8000000/?d_subtyp=205,206,207"
    
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
    pagination = soup.find('div', class_='pagination')
    if pagination:
        page_links = pagination.find_all(['a', 'span'])
        page_numbers = [int(link.text) for link in page_links if link.text.isdigit()]
        if page_numbers:
            num_pages = max(page_numbers)
    
    print(f"Found {num_pages} pages to scrape.")

    all_data = []

    for page_num in range(1, num_pages + 1):
        if page_num == 1:
            url = base_url
        else:
            url = f"{base_url}&strana={page_num}"

        print(f"Scraping page {page_num}: {url}")

        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            print(f"Error fetching page {page_num}: {e}")
            continue

        soup = BeautifulSoup(response.content, 'html.parser')
        
        listings = soup.find_all('div', class_='estate')
        
        if not listings:
            print(f"No listings found on page {page_num}. The website structure might have changed.")
            continue

        for listing in listings:
            try:
                title_tag = listing.find('h3').find('a')
                title_text = title_tag.text.strip() if title_tag else 'N/A'
                link_href = title_tag['href'] if title_tag else 'N/A'
                if link_href.startswith('/'):
                    link = f"https://www.reality-brno.net{link_href}"
                else:
                    link = link_href

                price_tag = listing.find('span', class_='big text-blue')
                price_text = price_tag.text.strip() if price_tag else '0'
                price = ''.join(re.findall(r'\d+', price_text))
                
                img_tag = listing.find('div', class_='estateImage').find('img')
                image_url = img_tag['src'] if img_tag and 'src' in img_tag.attrs else 'N/A'
                
                locality_tag = listing.find('p', class_='adress')
                locality = locality_tag.text.strip() if locality_tag else 'N/A'

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
    
    json_filename = 'reality_brno.json'
    records = df.to_dict(orient='records')
    # Add UID (1-indexed) and source identifier
    for idx, rec in enumerate(records, start=1):
        rec['uid'] = idx
        rec['source'] = 'reality_brno'
    with open(json_filename, 'w', encoding='utf-8') as f:
        json.dump(records, f, ensure_ascii=False, indent=4)
    print(f"\nData from {len(all_data)} listings saved to {json_filename}")

if __name__ == "__main__":
    scrape_reality_brno() 