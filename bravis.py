import requests
from bs4 import BeautifulSoup
import pandas as pd
import re
import time
import json

def scrape_bravis():
    """
    Scrapes real estate listings from bravis.cz for apartments in Brno from all pages.
    """
    base_url = "https://www.bravis.cz/prodej-bytu?address=&mesto=&typ-nemovitosti-byt+2=&typ-nemovitosti-byt+3=&action=search&mapa="
    
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
    pagination_div = soup.find('div', attrs={'data-maxpages': True})
    if pagination_div:
        num_pages = int(pagination_div['data-maxpages'])
    
    print(f"Found {num_pages} pages to scrape.")

    all_data = []

    for page_num in range(1, num_pages + 1):
        if page_num == 1:
            url = base_url
        else:
            url = f"https://www.bravis.cz/prodej-bytu?mesto=&typ-nemovitosti-byt+2=&typ-nemovitosti-byt+3=&action=search&mapa=&s={page_num}-order-0"

        print(f"Scraping page {page_num}: {url}")

        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            print(f"Error fetching page {page_num}: {e}")
            continue

        soup = BeautifulSoup(response.content, 'html.parser')
        
        listings = soup.find_all('div', class_='item')
        
        if not listings:
            print(f"No listings found on page {page_num}. The website structure might have changed.")
            continue

        for listing in listings:
            try:
                link_tag = listing.find('a')
                link_href = link_tag['href'] if link_tag else 'N/A'
                if not link_href.startswith('http'):
                    link = f"https://www.bravis.cz/{link_href}"
                else:
                    link = link_href

                desc_div = listing.find('div', class_='desc')
                if not desc_div:
                    continue
                
                title_tag = desc_div.find('h1')
                title_text = title_tag.text.strip() if title_tag else ''

                price_tag = desc_div.find('strong', class_='price')
                price_text = price_tag.text.strip() if price_tag else '0'
                price = ''.join(re.findall(r'\d+', price_text))

                img_tag = listing.find('img')
                image_url = img_tag['src'] if img_tag and 'src' in img_tag.attrs else 'N/A'

                locality_tag = desc_div.find('span', class_='location')
                locality = locality_tag.text.strip() if locality_tag else 'N/A'

                flat_type = 'N/A'
                size = 'N/A'
                
                params_list = desc_div.find('ul', class_='params')
                if params_list:
                    params = params_list.find_all('li')
                    if len(params) > 0:
                        flat_type_text = params[0].text.strip()
                        type_match = re.search(r'(byt\s*\d\+\w{1,2})', flat_type_text)
                        if type_match:
                            flat_type = type_match.group(1).replace('byt ', '')

                    if len(params) > 1:
                        size_text = params[1].text.strip()
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
        
        time.sleep(1)

    df = pd.DataFrame(all_data)
    
    print("\nScraped Data:")
    print(df)
    
    json_filename = 'bravis.json'
    records = df.to_dict(orient='records')
    # Add UID (1-indexed) and source identifier
    for idx, rec in enumerate(records, start=1):
        rec['uid'] = idx
        rec['source'] = 'bravis'
    with open(json_filename, 'w', encoding='utf-8') as f:
        json.dump(records, f, ensure_ascii=False, indent=4)
    print(f"\nData from {len(all_data)} listings saved to {json_filename}")

if __name__ == "__main__":
    scrape_bravis() 