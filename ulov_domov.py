import time, re, json, pandas as pd
from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# NEW
from selenium_helper import make_driver
driver = make_driver()

def scrape_ulov_domov():
    url = ("https://www.ulovdomov.cz/prodej/bytu/brno/2-kk?"
           "od=50m2&do=80m2&cena-do=8000000kc&dispozice=2-1%2C3-kk%2C3-1&lokace=Brno")
    driver.get(url)
    while True:
        try:
            btn = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Načíst další')]"))
            )
            driver.execute_script("arguments[0].scrollIntoView(true);", btn)
            time.sleep(1)
            driver.execute_script("arguments[0].click();", btn)
            time.sleep(3)
        except Exception:
            break

    soup = BeautifulSoup(driver.page_source, "lxml")
    listings = soup.find_all("div", attrs={"data-test": "previewOfferLeases"})
    print("Found", len(listings), "listings")

    all_data = []
    for listing in listings:
        try:
            img = listing.find("img")
            image = img["src"] if img else "N/A"
            a = listing.find("a", class_="css-1ihpi83")
            rel = a.get("href", "N/A") if a else "N/A"
            link = f"https://www.ulovdomov.cz{rel}" if rel.startswith("/") else rel
            locality = a.find("p", class_="css-adlj2b").text.strip()
            title = a.find("h2", attrs={"data-test": "headingOfLeasesPreview"}).text.strip()
            price = re.sub(r"[^\d]", "", a.find("span", class_="css-19kx31i").text) or "0"

            flat_type = re.search(r"(\d\s*\+\s*\w{1,2})", title)
            flat_type = flat_type.group(1).replace(" ", "") if flat_type else "N/A"
            size = re.search(r"(\d+)\s*m2", title)
            size = size.group(1) if size else "N/A"

            all_data.append({
                "image": image,
                "locality": locality,
                "type_of_flat": flat_type,
                "size": size,
                "price": int(price),
                "link": link,
            })
        except Exception as e:
            print("Error parsing listing:", e)

    driver.quit()
    records = pd.DataFrame(all_data).to_dict(orient="records")
    for idx, r in enumerate(records, 1):
        r["uid"] = idx
        r["source"] = "ulov_domov"
    with open("ulov_domov.json", "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=4)
    print("Saved", len(records), "rows to ulov_domov.json")

if __name__ == "__main__":
    scrape_ulov_domov()