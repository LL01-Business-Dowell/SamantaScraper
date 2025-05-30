from fastapi import FastAPI, File, UploadFile, Form
from fastapi.responses import StreamingResponse
import pandas as pd
import time
import threading
import re
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, StaleElementReferenceException
import os
import json
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import traceback
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173",
                   "map.uxlivinglab.online"],  # React frontend URL
    allow_credentials=True,
    allow_methods=["*"],  # Allow all HTTP methods (GET, POST, etc.)
    allow_headers=["*"],  # Allow all headers
)

tasks = {}


def log_message(message):
    """Add message to logs and print it"""
    timestamp = datetime.datetime.now().strftime('%H:%M:%S')
    log_entry = f"[{timestamp}] {message}"
    print(log_entry)
    # Add to a global log list if needed for status updates
    # scraping_status['logs'].append(log_entry)


def smart_sleep(min_sec=7, max_sec=10, reason=""):
    delay = random.uniform(min_sec, max_sec)
    log_message(f"⏳ Sleeping for {delay:.2f}s {reason}")
    time.sleep(delay)


def clean_text(text):
    """Clean and sanitize text extracted from the webpage"""
    if text:
        text = re.sub(r"[^\x20-\x7E]", "", text)
        return text.strip()
    return "N/A"


def safe_find_element(driver, by, value, timeout=5):
    """Safely find element with retry logic"""
    try:
        return WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((by, value))
        )
    except TimeoutException:
        return None


def safe_find_elements(driver, by, value, timeout=5):
    """Safely find elements with retry logic"""
    try:
        WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((by, value))
        )
        return driver.find_elements(by, value)
    except TimeoutException:
        return []


def init_driver():
    """Initializes and returns a Selenium WebDriver instance with improved error handling."""
    options = Options()
    options.add_argument("--headless=new")  # New headless mode
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument(
        "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.7049.85 Safari/537.36")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)

    print("  🌐 Setting up Chrome driver...")

    try:
        from webdriver_manager.chrome import ChromeDriverManager
        from selenium.webdriver.chrome.service import Service as ChromeService

        print("  🔄 Using WebDriver Manager to get compatible chromedriver...")
        service = ChromeService(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        print("  ✓ Chrome driver created successfully with WebDriver Manager")
        return driver
    except Exception as e:
        print(f"  ℹ️ WebDriver Manager approach failed: {e}")
        print("  🔄 Trying direct ChromeDriver creation...")

        try:
            driver = webdriver.Chrome(options=options)
            print("  ✓ Chrome driver created successfully")
            return driver
        except Exception as e:
            print(f"  ❌ Direct ChromeDriver creation failed: {e}")
            print("  🔄 Trying alternative approach with explicit service...")

            try:
                current_dir = os.path.dirname(os.path.abspath(__file__))
                possible_driver_paths = [
                    os.path.join(current_dir, "chromedriver"),
                    os.path.join(current_dir, "chromedriver.exe"),
                    "/opt/homebrew/bin/chromedriver",
                    "/usr/local/bin/chromedriver",
                    "chromedriver",
                    "chromedriver.exe"
                ]

                for driver_path in possible_driver_paths:
                    if os.path.exists(driver_path):
                        print(f"  🔍 Found chromedriver at: {driver_path}")
                        service = Service(executable_path=driver_path)
                        driver = webdriver.Chrome(service=service, options=options)
                        print("  ✓ Chrome driver created with explicit path")
                        return driver

                print("  ❌ No chromedriver found in common locations")
                print(
                    f"  ⚠️ Please download chromedriver version 135.0.7049.95 for Chrome {options.binary_location}")
                print("  ⚠️ from https://chromedriver.chromium.org/downloads")
                print("  ⚠️ and place it in the same directory as this script")
                return None
            except Exception as e2:
                print(f"  ❌ All ChromeDriver approaches failed: {e2}")
                return None


def extract_restaurant_details(driver, url):
    """Extract details from the restaurant page currently open in the driver"""
    details = {
        "Google Maps Link": url,
        "Name": "N/A",
        "Address": "N/A",
        "Phone": "N/A",
        "Rating": "N/A",
        "Reviews": "N/A",
        "Reviews_Count": 0,
        "Plus Code": "N/A",
        "Website": "N/A",
        "Category": "N/A",
        "Hours": "N/A",
        "Has_Multiple_Locations": False,
        "Has_Contact_Info": False,
        "Has_Sufficient_Reviews": False,
        "Has_Working_Hours": False
    }

    try:
        # Extract name with retry logic
        name_elem = safe_find_element(driver, By.XPATH, "//h1[contains(@class, 'DUwDvf')]")
        if name_elem:
            details["Name"] = clean_text(name_elem.text)
            log_message(f"✓ Found place name: {details['Name']}")

        # Extract address with multiple fallbacks
        address_xpaths = [
            "//button[@data-tooltip='Copy address']",
            "//span[contains(@class, 'section-info-text') and contains(text(), ',')]",
            "//div[contains(@class, 'Io6YTe') and contains(text(), ',')]",
            "//span[contains(@aria-label, 'Address')]",
            "//div[contains(@data-tooltip, 'Address')]"
        ]

        for xpath in address_xpaths:
            try:
                address_elem = safe_find_element(driver, By.XPATH, xpath)
                if address_elem:
                    details["Address"] = clean_text(address_elem.text)
                    log_message(f"✓ Found address: {details['Address']}")
                    break
            except Exception:
                continue

        # Extract phone number
        phone_xpaths = [
            "//button[@data-tooltip='Copy phone number']",
            "//span[contains(text(), '+49')]",
            "//div[contains(text(), '+49')]",
            "//span[contains(text(), 'Phone')]",
        ]

        for xpath in phone_xpaths:
            try:
                phone_elem = safe_find_element(driver, By.XPATH, xpath)
                if phone_elem:
                    details["Phone"] = clean_text(phone_elem.text)
                    log_message(f"✓ Found phone number: {details['Phone']}")
                    if details["Phone"] and details["Phone"] != "N/A":
                        details["Has_Contact_Info"] = True
                    break
            except Exception:
                continue

        # Check for WhatsApp as alternative contact
        if not details["Has_Contact_Info"]:
            whatsapp_elem = safe_find_element(driver, By.XPATH, "//a[contains(@href, 'whatsapp')]")
            if whatsapp_elem:
                details["Has_Contact_Info"] = True
                log_message("✓ Business has WhatsApp contact")

        # Extract rating
        rating_elem = safe_find_element(driver, By.XPATH, "//span[@class='MW4etd']")
        if rating_elem:
            details["Rating"] = clean_text(rating_elem.text)
            log_message(f"✓ Found rating: {details['Rating']}")

        # Extract reviews count
        reviews_elem = safe_find_element(driver, By.XPATH, "//span[@class='UY7F9']")
        if reviews_elem:
            reviews_text = clean_text(reviews_elem.text)
            details["Reviews"] = reviews_text
            try:
                numeric_reviews = re.sub(r'[^0-9.]', '', reviews_text)
                if numeric_reviews:
                    details["Reviews_Count"] = int(float(numeric_reviews))
                    if details["Reviews_Count"] >= 25:
                        details["Has_Sufficient_Reviews"] = True
                        log_message(f"✓ Has sufficient reviews: {details['Reviews_Count']}")
            except Exception:
                pass

        # Extract plus code
        plus_code_elem = safe_find_element(driver, By.XPATH, "//button[@data-tooltip='Copy plus code']")
        if plus_code_elem:
            details["Plus Code"] = clean_text(plus_code_elem.text)

        # Extract website
        website_elem = safe_find_element(driver, By.XPATH, "//a[contains(@aria-label, 'Visit') or contains(@href, 'http')]")
        if website_elem:
            details["Website"] = clean_text(website_elem.get_attribute("href"))

        # Extract category
        category_elems = safe_find_elements(driver, By.XPATH, "//button[contains(@jsaction, 'pane.rating.category')]")
        if category_elems:
            details["Category"] = clean_text(category_elems[0].text)

        # Extract hours with improved logic
        try:
            hours_dropdown = safe_find_elements(driver, By.XPATH, "//button[contains(@aria-label, 'hour') or contains(@aria-label, 'Hour') or contains(@aria-label, 'Open')]")
            if hours_dropdown:
                driver.execute_script("arguments[0].click();", hours_dropdown[0])
                smart_sleep(2, 4, "waiting for hours dropdown")

                hours_rows = safe_find_elements(driver, By.XPATH, "//table[contains(@class, 'WgFkxc')]//tr")
                if hours_rows:
                    days_hours = [clean_text(row.text) for row in hours_rows if row.text.strip()]
                    if days_hours:
                        details["Hours"] = "; ".join(days_hours)
                        details["Has_Working_Hours"] = True
                        log_message("✓ Extracted business hours")
        except Exception as e:
            log_message(f"✗ Error extracting hours: {e}")

        # Check for multiple locations
        location_elems = safe_find_elements(driver, By.XPATH, "//a[contains(text(), 'location') or contains(text(), 'branch') or contains(text(), 'View all')]")
        chain_elems = safe_find_elements(driver, By.XPATH, "//span[contains(text(), 'chain') or contains(text(), 'branches')]")

        if location_elems or chain_elems:
            details["Has_Multiple_Locations"] = True
            log_message("✗ Business has multiple locations/branches")

    except Exception as e:
        log_message(f"❌ Error extracting details: {e}")
        details["Error"] = str(e)

    return details


def scrape_Maps(task_id, location_data, keyword):
    driver = init_driver()
    results = []

    for idx, (postal_code, city, country) in enumerate(location_data):
        if not tasks.get(task_id, {}).get("running", False):
            print(f"Task {task_id} canceled. Exiting scraping process.")
            driver.quit()
            return

        search_query = f"{keyword} in {postal_code}, {city}, {country}"
        Maps_url = f"https://www.google.com/maps/search/{search_query.replace(' ', '+')}"

        try:
            driver.get(Maps_url)
            smart_sleep(8, 12, "for search results to load")

            results_container = safe_find_element(driver, By.XPATH, "//div[@role='feed']", 15)
            if not results_container:
                log_message(f"⚠️ Couldn't find results container for pincode {postal_code}")
                continue

            processed_count = 0
            max_iterations = 30
            same_count_iterations = 0
            previous_results_count = 0

            for scroll_iteration in range(max_iterations):
                if not tasks.get(task_id, {}).get("running", False):
                    log_message("🛑 Scraping stopped by user")
                    break

                time.sleep(2)
                result_items = safe_find_elements(driver, By.XPATH, "//div[@role='feed']/div[.//h3 or .//a[contains(@href, '/maps/place/')]]")

                if not result_items:
                    log_message("No results found, trying alternative selector")
                    result_items = safe_find_elements(driver, By.XPATH, "//div[@role='feed']//div[contains(@class, 'Nv2PK')]")

                current_count = len(result_items)
                log_message(f"📊 Found {current_count} results (scroll {scroll_iteration+1}/{max_iterations})")

                if current_count == previous_results_count:
                    same_count_iterations += 1
                    if same_count_iterations >= 3:
                        log_message("🛑 Reached end of results")
                        break
                else:
                    same_count_iterations = 0

                previous_results_count = current_count

                results_to_process = result_items[processed_count:]

                for item_idx, item in enumerate(results_to_process):
                    if not tasks.get(task_id, {}).get("running", False):
                        break

                    name = "N/A"
                    restaurant_url = None

                    try:
                        name_elem = item.find_element(By.XPATH, ".//div[contains(@class, 'fontHeadlineSmall')] | .//h3 | .//span[contains(@class, 'qBF1Pd')]")
                        name = clean_text(name_elem.text) if name_elem else "N/A"
                    except:
                        pass

                    try:
                        url_elem = item.find_element(By.XPATH, ".//a[contains(@href, '/maps/place/')]")
                        restaurant_url = url_elem.get_attribute("href")
                    except:
                        continue

                    if restaurant_url in [r["URL"] for r in results]: # Check against already collected URLs
                        continue

                    log_message(f"📍 Processing result {processed_count + item_idx + 1}: {name}")

                    driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", url_elem)
                    time.sleep(1)

                    click_successful = False
                    for attempt in range(3):
                        try:
                            driver.execute_script("arguments[0].click();", url_elem)
                            WebDriverWait(driver, 10).until(
                                EC.presence_of_element_located((By.XPATH, "//h1[contains(@class, 'DUwDvf')]"))
                            )
                            click_successful = True
                            break
                        except Exception as e:
                            log_message(f"Click attempt {attempt + 1} failed: {e}")
                            time.sleep(2)

                    if not click_successful:
                        log_message("Failed to click on result after multiple attempts")
                        continue

                    smart_sleep(5, 7, "for restaurant details to load")

                    details = extract_restaurant_details(driver, restaurant_url)

                    data_row = {
                        "Postal Code": postal_code,
                        "Name": details.get("Name", "N/A"),
                        "Address": details.get("Address", "N/A"),
                        "Phone": details.get("Phone", "N/A"),
                        "Website": details.get("Website", "N/A"),
                        "URL": restaurant_url,
                        "City": city,
                        "Country": country,
                        "Rating": details.get("Rating", "N/A"),
                        "Reviews": details.get("Reviews", "N/A"),
                        "Reviews_Count": details.get("Reviews_Count", 0),
                        "Plus Code": details.get("Plus Code", "N/A"),
                        "Category": details.get("Category", "N/A"),
                        "Hours": details.get("Hours", "N/A"),
                        "Has_Multiple_Locations": details.get("Has_Multiple_Locations", False),
                        "Has_Contact_Info": details.get("Has_Contact_Info", False),
                        "Has_Sufficient_Reviews": details.get("Has_Sufficient_Reviews", False),
                        "Has_Working_Hours": details.get("Has_Working_Hours", False),
                    }
                    results.append(data_row)
                    processed_count += 1
                    tasks[task_id]["progress"] = (processed_count / current_count) * 100 if current_count > 0 else 0
                    tasks[task_id]["results"] = results

                    driver.back()
                    smart_sleep(4, 6, "after going back to search results")

                    results_container = safe_find_element(driver, By.XPATH, "//div[@role='feed']", 10)
                    if not results_container:
                        log_message("Lost results container, breaking")
                        break

                try:
                    driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight", results_container)
                    smart_sleep(5, 8, "after scrolling to load more results")
                except Exception as e:
                    log_message(f"Error scrolling: {e}")
                    break

        except Exception as e:
            print(f"Error accessing {Maps_url}: {e}")
            continue

    driver.quit()
    tasks[task_id]["running"] = False


def scrape_Maps_location(task_id, keyword, country, city):
    driver = init_driver()

    if not tasks.get(task_id, {}).get("running", False):
        print(f"Task {task_id} canceled. Exiting scraping process.")
        driver.quit()
        return

    search_query = f"{keyword} in {city}, {country}"
    Maps_url = f"https://www.google.com/maps/search/{search_query.replace(' ', '+')}"

    try:
        driver.get(Maps_url)
        smart_sleep(8, 12, "for search results to load")


        extracted_urls = set()
        results = []
        total_count = 0

        # Wait for results container
        results_container = safe_find_element(driver, By.XPATH, "//div[@role='feed']", 15)
        if not results_container:
            log_message(f"⚠️ Couldn't find results container for {city}, {country}")
            driver.quit()
            return

        max_iterations = 30
        same_count_iterations = 0
        previous_results_count = 0

        for scroll_iteration in range(max_iterations):
            if not tasks.get(task_id, {}).get("running", False):
                log_message("🛑 Scraping stopped by user")
                break

            time.sleep(2)
            result_items = safe_find_elements(driver, By.XPATH, "//div[@role='feed']/div[.//h3 or .//a[contains(@href, '/maps/place/')]]")

            if not result_items:
                log_message("No results found, trying alternative selector")
                result_items = safe_find_elements(driver, By.XPATH, "//div[@role='feed']//div[contains(@class, 'Nv2PK')]")

            current_count = len(result_items)
            log_message(f"📊 Found {current_count} results (scroll {scroll_iteration+1}/{max_iterations})")

            if current_count == previous_results_count:
                same_count_iterations += 1
                if same_count_iterations >= 3:
                    log_message("🛑 Reached end of results")
                    break
            else:
                same_count_iterations = 0

            previous_results_count = current_count

            results_to_process = result_items[total_count:] # Process only new items

            for item_idx, item in enumerate(results_to_process):
                if not tasks.get(task_id, {}).get("running", False):
                    break

                name = "N/A"
                restaurant_url = None

                try:
                    name_elem = item.find_element(By.XPATH, ".//div[contains(@class, 'fontHeadlineSmall')] | .//h3 | .//span[contains(@class, 'qBF1Pd')]")
                    name = clean_text(name_elem.text) if name_elem else "N/A"
                except:
                    pass

                try:
                    url_elem = item.find_element(By.XPATH, ".//a[contains(@href, '/maps/place/')]")
                    restaurant_url = url_elem.get_attribute("href")
                except:
                    continue

                if restaurant_url in extracted_urls:
                    continue

                extracted_urls.add(restaurant_url)

                log_message(f"📍 Processing result {total_count + item_idx + 1}: {name}")

                driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", url_elem)
                time.sleep(1)

                click_successful = False
                for attempt in range(3):
                    try:
                        driver.execute_script("arguments[0].click();", url_elem)
                        WebDriverWait(driver, 10).until(
                            EC.presence_of_element_located((By.XPATH, "//h1[contains(@class, 'DUwDvf')]"))
                        )
                        click_successful = True
                        break
                    except Exception as e:
                        log_message(f"Click attempt {attempt + 1} failed: {e}")
                        time.sleep(2)

                if not click_successful:
                    log_message("Failed to click on result after multiple attempts")
                    continue

                smart_sleep(5, 7, "for business details to load")

                details = extract_restaurant_details(driver, restaurant_url)

                business_data = {
                    "Name": details.get("Name", "N/A"),
                    "Address": details.get("Address", "N/A"),
                    "Phone": details.get("Phone", "N/A"),
                    "Website": details.get("Website", "N/A"),
                    "URL": restaurant_url,
                    "City": city,
                    "Country": country,
                    "Rating": details.get("Rating", "N/A"),
                    "Reviews": details.get("Reviews", "N/A"),
                    "Reviews_Count": details.get("Reviews_Count", 0),
                    "Plus Code": details.get("Plus Code", "N/A"),
                    "Category": details.get("Category", "N/A"),
                    "Hours": details.get("Hours", "N/A"),
                    "Has_Multiple_Locations": details.get("Has_Multiple_Locations", False),
                    "Has_Contact_Info": details.get("Has_Contact_Info", False),
                    "Has_Sufficient_Reviews": details.get("Has_Sufficient_Reviews", False),
                    "Has_Working_Hours": details.get("Has_Working_Hours", False),
                }
                results.append(business_data)
                total_count += 1
                tasks[task_id]["progress"] = total_count
                tasks[task_id]["results"] = results

                driver.back()
                smart_sleep(4, 6, "after going back to search results")

                results_container = safe_find_element(driver, By.XPATH, "//div[@role='feed']", 10)
                if not results_container:
                    log_message("Lost results container, breaking")
                    break

            try:
                driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight", results_container)
                smart_sleep(5, 8, "after scrolling to load more results")
            except Exception as e:
                log_message(f"Error scrolling: {e}")
                break

    except Exception as e:
        print(f"Error accessing {Maps_url}: {e}")

    driver.quit()
    tasks[task_id]["running"] = False
    print(f"Task {task_id} completed successfully.")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
JSON_FOLDER = os.path.join(BASE_DIR, "data", "countries")


@app.get("/countries")
def get_countries():
    try:
        countries = sorted(
            [f[:-5] for f in os.listdir(JSON_FOLDER) if f.endswith(".json")])
        return {"countries": countries}

    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.get("/cities/{country}")
def get_cities(country: str):
    try:
        country_files = {f.lower(): f for f in os.listdir(
            JSON_FOLDER) if f.endswith(".json")}

        country_filename = country.lower() + ".json"
        if country_filename not in country_files:
            return JSONResponse(status_code=404, content={"error": f"Country '{country}' not found"})

        file_path = os.path.join(JSON_FOLDER, country_files[country_filename])

        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        cities = [
            city["ASCII Name"]
            for city in data
            # Convert population to int
            if int(city.get("Population", 0)) > 100000
        ]

        if not cities:
            return JSONResponse(status_code=200, content={"message": "No cities with population greater than 100000"})

        return {"cities": cities}

    except ValueError as e:
        return JSONResponse(status_code=500, content={"error": f"Invalid population data: {str(e)}"})

    except json.JSONDecodeError:
        return JSONResponse(status_code=500, content={"error": "Invalid JSON format in file"})

    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.post("/upload/")
async def upload_csv(file: UploadFile, keyword: str = Form(...), email: str = Form(...)):
    task_id = str(time.time())
    df = pd.read_csv(file.file)

    location_data = []
    for index, row in df.iterrows():
        postal_code = str(row.iloc[0]) if not pd.isna(row.iloc[0]) else ""
        city = str(row.iloc[1]) if not pd.isna(row.iloc[1]) else ""
        country = str(row.iloc[2]) if not pd.isna(row.iloc[2]) else ""

        location_data.append([postal_code, city, country])

    tasks[task_id] = {"running": True, "progress": 0, "results": []}

    threading.Thread(target=scrape_Maps, args=(
        task_id, location_data, keyword)).start()

    return {"message": "Processing started", "task_id": task_id}


@app.post("/search-by-location/")
async def upload_csv(keyword: str = Form(...), country: str = Form(...), city: str = Form(...), email: str = Form(...)):
    task_id = str(time.time())

    tasks[task_id] = {"running": True, "progress": 0, "results": []}

    threading.Thread(target=scrape_Maps_location, args=(
        task_id, keyword, country, city)).start()

    return {"message": "Processing started", "task_id": task_id}


@app.get("/progress/{task_id}")
async def get_progress(task_id: str):
    if task_id in tasks:
        task = tasks[task_id]
        return {
            "progress": task.get("progress", 0),
            "results": task.get("results", []),
            "running": task.get("running", False),
        }
    return {"error": "Task not found"}


@app.post("/cancel/{task_id}")
def cancel_task(task_id: str):
    if task_id in tasks:
        tasks[task_id]["running"] = False
        time.sleep(1)
        del tasks[task_id]
        return {"message": f"Task {task_id} has been canceled"}
    return JSONResponse(status_code=404, content={"error": "Task not found"})


@app.get("/download/{task_id}")
def download_results(task_id: str):
    if task_id not in tasks or not tasks[task_id]["results"]:
        return {"error": "No results found"}

    def iter_csv():
        # Create header row with all columns
        yield "Postal Code,Name,Address,Phone,Website,URL,City,Country,Rating,Reviews,Reviews_Count,Plus Code,Category,Hours,Has_Multiple_Locations,Has_Contact_Info,Has_Sufficient_Reviews,Has_Working_Hours\n"

        for row in tasks[task_id]["results"]:
            # Properly escape fields that might contain commas
            postal_code = f'"{row["Postal Code"]}"'
            name = f'"{row["Name"]}"'
            address = f'"{row["Address"]}"'
            phone = f'"{row["Phone"]}"'
            website = f'"{row["Website"]}"'
            url = f'"{row["URL"]}"'
            city = f'"{row["City"]}"'
            country = f'"{row["Country"]}"'
            rating = f'"{row["Rating"]}"'
            reviews = f'"{row["Reviews"]}"'
            reviews_count = f'"{row["Reviews_Count"]}"'
            plus_code = f'"{row["Plus Code"]}"'
            category = f'"{row["Category"]}"'
            hours = f'"{row["Hours"]}"'
            has_multiple_locations = f'"{row["Has_Multiple_Locations"]}"'
            has_contact_info = f'"{row["Has_Contact_Info"]}"'
            has_sufficient_reviews = f'"{row["Has_Sufficient_Reviews"]}"'
            has_working_hours = f'"{row["Has_Working_Hours"]}"'


            yield f"{postal_code},{name},{address},{phone},{website},{url},{city},{country},{rating},{reviews},{reviews_count},{plus_code},{category},{hours},{has_multiple_locations},{has_contact_info},{has_sufficient_reviews},{has_working_hours}\n"

    return StreamingResponse(iter_csv(), media_type="text/csv",
                             headers={"Content-Disposition": f"attachment; filename=results_{task_id}.csv"})


@app.get("/download-search/{task_id}")
def download_search_results(task_id: str):
    if task_id not in tasks or not tasks[task_id]["results"]:
        return {"error": "No results found"}

    def iter_csv():
        # Correct header with all columns
        yield "Name,Address,Phone,Website,URL,City,Country,Rating,Reviews,Reviews_Count,Plus Code,Category,Hours,Has_Multiple_Locations,Has_Contact_Info,Has_Sufficient_Reviews,Has_Working_Hours\n"

        for row in tasks[task_id]["results"]:
            # Properly escape fields that might contain commas
            name = f'"{row["Name"]}"'
            address = f'"{row["Address"]}"'
            phone = f'"{row["Phone"]}"'
            website = f'"{row["Website"]}"'
            url = f'"{row["URL"]}"'
            city = f'"{row["City"]}"'
            country = f'"{row["Country"]}"'
            rating = f'"{row["Rating"]}"'
            reviews = f'"{row["Reviews"]}"'
            reviews_count = f'"{row["Reviews_Count"]}"'
            plus_code = f'"{row["Plus Code"]}"'
            category = f'"{row["Category"]}"'
            hours = f'"{row["Hours"]}"'
            has_multiple_locations = f'"{row["Has_Multiple_Locations"]}"'
            has_contact_info = f'"{row["Has_Contact_Info"]}"'
            has_sufficient_reviews = f'"{row["Has_Sufficient_Reviews"]}"'
            has_working_hours = f'"{row["Has_Working_Hours"]}"'


            yield f"{name},{address},{phone},{website},{url},{city},{country},{rating},{reviews},{reviews_count},{plus_code},{category},{hours},{has_multiple_locations},{has_contact_info},{has_sufficient_reviews},{has_working_hours}\n"

    return StreamingResponse(iter_csv(), media_type="text/csv",
                             headers={"Content-Disposition": f"attachment; filename=results_{task_id}.csv"})


if __name__ == "__main__":
    import uvicorn
    import datetime
    import random
    uvicorn.run(app, host="0.0.0.0", port=8000)