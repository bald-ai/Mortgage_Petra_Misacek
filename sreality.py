import json, re, time, pandas as pd
from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By

# NEW
from selenium_helper import make_driver
driver = make_driver()

def scrape_sreality():
    base = ("https://www.sreality.cz/hledani/prodej/byty"
            "?velikost=2%2Bkk%2C2%2B1%2C3%2Bkk%2C3%2B1"
            "&lokality=Brno+město&cena-na=%7E8000000&plocha-na=50~80")
    driver.get(base)
    time.sleep(2)

    all_data = []
    soup = BeautifulSoup(driver.page_source, "lxml")
    for card in soup.select(".property"):
        try:
            image = card.select_one("img")["src"]
            link = "https://www.sreality.cz" + card["href"]
            title = card.select_one(".name").get_text(strip=True)
            locality = card.select_one(".locality").get_text(strip=True)
            size_match = re.search(r"(\d+)\s*m²", title)
            size = size_match.group(1) if size_match else "N/A"
            price = re.sub(r"[^\d]", "", card.select_one(".norm-price").text) or "0"
            flat_type = re.search(r"(\d\+\D+)", title)
            flat_type = flat_type.group(1) if flat_type else "N/A"

            all_data.append({
                "image": image,
                "locality": locality,
                "type_of_flat": flat_type,
                "size": size,
                "price": int(price),
                "link": link,
            })
        except Exception as e:
            print("Skip card:", e)

    driver.quit()
    for idx, rec in enumerate(all_data, 1):
        rec["uid"] = idx
        rec["source"] = "sreality"
    with open("sreality.json", "w", encoding="utf-8") as f:
        json.dump(all_data, f, ensure_ascii=False, indent=4)
    print("Saved", len(all_data), "rows to sreality.json")

if __name__ == "__main__":
    scrape_sreality()