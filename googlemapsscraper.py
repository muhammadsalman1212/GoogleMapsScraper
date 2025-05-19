from playwright.sync_api import sync_playwright
import time
import csv
from urllib.parse import urlparse, parse_qs

proxy_username = ""
proxy_password = ""
proxy_url = "p.webshare.io"
proxy_port = "80"

def scrape_google_maps():
    # Ask user for Google Maps URL
    default_url = "https://www.google.com/maps/search/construction+companies+in+toronto"
    maps_url = input(f"Enter Google Maps search URL (default: {default_url}): ") or default_url

    # Ask user for scroll count
    scroll_count = int(input("Enter number of times to scroll (recommended 5-20): ") or 5)
    nameofcsv = input("Enter name of CSV file:")

    with sync_playwright() as p:
        # Launch browser with proxy
        browser = p.chromium.launch(
            headless=False,
            channel='chrome',
            proxy={
                "server": f"http://{proxy_url}:{proxy_port}",
                "username": proxy_username,
                "password": proxy_password
            }
        )
        page = browser.new_page()

        page.goto(maps_url, timeout=60000)
        print("Page loaded successfully")

        # Wait for listings to load
        page.wait_for_selector('//div[contains(@class, "Nv2PK")]', timeout=30000)
        print("Listings container found")

        # Scroll to load more listings
        for i in range(scroll_count):
            page.evaluate("""() => {
                const scrollable = document.querySelector('[role="feed"]');
                if (scrollable) scrollable.scrollTop = scrollable.scrollHeight;
            }""")
            print(f"Scrolled {i + 1} of {scroll_count} times")
            time.sleep(3)

        # Get all listing elements using XPath
        listings = page.query_selector_all('//div[contains(@class, "Nv2PK")]')
        print(f"\nFound {len(listings)} listing elements")

        results = []

        for listing in listings:
            try:
                # Extract business name
                name_element = listing.query_selector('.qBF1Pd')
                name = name_element.inner_text() if name_element else "N/A"

                # Extract business type (category) - updated selector
                business_type_element = listing.query_selector('div.W4Efsd > div.W4Efsd > span:first-child > span:first-child')
                business_type = business_type_element.inner_text() if business_type_element else "N/A"

                # Extract phone number
                phone_element = listing.query_selector('//span[contains(@class, "UsdlK")]')
                phone = phone_element.inner_text() if phone_element else "N/A"

                # Extract address - more robust selector
                address_element = listing.query_selector('//div[contains(@class, "W4Efsd")][contains(., "·")]/span[2]')
                address = address_element.inner_text().strip() if address_element else "N/A"

                # Extract website
                website_element = listing.query_selector('//a[contains(@aria-label, "website")]')
                website = website_element.get_attribute("href") if website_element else "N/A"

                # Extract Google Maps URL
                map_link_element = listing.query_selector('a.hfpxzc')
                map_url = map_link_element.get_attribute("href") if map_link_element else "N/A"

                # Extract rating
                rating_element = listing.query_selector('.MW4etd')
                rating = rating_element.inner_text() if rating_element else "N/A"

                # Extract review count
                review_count_element = listing.query_selector('.UY7F9')
                review_count = review_count_element.inner_text().strip('()') if review_count_element else "N/A"

                results.append({
                    "name": name,
                    "type": business_type,
                    "phone": phone,
                    "address": address,
                    "website": website,
                    "map_url": map_url,
                    "rating": rating,
                    "review_count": review_count
                })

            except Exception as e:
                print(f"Error processing a listing: {e}")
                continue

        # Print results to console
        print("\nSample Results:")
        for i, result in enumerate(results[:5], 1):
            print(f"\nListing {i}:")
            print(f"Name: {result['name']}")
            print(f"Type: {result['type']}")
            print(f"Phone: {result['phone']}")
            print(f"Address: {result['address']}")
            print(f"Website: {result['website']}")
            print(f"Rating: {result['rating']}")
            print(f"Reviews: {result['review_count']}")
            print(f"Google Maps URL: {result['map_url']}")

        print(f"\nTotal listings scraped: {len(results)}")

        # Save to CSV
        if results:
            filename = f"{nameofcsv}.csv"

            with open(filename, mode='w', newline='', encoding='utf-8') as file:
                writer = csv.DictWriter(file, fieldnames=results[0].keys())
                writer.writeheader()
                writer.writerows(results)

            print(f"\nAll results saved to: {filename}")

        browser.close()

scrape_google_maps()