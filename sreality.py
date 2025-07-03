import json, re, time, pandas as pd
from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException

from selenium_helper import make_driver


def scrape_sreality():
    """Login to Seznam.cz, then scrape listings from Sreality.cz (Brno flats).

    The function logs progress to stdout so we can debug where it might stall.
    """
    # --- Config ----------------------------------------------------------
    login_url = "https://login.szn.cz/"
    base_url = "https://www.sreality.cz/hledani/prodej/byty?velikost=2%2B1%2C2%2Bkk%2C3%2B1%2C3%2Bkk&cena-do=8000000&plocha-od=50&region=Brno&region-id=5740&region-typ=municipality"
    email = "baldai@hey.com"
    password = "Seznam236"

    # --------------------------------------------------------------------
    driver = make_driver()
    try:
        # -------------------- Step 1: Log-in -----------------------------
        print(f"DEBUG: Navigating to login page → {login_url}")
        driver.get(login_url)
        time.sleep(2)

        driver.find_element(By.ID, "login-username").send_keys(email)
        driver.find_element(By.CSS_SELECTOR, "button[data-locale='login.submit']").click()
        print("DEBUG: Username submitted")

        time.sleep(2)
        driver.find_element(By.ID, "login-password").send_keys(password)
        driver.find_element(By.CSS_SELECTOR, "button[data-locale='login.submit']").click()
        print("DEBUG: Password submitted, awaiting authentication…")
        time.sleep(5)

        # -------------------- Step 2: Scrape -----------------------------
        print(f"DEBUG: Login OK, navigating to search URL → {base_url}")
        driver.get(base_url)
        time.sleep(5)  # allow initial results to load

        all_data: list[dict] = []
        page_num = 1

        while True:
            print(f"\n--- Scraping Page {page_num} ---")
            time.sleep(2)

            # Listing cards are lazy-loaded; pull them via Selenium then parse
            listings = driver.find_elements(By.CSS_SELECTOR, "li.MuiGrid2-root.MuiGrid2-direction-xs-row")
            print(f"DEBUG: Found {len(listings)} listing elements on this page")

            if not listings:
                print("DEBUG: No listings found → stopping scrape")
                break

            for idx, element in enumerate(listings, 1):
                try:
                    # Ensure lazy images are loaded
                    driver.execute_script(
                        "arguments[0].scrollIntoView({block: 'center', inline: 'nearest'});",
                        element,
                    )
                    time.sleep(0.3)

                    html = element.get_attribute("outerHTML")
                    soup = BeautifulSoup(html, "lxml")

                    link_anchor = soup.find("a", class_="css-1s6ohwi")
                    if not link_anchor:
                        continue

                    href = link_anchor.get("href", "")
                    link = (
                        f"https://www.sreality.cz{href}" if href.startswith("/") else href or "N/A"
                    )

                    img_tag = link_anchor.find("img", class_="css-f5kes")
                    image_url = (
                        img_tag.get("srcset", "").split(" ")[0] if img_tag else "N/A"
                    )
                    if image_url.startswith("//"):
                        image_url = f"https:{image_url}"

                    text_block = link_anchor.find("div", class_="css-173t8lh")
                    if not text_block:
                        continue

                    info_pars = text_block.find_all("p", class_="css-d7upve")
                    price_par = text_block.find("p", class_="css-ca9wwd")

                    title_text = info_pars[0].get_text(strip=True) if info_pars else "N/A"
                    locality = info_pars[1].get_text(strip=True) if len(info_pars) > 1 else "N/A"
                    price_text = price_par.get_text(strip=True) if price_par else "0"
                    price = re.sub(r"[^\d]", "", price_text) or "0"

                    # Derive flat type and size from title
                    flat_type = "N/A"
                    size = "N/A"
                    if title_text:
                        if m := re.search(r"(\d\s*\+\s*\w{1,2})", title_text):
                            flat_type = m.group(1).replace(" ", "")
                        if m := re.search(r"(\d+)\s*m²", title_text):
                            size = m.group(1)

                    record = {
                        "image": image_url,
                        "locality": locality,
                        "type_of_flat": flat_type,
                        "size": size,
                        "price": int(price),
                        "link": link,
                    }
                    all_data.append(record)

                    print(f"DEBUG: [{len(all_data)}] Extracted → {record}")
                except Exception as e:
                    print(f"WARN: Error parsing listing #{idx} on page {page_num}: {e}")

            # --------------- Pagination ------------------------------
            try:
                next_btn = driver.find_element(By.CSS_SELECTOR, "button[data-e2e='show-more-btn']")
                driver.execute_script("arguments[0].click();", next_btn)
                page_num += 1
                time.sleep(5)
            except NoSuchElementException:
                print("DEBUG: No 'Show more' button → reached last page")
                break
            except Exception as e:
                print(f"WARN: Failed to go to next page: {e}")
                break

        # -------------------- Step 3: Save -----------------------------
        print("\n--- Scraping complete ---")
        print(f"Total listings scraped: {len(all_data)}")

        # Add uid & source
        for idx, rec in enumerate(all_data, start=1):
            rec["uid"] = idx
            rec["source"] = "sreality"

        out_file = "sreality.json"
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(all_data, f, ensure_ascii=False, indent=4)
        print(f"Data saved to {out_file}")

    finally:
        driver.quit()


if __name__ == "__main__":
    scrape_sreality()