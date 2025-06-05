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
from selenium.common.exceptions import TimeoutException, NoSuchElementException, StaleElementReferenceException, WebDriverException
import os
import json
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import traceback
import logging
import datetime
import random

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "map.uxlivinglab.online"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

tasks = {}

def log_message(message):
    """Add message to logs and print it"""
    timestamp = datetime.datetime.now().strftime('%H:%M:%S')
    log_entry = f"[{timestamp}] {message}"
    print(log_entry)
    logger.info(log_entry)

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

def safe_find_element(driver, by, value, timeout=10):
    """Safely find element with retry logic and better error handling"""
    try:
        element = WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((by, value))
        )
        return element
    except TimeoutException:
        log_message(f"Timeout waiting for element: {value}")
        return None
    except Exception as e:
        log_message(f"Error finding element {value}: {e}")
        return None

def safe_find_elements(driver, by, value, timeout=10):
    """Safely find elements with retry logic and better error handling"""
    try:
        WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((by, value))
        )
        return driver.find_elements(by, value)
    except TimeoutException:
        log_message(f"Timeout waiting for elements: {value}")
        return []
    except Exception as e:
        log_message(f"Error finding elements {value}: {e}")
        return []

def init_driver():
    """Initializes and returns a Selenium WebDriver instance with improved error handling."""
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--disable-web-security")
    options.add_argument("--disable-features=VizDisplayCompositor")
    options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.7049.85 Safari/537.36")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    
    # Add memory and performance optimizations
    options.add_argument("--memory-pressure-off")
    options.add_argument("--max_old_space_size=4096")

    log_message("🌐 Setting up Chrome driver...")

    try:
        from webdriver_manager.chrome import ChromeDriverManager
        from selenium.webdriver.chrome.service import Service as ChromeService

        log_message("🔄 Using WebDriver Manager to get compatible chromedriver...")
        service = ChromeService(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        
        # Execute script to avoid detection
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        log_message("✓ Chrome driver created successfully with WebDriver Manager")
        return driver
    except Exception as e:
        log_message(f"ℹ️ WebDriver Manager approach failed: {e}")
        log_message("🔄 Trying direct ChromeDriver creation...")

        try:
            driver = webdriver.Chrome(options=options)
            driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            log_message("✓ Chrome driver created successfully")
            return driver
        except Exception as e:
            log_message(f"❌ Direct ChromeDriver creation failed: {e}")
            return None

def extract_restaurant_details(driver, url, task_id):
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
        # Check if task is still running
        if not tasks.get(task_id, {}).get("running", False):
            return details

        # Extract name with retry logic
        name_elem = safe_find_element(driver, By.XPATH, "//h1[contains(@class, 'DUwDvf')]", 15)
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
                address_elem = safe_find_element(driver, By.XPATH, xpath, 5)
                if address_elem:
                    details["Address"] = clean_text(address_elem.text)
                    log_message(f"✓ Found address: {details['Address']}")
                    break
            except Exception:
                continue

        # Extract phone number
        phone_xpaths = [
            "//button[@data-tooltip='Copy phone number']",
            "//span[contains(text(), '+')]",
            "//div[contains(text(), '+')]",
            "//span[contains(@aria-label, 'Phone')]",
        ]

        for xpath in phone_xpaths:
            try:
                phone_elem = safe_find_element(driver, By.XPATH, xpath, 5)
                if phone_elem:
                    phone_text = clean_text(phone_elem.text)
                    if phone_text and any(char.isdigit() for char in phone_text):
                        details["Phone"] = phone_text
                        details["Has_Contact_Info"] = True
                        log_message(f"✓ Found phone number: {details['Phone']}")
                        break
            except Exception:
                continue

        # Check for WhatsApp as alternative contact
        if not details["Has_Contact_Info"]:
            try:
                whatsapp_elem = safe_find_element(driver, By.XPATH, "//a[contains(@href, 'whatsapp')]", 3)
                if whatsapp_elem:
                    details["Has_Contact_Info"] = True
                    log_message("✓ Business has WhatsApp contact")
            except Exception:
                pass

        # Extract rating
        rating_elem = safe_find_element(driver, By.XPATH, "//span[@class='MW4etd']", 5)
        if rating_elem:
            details["Rating"] = clean_text(rating_elem.text)
            log_message(f"✓ Found rating: {details['Rating']}")

        # Extract reviews count
        reviews_elem = safe_find_element(driver, By.XPATH, "//span[@class='UY7F9']", 5)
        if reviews_elem:
            reviews_text = clean_text(reviews_elem.text)
            details["Reviews"] = reviews_text
            try:
                # Extract numeric value from reviews text
                numeric_reviews = re.findall(r'[\d,]+', reviews_text)
                if numeric_reviews:
                    reviews_count = int(numeric_reviews[0].replace(',', ''))
                    details["Reviews_Count"] = reviews_count
                    if reviews_count >= 25:
                        details["Has_Sufficient_Reviews"] = True
                        log_message(f"✓ Has sufficient reviews: {reviews_count}")
            except Exception as e:
                log_message(f"Error parsing reviews count: {e}")

        # Extract plus code
        plus_code_elem = safe_find_element(driver, By.XPATH, "//button[@data-tooltip='Copy plus code']", 3)
        if plus_code_elem:
            details["Plus Code"] = clean_text(plus_code_elem.text)

        # Extract website
        website_elem = safe_find_element(driver, By.XPATH, "//a[contains(@aria-label, 'Visit') or contains(@href, 'http')]", 3)
        if website_elem:
            href = website_elem.get_attribute("href")
            if href and 'google.com' not in href:
                details["Website"] = clean_text(href)

        # Extract category
        category_elems = safe_find_elements(driver, By.XPATH, "//button[contains(@jsaction, 'pane.rating.category')]", 5)
        if category_elems:
            details["Category"] = clean_text(category_elems[0].text)

        # Extract hours with improved logic
        try:
            hours_buttons = safe_find_elements(driver, By.XPATH, "//button[contains(@aria-label, 'hour') or contains(@aria-label, 'Hour') or contains(@aria-label, 'Open')]", 5)
            if hours_buttons:
                driver.execute_script("arguments[0].click();", hours_buttons[0])
                time.sleep(3)

                hours_rows = safe_find_elements(driver, By.XPATH, "//table[contains(@class, 'WgFkxc')]//tr", 5)
                if hours_rows:
                    days_hours = []
                    for row in hours_rows:
                        row_text = clean_text(row.text)
                        if row_text and row_text.strip():
                            days_hours.append(row_text)
                    
                    if days_hours:
                        details["Hours"] = "; ".join(days_hours)
                        details["Has_Working_Hours"] = True
                        log_message("✓ Extracted business hours")
        except Exception as e:
            log_message(f"✗ Error extracting hours: {e}")

        # Check for multiple locations
        try:
            location_indicators = [
                "//a[contains(text(), 'location')]",
                "//a[contains(text(), 'branch')]",
                "//a[contains(text(), 'View all')]",
                "//span[contains(text(), 'chain')]",
                "//span[contains(text(), 'branches')]"
            ]
            
            for xpath in location_indicators:
                elements = safe_find_elements(driver, By.XPATH, xpath, 2)
                if elements:
                    details["Has_Multiple_Locations"] = True
                    log_message("✗ Business has multiple locations/branches")
                    break
        except Exception:
            pass

    except Exception as e:
        log_message(f"❌ Error extracting details: {e}")
        details["Error"] = str(e)

    return details

def scrape_Maps_location(task_id, keyword, country, city):
    """Scrape Google Maps for businesses in a specific location with improved error handling"""
    driver = None
    try:
        driver = init_driver()
        if not driver:
            log_message("❌ Failed to initialize driver")
            tasks[task_id]["running"] = False
            tasks[task_id]["error"] = "Failed to initialize web driver"
            return

        if not tasks.get(task_id, {}).get("running", False):
            log_message(f"Task {task_id} canceled before starting.")
            return

        search_query = f"{keyword} in {city}, {country}"
        maps_url = f"https://www.google.com/maps/search/{search_query.replace(' ', '+')}"
        
        log_message(f"🔍 Searching for: {search_query}")
        log_message(f"🌐 URL: {maps_url}")

        try:
            driver.get(maps_url)
            smart_sleep(10, 15, "for search results to load")
        except Exception as e:
            log_message(f"❌ Error loading search page: {e}")
            tasks[task_id]["running"] = False
            tasks[task_id]["error"] = f"Error loading search page: {e}"
            return

        extracted_urls = set()
        results = []
        total_processed = 0

        # Wait for results container with multiple attempts
        results_container = None
        for attempt in range(3):
            results_container = safe_find_element(driver, By.XPATH, "//div[@role='feed']", 20)
            if results_container:
                break
            log_message(f"Attempt {attempt + 1}/3 - Results container not found, retrying...")
            time.sleep(5)

        if not results_container:
            log_message(f"⚠️ Couldn't find results container for {city}, {country}")
            tasks[task_id]["running"] = False
            tasks[task_id]["error"] = "No results container found"
            return

        log_message("✓ Found results container, starting to process results...")

        max_iterations = 25
        consecutive_no_new_results = 0
        previous_results_count = 0

        for scroll_iteration in range(max_iterations):
            if not tasks.get(task_id, {}).get("running", False):
                log_message("🛑 Scraping stopped by user")
                break

            try:
                # Find all result items
                result_items = safe_find_elements(driver, By.XPATH, "//div[@role='feed']/div[.//h3 or .//a[contains(@href, '/maps/place/')]]", 10)
                
                if not result_items:
                    log_message("No results found with primary selector, trying alternative...")
                    result_items = safe_find_elements(driver, By.XPATH, "//div[@role='feed']//div[contains(@class, 'Nv2PK')]", 10)

                current_count = len(result_items)
                log_message(f"📊 Found {current_count} results (iteration {scroll_iteration+1}/{max_iterations})")

                # Check if we're getting new results
                if current_count == previous_results_count:
                    consecutive_no_new_results += 1
                    if consecutive_no_new_results >= 3:
                        log_message("🛑 No new results for 3 consecutive iterations, stopping")
                        break
                else:
                    consecutive_no_new_results = 0

                previous_results_count = current_count

                # Process new items only
                items_to_process = result_items[total_processed:]
                
                for item_idx, item in enumerate(items_to_process):
                    if not tasks.get(task_id, {}).get("running", False):
                        break

                    try:
                        # Extract name and URL
                        name = "N/A"
                        restaurant_url = None

                        # Try to find name
                        name_selectors = [
                            ".//div[contains(@class, 'fontHeadlineSmall')]",
                            ".//h3",
                            ".//span[contains(@class, 'qBF1Pd')]"
                        ]
                        
                        for selector in name_selectors:
                            try:
                                name_elem = item.find_element(By.XPATH, selector)
                                if name_elem:
                                    name = clean_text(name_elem.text)
                                    if name and name != "N/A":
                                        break
                            except:
                                continue

                        # Try to find URL
                        try:
                            url_elem = item.find_element(By.XPATH, ".//a[contains(@href, '/maps/place/')]")
                            restaurant_url = url_elem.get_attribute("href")
                        except:
                            continue

                        if not restaurant_url or restaurant_url in extracted_urls:
                            continue

                        extracted_urls.add(restaurant_url)
                        log_message(f"📍 Processing result {total_processed + 1}: {name}")

                        # Scroll to item and click
                        driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", url_elem)
                        time.sleep(2)

                        # Try clicking with multiple approaches
                        click_successful = False
                        for attempt in range(3):
                            try:
                                if attempt == 0:
                                    driver.execute_script("arguments[0].click();", url_elem)
                                elif attempt == 1:
                                    url_elem.click()
                                else:
                                    driver.get(restaurant_url)
                                
                                # Wait for the business details page to load
                                WebDriverWait(driver, 15).until(
                                    EC.any_of(
                                        EC.presence_of_element_located((By.XPATH, "//h1[contains(@class, 'DUwDvf')]")),
                                        EC.presence_of_element_located((By.XPATH, "//h1"))
                                    )
                                )
                                click_successful = True
                                break
                            except Exception as e:
                                log_message(f"Click attempt {attempt + 1} failed: {e}")
                                time.sleep(3)

                        if not click_successful:
                            log_message("❌ Failed to access business details page")
                            continue

                        # Wait for page to fully load
                        smart_sleep(5, 8, "for business details to load")

                        # Extract business details
                        details = extract_restaurant_details(driver, restaurant_url, task_id)

                        # Create business data entry
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
                        total_processed += 1
                        
                        # Update task progress
                        tasks[task_id]["progress"] = total_processed
                        tasks[task_id]["results"] = results
                        
                        log_message(f"✅ Successfully processed {total_processed} businesses")

                        # Navigate back to search results
                        try:
                            driver.back()
                            smart_sleep(4, 6, "after navigating back")
                            
                            # Wait for results container to reappear
                            results_container = safe_find_element(driver, By.XPATH, "//div[@role='feed']", 15)
                            if not results_container:
                                log_message("⚠️ Lost results container after going back")
                                break
                        except Exception as e:
                            log_message(f"❌ Error navigating back: {e}")
                            break

                    except Exception as e:
                        log_message(f"❌ Error processing item {total_processed + 1}: {e}")
                        continue

                # Scroll to load more results
                try:
                    driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight", results_container)
                    smart_sleep(6, 9, "after scrolling to load more results")
                except Exception as e:
                    log_message(f"❌ Error scrolling: {e}")
                    break

            except Exception as e:
                log_message(f"❌ Error in scroll iteration {scroll_iteration + 1}: {e}")
                break

        log_message(f"🎉 Scraping completed! Total businesses processed: {total_processed}")
        
    except Exception as e:
        log_message(f"❌ Critical error in scraping function: {e}")
        log_message(f"❌ Traceback: {traceback.format_exc()}")
        tasks[task_id]["error"] = str(e)
    finally:
        if driver:
            try:
                driver.quit()
                log_message("✓ Driver closed successfully")
            except:
                pass
        
        tasks[task_id]["running"] = False
        log_message(f"Task {task_id} completed with {len(tasks[task_id].get('results', []))} results")

# Include the same scrape_Maps function with similar improvements...
def scrape_Maps(task_id, location_data, keyword):
    """Scrape Google Maps for businesses across multiple locations with improved error handling"""
    driver = None
    try:
        driver = init_driver()
        if not driver:
            log_message("❌ Failed to initialize driver")
            tasks[task_id]["running"] = False
            tasks[task_id]["error"] = "Failed to initialize web driver"
            return

        results = []
        total_processed = 0

        for idx, (postal_code, city, country) in enumerate(location_data):
            if not tasks.get(task_id, {}).get("running", False):
                log_message(f"Task {task_id} canceled. Exiting scraping process.")
                break

            search_query = f"{keyword} in {postal_code}, {city}, {country}"
            maps_url = f"https://www.google.com/maps/search/{search_query.replace(' ', '+')}"
            
            log_message(f"🔍 Processing location {idx + 1}/{len(location_data)}: {postal_code}, {city}, {country}")

            try:
                driver.get(maps_url)
                smart_sleep(8, 12, "for search results to load")

                results_container = safe_find_element(driver, By.XPATH, "//div[@role='feed']", 15)
                if not results_container:
                    log_message(f"⚠️ Couldn't find results container for {postal_code}")
                    continue

                # Process results for this location (similar logic to scrape_Maps_location)
                # ... (implement similar processing logic)

            except Exception as e:
                log_message(f"❌ Error processing location {postal_code}: {e}")
                continue

    except Exception as e:
        log_message(f"❌ Critical error in scraping function: {e}")
        tasks[task_id]["error"] = str(e)
    finally:
        if driver:
            try:
                driver.quit()
            except:
                pass
        tasks[task_id]["running"] = False

# REST OF THE API ENDPOINTS REMAIN THE SAME...

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
JSON_FOLDER = os.path.join(BASE_DIR, "data", "countries")

@app.get("/countries")
def get_countries():
    try:
        countries = sorted([f[:-5] for f in os.listdir(JSON_FOLDER) if f.endswith(".json")])
        return {"countries": countries}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.get("/cities/{country}")
def get_cities(country: str):
    try:
        country_files = {f.lower(): f for f in os.listdir(JSON_FOLDER) if f.endswith(".json")}
        country_filename = country.lower() + ".json"
        
        if country_filename not in country_files:
            return JSONResponse(status_code=404, content={"error": f"Country '{country}' not found"})

        file_path = os.path.join(JSON_FOLDER, country_files[country_filename])
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        cities = [city["ASCII Name"] for city in data if int(city.get("Population", 0)) > 100000]
        
        if not cities:
            return JSONResponse(status_code=200, content={"message": "No cities with population greater than 100000"})

        return {"cities": cities}
    
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

    tasks[task_id] = {"running": True, "progress": 0, "results": [], "error": None}
    threading.Thread(target=scrape_Maps, args=(task_id, location_data, keyword)).start()

    return {"message": "Processing started", "task_id": task_id}

@app.post("/search-by-location/")
async def search_by_location(keyword: str = Form(...), country: str = Form(...), city: str = Form(...), email: str = Form(...)):
    task_id = str(time.time())
    tasks[task_id] = {"running": True, "progress": 0, "results": [], "error": None}
    
    threading.Thread(target=scrape_Maps_location, args=(task_id, keyword, country, city)).start()
    
    return {"message": "Processing started", "task_id": task_id}

@app.get("/progress/{task_id}")
async def get_progress(task_id: str):
    if task_id in tasks:
        task = tasks[task_id]
        return {
            "progress": task.get("progress", 0),
            "results": task.get("results", []),
            "running": task.get("running", False),
            "error": task.get("error", None)
        }
    return {"error": "Task not found"}

@app.post("/cancel/{task_id}")
def cancel_task(task_id: str):
    if task_id in tasks:
        tasks[task_id]["running"] = False
        time.sleep(1)
        return {"message": f"Task {task_id} has been canceled"}
    return JSONResponse(status_code=404, content={"error": "Task not found"})

@app.get("/download/{task_id}")
def download_results(task_id: str):
    if task_id not in tasks or not tasks[task_id]["results"]:
        return {"error": "No results found"}

    def iter_csv():
        yield "Postal Code,Name,Address,Phone,Website,URL,City,Country,Rating,Reviews,Reviews_Count,Plus Code,Category,Hours,Has_Multiple_Locations,Has_Contact_Info,Has_Sufficient_Reviews,Has_Working_Hours\n"
        
        for row in tasks[task_id]["results"]:
            postal_code = f'"{row.get("Postal Code", "")}"'
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
        yield "Name,Address,Phone,Website,URL,City,Country\n"
        
        for row in tasks[task_id]["results"]:
            # Properly escape fields that might contain commas
            name = f'"{row["Name"]}"'
            address = f'"{row["Address"]}"'
            phone = f'"{row["Phone"]}"'
            website = f'"{row["Website"]}"'
            url = f'"{row["URL"]}"'
            city = f'"{row["City"]}"'
            country = f'"{row["Country"]}"'
            
            yield f"{name},{address},{phone},{website},{url},{city},{country}\n"

    return StreamingResponse(iter_csv(), media_type="text/csv", 
                           headers={"Content-Disposition": f"attachment; filename=results_{task_id}.csv"})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
