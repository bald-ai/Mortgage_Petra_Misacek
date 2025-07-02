import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import pandas as pd
import re, json

# NEW — use Playwright Chromium
from selenium_helper import make_driver
driver = make_driver()

def scrape_remax():
    url = ("https://www.remax-czech.cz/reality/vyhledavani/"
           "?area_from=50&area_to=80&desc_text=Brno&hledani=1"
           "&price_to=8000000&sale=1")
    driver.get(url)
    print(f"Navigated to {url}")
    all_data = []

    while True:
        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CLASS_NAME, "pl-items__item"))
            )
            soup = BeautifulSoup(driver.page_source, "lxml")
            listings = soup.find_all("div", class_="pl-items__item")
            print(f"Found {len(listings)} listings on current page.")

            for listing in listings:
                try:
                    image_url = listing.get("data-img", "N/A")
                    link_tag = listing.find("a", class_="pl-items__link")
                    rel_link = link_tag.get("href", "N/A") if link_tag else "N/A"
                    link = f"https://www.remax-czech.cz{rel_link}" if rel_link != "N/A" else "N/A"
                    title = listing.find("h2").strong.text.strip()
                    locality = listing.find("p").text.strip().replace("\n", ", ").replace("\t", "")
                    price_txt = listing.find("div", class_="pl-items__item-price").strong.text.strip()
                    price_num = re.sub(r"[^\d]", "", price_txt) or "0"

                    flat_type = re.search(r"(\d\s*\+\s*\w{1,2})", title)
                    flat_type = flat_type.group(1).replace(" ", "") if flat_type else "N/A"
                    size = re.search(r"(\d+)\s*m²", title)
                    size = size.group(1) if size else "N/A"

                    all_data.append({
                        "image": image_url,
                        "locality": locality,
                        "type_of_flat": flat_type,
                        "size": size,
                        "price": int(price_num),
                        "link": link,
                    })
                except Exception as e:
                    print("Error parsing a listing:", e)

            nxt = driver.find_element(By.CSS_SELECTOR, "a.page-link[title='další']")
            if "disabled" in nxt.find_element(By.XPATH, "./parent::li").get_attribute("class"):
                print("Last page reached.")
                break
            driver.execute_script("arguments[0].click();", nxt)
            time.sleep(3)
        except Exception:
            break

    driver.quit()
    print(f"\nScraped {len(all_data)} listings.")
    records = pd.DataFrame(all_data).to_dict(orient="records")
    for idx, r in enumerate(records, 1):
        r["uid"] = idx
        r["source"] = "remax"
    with open("remax.json", "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=4)
    print("Data saved to remax.json")

if __name__ == "__main__":
    scrape_remax()