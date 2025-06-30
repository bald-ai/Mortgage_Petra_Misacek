import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import pandas as pd
import re
from bs4 import BeautifulSoup
import json

def scrape_remax():
    """
    Scrapes real estate listings from remax-czech.cz for apartments for sale in Brno.
    It navigates through pages by clicking the 'next' arrow button until the last page is reached.
    """
    url = "https://www.remax-czech.cz/reality/vyhledavani/?area_from=50&area_to=80&desc_text=Brno&hledani=1&price_to=8000000&sale=1"
    
    # Setup Chrome options
    chrome_options = Options()
    # Run in headless mode so the scraper works on machines without a display.
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

    all_data = []

    while True:
        try:
            # Wait for listings to be present
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CLASS_NAME, "pl-items__item"))
            )
            
            page_source = driver.page_source
            soup = BeautifulSoup(page_source, 'lxml')
            listings = soup.find_all('div', class_='pl-items__item')
            print(f"Found {len(listings)} listings on current page.")

            for listing in listings:
                try:
                    image_url = listing.get('data-img', 'N/A')

                    link_tag = listing.find('a', class_='pl-items__link')
                    relative_link = link_tag.get('href', 'N/A') if link_tag else 'N/A'
                    link = f"https://www.remax-czech.cz{relative_link}" if relative_link != 'N/A' else 'N/A'

                    title_tag = listing.find('h2')
                    title_text = title_tag.strong.text.strip() if title_tag and title_tag.strong else ''

                    locality_tag = listing.find('p')
                    locality = locality_tag.text.strip().replace('\n', ', ').replace('\t', '') if locality_tag else 'N/A'

                    price_tag = listing.find('div', class_='pl-items__item-price')
                    price_text = price_tag.strong.text.strip() if price_tag and price_tag.strong else '0'
                    price = ''.join(re.findall(r'\d+', price_text))

                    flat_type = 'N/A'
                    size = 'N/A'
                    
                    if title_text:
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

            # Find and click the next page button
            next_page_button = driver.find_element(By.CSS_SELECTOR, "a.page-link[title='další']")
            # Check if the button's parent li is disabled
            if "disabled" in next_page_button.find_element(By.XPATH, "./parent::li").get_attribute("class"):
                print("Last page reached. Finishing scraping.")
                break
            
            driver.execute_script("arguments[0].click();", next_page_button)
            print("Clicked 'next page' button.")
            time.sleep(3) # Wait for page to load

        except NoSuchElementException:
            print("No more 'next page' button found. All pages scraped.")
            break
        except TimeoutException:
            print("Timed out waiting for page elements. Finishing scraping.")
            break
        except Exception as e:
            print(f"An error occurred during scraping: {e}")
            break

    driver.quit()
    
    df = pd.DataFrame(all_data)
    
    print(f"\nScraped a total of {len(all_data)} listings.")
    print(df.head())
    
    json_filename = 'remax.json'
    records = df.to_dict(orient='records')
    # Add UID (1-indexed) and source identifier
    for idx, rec in enumerate(records, start=1):
        rec['uid'] = idx
        rec['source'] = 'remax'
    with open(json_filename, 'w', encoding='utf-8') as f:
        json.dump(records, f, ensure_ascii=False, indent=4)
    print(f"\nData saved to {json_filename}")

if __name__ == "__main__":
    scrape_remax() 