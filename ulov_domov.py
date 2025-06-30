import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
import pandas as pd
import re
from bs4 import BeautifulSoup
import json

def scrape_ulov_domov():
    """
    Scrapes real estate listings from ulovdomov.cz for apartments for sale in Brno.
    It clicks the "load more" button until all listings are displayed.
    """
    url = "https://www.ulovdomov.cz/prodej/bytu/brno/2-kk?od=50m2&do=80m2&cena-do=8000000kc&dispozice=2-1%2C3-kk%2C3-1&lokace=Brno"
    
    # Setup Chrome options
    chrome_options = Options()
    # Run in headless mode so the scraper can execute without a GUI.
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-gpu")
    
    # Setup Chrome driver using webdriver-manager
    try:
        service = ChromeService(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
    except Exception as e:
        print(f"Error setting up Chrome driver: {e}")
        print("Please ensure you have Google Chrome installed.")
        return

    driver.get(url)

    print(f"Navigated to {url}")

    while True:
        try:
            # Wait for the "Načíst další" button to be clickable and scroll it into view
            load_more_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Načíst další')]"))
            )
            driver.execute_script("arguments[0].scrollIntoView(true);", load_more_button)
            time.sleep(1) # wait for scroll
            
            # Click the button using JavaScript to avoid potential interception
            driver.execute_script("arguments[0].click();", load_more_button)
            print("Clicked 'Načíst další' button.")
            
            # Wait for 3 seconds as requested by user
            time.sleep(3)
        except TimeoutException:
            print("No more 'Načíst další' button found. All listings should be loaded.")
            break
        except Exception as e:
            print(f"An error occurred while trying to click the button: {e}")
            break

    page_source = driver.page_source
    print(f"Final page source length: {len(page_source)}")
    
    driver.quit()

    soup = BeautifulSoup(page_source, 'lxml')
    
    listings = soup.find_all('div', attrs={'data-test': 'previewOfferLeases'})
    
    print(f"Found {len(listings)} listings to parse.")

    all_data = []

    for listing in listings:
        try:
            image_tag = listing.find('img')
            image_url = image_tag['src'] if image_tag and 'src' in image_tag.attrs else 'N/A'

            link_anchor = listing.find('a', class_='css-1ihpi83')
            
            link_href = link_anchor.get('href', 'N/A') if link_anchor else 'N/A'
            link = f"https://www.ulovdomov.cz{link_href}" if link_href != 'N/A' and link_href.startswith('/') else link_href

            locality_tag = link_anchor.find('p', class_='css-adlj2b') if link_anchor else None
            locality = locality_tag.text.strip() if locality_tag else 'N/A'

            title_tag = link_anchor.find('h2', attrs={'data-test': 'headingOfLeasesPreview'}) if link_anchor else None
            title_text = title_tag.text.strip() if title_tag else ''

            price_tag = link_anchor.find('span', class_='css-19kx31i') if link_anchor else None
            price_text = price_tag.text.strip() if price_tag else '0'
            price = ''.join(re.findall(r'\d+', price_text))

            flat_type = 'N/A'
            size = 'N/A'
            
            if title_text:
                type_match = re.search(r'(\d\s*\+\s*\w{1,2})', title_text)
                if type_match:
                    flat_type = type_match.group(1).replace(' ', '')

                size_match = re.search(r'(\d+)\s*m2', title_text)
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
    
    json_filename = 'ulov_domov.json'
    records = df.to_dict(orient='records')
    # Add UID (1-indexed) and source identifier
    for idx, rec in enumerate(records, start=1):
        rec['uid'] = idx
        rec['source'] = 'ulov_domov'
    with open(json_filename, 'w', encoding='utf-8') as f:
        json.dump(records, f, ensure_ascii=False, indent=4)
    print(f"\nData from {len(all_data)} listings saved to {json_filename}")


if __name__ == "__main__":
    scrape_ulov_domov() 