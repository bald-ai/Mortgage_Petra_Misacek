import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException
import pandas as pd
import re
from bs4 import BeautifulSoup
import json

def scrape_sreality():
    """
    Logs into Seznam.cz and then scrapes real estate listings from sreality.cz,
    iterating through all pages until completion.
    """
    login_url = "https://login.szn.cz/"
    sreality_url = "https://www.sreality.cz/hledani/prodej/byty?velikost=2%2B1%2C2%2Bkk%2C3%2B1%2C3%2Bkk&stari=tyden&cena-do=8000000&plocha-od=50&plocha-do=80&region=Brno&region-id=5740&region-typ=municipality"
    email = "baldai@hey.com"
    password = "Seznam236"

    try:
        service = ChromeService(ChromeDriverManager().install())
        chrome_options = Options()
        chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-gpu")
        driver = webdriver.Chrome(service=service, options=chrome_options)
    except Exception as e:
        print(f"Error setting up Chrome driver: {e}")
        return

    # --- Step 1: Login to Seznam ---
    try:
        print("Starting login process...")
        driver.get(login_url)
        time.sleep(2)
        
        driver.find_element(By.ID, "login-username").send_keys(email)
        time.sleep(1)
        driver.find_element(By.CSS_SELECTOR, "button[data-locale='login.submit']").click()
        print("Username entered.")
        
        time.sleep(2)
        driver.find_element(By.ID, "login-password").send_keys(password)
        time.sleep(1)
        driver.find_element(By.CSS_SELECTOR, "button[data-locale='login.submit']").click()
        print("Password entered. Login submitted.")
        
        time.sleep(5) # Wait for login to be processed
    except Exception as e:
        print(f"An error occurred during login: {e}")
        driver.quit()
        return

    # --- Step 2: Navigate to Sreality and Scrape ---
    print(f"Login successful. Navigating to {sreality_url}")
    driver.get(sreality_url)
    time.sleep(5) # Wait for page to load

    all_data = []
    page_num = 1

    while True:
        print(f"--- Scraping Page {page_num} ---")
        
        # Wait for the main container of listings to be present
        time.sleep(2) # A brief wait for the container to settle
        
        # Get all listing elements on the page using Selenium
        listing_elements = driver.find_elements(By.CSS_SELECTOR, 'li.MuiGrid2-root.MuiGrid2-direction-xs-row')
        print(f"Found {len(listing_elements)} listing elements on this page.")

        if not listing_elements:
            print("No listing elements found, ending scrape.")
            break

        for element in listing_elements:
            try:
                # Scroll each element into view before scraping
                driver.execute_script("arguments[0].scrollIntoView({block: 'center', inline: 'nearest'});", element)
                time.sleep(0.5) # A short pause for lazy-loaded content to appear

                # Get the HTML of the now-visible element and parse it
                element_html = element.get_attribute('outerHTML')
                soup = BeautifulSoup(element_html, 'lxml')

                # The parsing logic remains the same, but now operates on a single listing's HTML
                link_anchor = soup.find('a', class_='css-1s6ohwi')
                if not link_anchor:
                    continue
                
                link_href = link_anchor.get('href', 'N/A')
                link = f"https://www.sreality.cz{link_href}" if link_href.startswith('/') else link_href
                
                image_tag = link_anchor.find('img', class_='css-f5kes')
                image_url = image_tag.get('srcset', '').split(' ')[0] if image_tag else 'N/A'
                if image_url.startswith('//'):
                    image_url = f"https:{image_url}"

                text_content = link_anchor.find('div', class_='css-173t8lh')
                if not text_content:
                    continue
                
                info_paragraphs = text_content.find_all('p', class_='css-d7upve')
                price_paragraph = text_content.find('p', class_='css-ca9wwd')

                title_text = info_paragraphs[0].text.strip() if len(info_paragraphs) > 0 else 'N/A'
                locality = info_paragraphs[1].text.strip() if len(info_paragraphs) > 1 else 'N/A'
                price_text = price_paragraph.text.strip() if price_paragraph else '0'
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

        # --- Step 3: Find and click the 'Next Page' button ---
        try:
            next_page_button = driver.find_element(By.CSS_SELECTOR, 'button[data-e2e="show-more-btn"]')
            print("Found 'Next Page' button. Clicking...")
            driver.execute_script("arguments[0].click();", next_page_button)
            page_num += 1
            time.sleep(5) # Wait for the next page to load
        except NoSuchElementException:
            print("No 'Next Page' button found. This is the last page.")
            break
        except Exception as e:
            print(f"An error occurred navigating to the next page: {e}")
            break

    driver.quit()
    
    df = pd.DataFrame(all_data)
    
    print("\n--- Scraping Complete ---")
    print(f"Total listings scraped: {len(all_data)}")
    print(df.head())
    
    json_filename = 'sreality.json'
    # Convert dataframe to list of dictionaries and save with standard json library
    records = df.to_dict(orient='records')
    # Add UID (1-indexed) and source identifier
    for idx, rec in enumerate(records, start=1):
        rec['uid'] = idx
        rec['source'] = 'sreality'
    with open(json_filename, 'w', encoding='utf-8') as f:
        json.dump(records, f, ensure_ascii=False, indent=4)

    print(f"\nData saved to {json_filename}")

if __name__ == "__main__":
    scrape_sreality() 