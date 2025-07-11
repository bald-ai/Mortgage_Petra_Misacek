import requests
import json
import re

# Use a Session object to automatically handle cookies and headers
session = requests.Session()

def process_listings(raw_data):
    """
    Processes the raw API output and transforms it into the desired JSON format with validation.
    """
    processed_listings = []
    uid_counter = 1  # Sequential UID counter for consistency with other scrapers
    
    # A mapping to convert API disposition values to a user-friendly format
    disposition_map = {
        "onePlusKk": "1+kk",
        "onePlusOne": "1+1",
        "twoPlusKk": "2+kk",
        "twoPlusOne": "2+1",
        "threePlusKk": "3+kk",
        "threePlusOne": "3+1",
        "fourPlusKk": "4+kk",
        "fourPlusOne": "4+1",
        "fivePlusKk": "5+kk",
        "fiveAndMore": "5+",
        "atypical": "Atypický"
    }

    # Safely access the offers list from the raw data
    offers = raw_data.get('data', {}).get('offers', [])

    for listing in offers:
        # --- Safely extract and format data for each field ---
        
        # Build the locality string from its parts
        street = listing.get('street', {}).get('title', '')
        village = listing.get('village', {}).get('title', '')
        village_part = listing.get('villagePart', {}).get('title', '')
        locality_parts = [part for part in [street, f"{village} - {village_part}"] if part and part.strip() != '-']
        locality = ", ".join(locality_parts)

        # Get the first photo, or provide a default if none exist
        image_url = (listing.get('photos') or [{}])[0].get('path', 'No Image Available')
        
        # Validate Size: Use "N/A" if area is not a number or is 0.
        area_value = listing.get('area')
        if isinstance(area_value, (int, float)) and area_value > 0:
            size_output = str(area_value)
        else:
            size_output = "N/A"

        # Validate Price: Use "Something weird" if price is null.
        price_value = (listing.get('rentalPrice') or {}).get('value')
        # Ensure price is an integer if possible, otherwise None
        if isinstance(price_value, str):
            price_digits = re.sub(r'\D', '', price_value)
            price_output = int(price_digits) if price_digits else None
        elif isinstance(price_value, (int, float)):
            price_output = int(price_value)
        else:
            price_output = None
        
        # Create the dictionary for the current listing in the desired format
        processed_listing = {
            "uid": uid_counter,
            "link": listing.get('absoluteUrl', ''),
            "type_of_flat": disposition_map.get(listing.get('disposition'), 'N/A'),
            "size": size_output,
            "price": price_output,
            "locality": locality,
            "image": image_url,
            "source": "ulov_domov"
        }
        processed_listings.append(processed_listing)
        uid_counter += 1  # Increment for next listing
        
    return processed_listings

def main(output_filename="ud.json"):
    # --- Step 1: Log In to Get the Token ---

    login_url = 'https://www.ulovdomov.cz/fe-api/auth/login'
    login_payload = {
        'email': 'baldai@hey.com',
        'password': 'krookboh64'
    }
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36',
        'Content-Type': 'application/json'
    })

    print("▶️ Attempting to log in...")
    try:
        login_response = session.post(login_url, json=login_payload)
        login_response.raise_for_status()
        login_data = login_response.json()
        bearer_token = login_data['accessToken']
        # Add the Bearer token to the session's headers for all subsequent requests
        session.headers.update({'Authorization': f'Bearer {bearer_token}'})
        print("✅ Successfully logged in and set the token for this session.")

    except requests.exceptions.RequestException as e:
        print(f"❌ Login failed: {e}")
        return # Exit the function if login fails

    # --- Step 2: Use the Token to Get Listings ---

    find_url = "https://ud.api.ulovdomov.cz/v1/offer/find"
    find_payload = {
        "bounds": {
            "northEast": {"lat": 49.294485, "lng": 16.7278532},
            "southWest": {"lat": 49.1096552, "lng": 16.4280678}
        },
        "disposition": ["twoPlusKk", "twoPlusOne", "threePlusKk", "threePlusOne"],
        "floorArea": {"max": 80, "min": 50},
        "offerType": "sale",
        "price": {"max": 8000000},
        "propertyType": "flat"
    }

    print("▶️ Fetching listings with the new token...")
    try:
        data_response = session.post(find_url, params={'page': 1, 'perPage': 35}, json=find_payload)
        data_response.raise_for_status()
        raw_data = data_response.json()
        print("✅ Successfully fetched raw listing data.")

        # --- Step 3: Process the Raw Data and Save to a New JSON File ---
        
        print("▶️ Processing raw data into the desired format...")
        processed_data = process_listings(raw_data)
        
        # Save the processed data to listings.json
        with open(output_filename, "w", encoding="utf-8") as f:
            json.dump(processed_data, f, indent=4, ensure_ascii=False)
        print(f"✅ Success! {len(processed_data)} listings saved to {output_filename}.")

    except requests.exceptions.RequestException as e:
        print(f"❌ Could not fetch listings: {e}")
    except json.JSONDecodeError:
        print("❌ Failed to decode JSON from the response.")

def scrape_api_ud():
    """Wrapper function for pipeline integration."""
    main("api_ud.json")

if __name__ == "__main__":
    main()