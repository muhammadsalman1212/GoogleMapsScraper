from playwright.sync_api import sync_playwright
import time
import csv
import os
from urllib.parse import urlparse, parse_qs

proxy_username = "fwizxhyz-US-GB-CA-rotate"
proxy_password = "2fnj73wxslov"
proxy_url = "p.webshare.io"
proxy_port = "80"



def check_or_create_input_csv():
    """Check if input CSV exists, if not create it and prompt user to add links"""
    input_csv = "input_links.csv"

    if not os.path.exists(input_csv):
        print(f"'{input_csv}' file not found. Creating it now...")
        print("Please add Google Maps links to this file (one URL per line) and run the script again.")

        # Create the CSV with example link
        with open(input_csv, 'w', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerow(["https://www.google.com/maps/search/construction+companies+in+toronto"])

        print(f"Created '{input_csv}' with an example link. Please edit it and add your target URLs.")
        return False
    return True


def get_links_from_csv():
    """Read Google Maps links from the input CSV file"""
    input_csv = "input_links.csv"

    try:
        with open(input_csv, mode='r', encoding='utf-8') as file:
            reader = csv.reader(file)
            links = [row[0].strip() for row in reader if row and row[0].startswith('http')]

        if not links:
            print(f"No valid links found in {input_csv}. Please add Google Maps URLs.")
            return None

        print(f"Found {len(links)} links in {input_csv}")
        return links

    except Exception as e:
        print(f"Error reading CSV file: {e}")
        return None


def scrape_single_page(page, url, scroll_count):
    """Scrape data from a single Google Maps page"""
    try:
        page.goto(url, timeout=60000)
        print(f"Page loaded successfully: {url}")
    except Exception as e:
        print(f"Error loading page {url}: {e}")
        return []

    # Wait for listings to load
    try:
        page.wait_for_selector('//div[contains(@class, "Nv2PK")]', timeout=30000)
        print("Listings container found")
    except Exception as e:
        print(f"Error waiting for listings: {e}")
        return []

    # Scroll to load more listings
    for i in range(scroll_count):
        try:
            page.evaluate("""() => {
                const scrollable = document.querySelector('[role="feed"]');
                if (scrollable) scrollable.scrollTop = scrollable.scrollHeight;
            }""")
            print(f"Scrolled {i + 1} of {scroll_count} times")
            time.sleep(3)
        except Exception as e:
            print(f"Error during scrolling: {e}")
            break

    # Get all listing elements using XPath
    try:
        listings = page.query_selector_all('//div[contains(@class, "Nv2PK")]')
        print(f"Found {len(listings)} listing elements")
    except Exception as e:
        print(f"Error finding listings: {e}")
        return []

    results = []

    for listing in listings:
        try:
            # Extract business name
            name_element = listing.query_selector('.qBF1Pd')
            name = name_element.inner_text() if name_element else "N/A"

            # Extract business type (category) - updated selector
            business_type_element = listing.query_selector(
                'div.W4Efsd > div.W4Efsd > span:first-child > span:first-child')
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
                "review_count": review_count,
                "source_url": url  # Track which URL this came from
            })

        except Exception as e:
            print(f"Error processing a listing: {e}")
            continue

    return results


def save_to_csv(results, filename):
    """Save results to CSV, creating file if it doesn't exist or appending if it does"""
    if not results:
        return

    file_exists = os.path.isfile(filename)

    try:
        with open(filename, mode='a+' if file_exists else 'w', newline='', encoding='utf-8') as file:
            writer = csv.DictWriter(file, fieldnames=results[0].keys())

            if not file_exists:
                writer.writeheader()

            writer.writerows(results)

    except Exception as e:
        print(f"Error saving to CSV: {e}")


def scrape_google_maps():
    # First check if input CSV exists
    if not check_or_create_input_csv():
        return  # Exit if we just created the CSV

    # Get input parameters
    scroll_count = int(input("Enter number of times to scroll (recommended 5-20): ") or 5)
    output_csv = input("Enter name of output CSV file (default: output_data.csv): ") or "output_data.csv"

    # Get links to scrape
    maps_urls = get_links_from_csv()
    if not maps_urls:
        return

    all_results = []

    with sync_playwright() as p:
        # Launch browser with proxy
        try:
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

            # Process each URL
            for url in maps_urls:
                print(f"\nProcessing URL: {url}")
                results = scrape_single_page(page, url, scroll_count)
                if results:
                    all_results.extend(results)
                    print(f"Successfully scraped {len(results)} listings from this URL")

                    # Save progress after each URL
                    save_to_csv(all_results, output_csv)
                else:
                    print(f"No results scraped from {url}")

        except Exception as e:
            print(f"Error during browser operation: {e}")
        finally:
            try:
                browser.close()
            except:
                pass

    # Final summary
    if all_results:
        print("\nSample Results:")
        for i, result in enumerate(all_results[:5], 1):
            print(f"\nListing {i}:")
            print(f"Name: {result['name']}")
            print(f"Type: {result['type']}")
            print(f"Phone: {result['phone']}")
            print(f"Address: {result['address']}")
            print(f"Website: {result['website']}")
            print(f"Rating: {result['rating']}")
            print(f"Reviews: {result['review_count']}")
            print(f"Google Maps URL: {result['map_url']}")
            print(f"Source URL: {result['source_url']}")

        print(f"\nTotal listings scraped from all URLs: {len(all_results)}")
        print(f"All results saved to: {output_csv}")
    else:
        print("\nNo results were scraped from any URLs")





if __name__ == "__main__":
    scrape_google_maps()