from fastapi import FastAPI, File, UploadFile, Form
from fastapi.responses import StreamingResponse
import pandas as pd
import time
import threading
import re
from selenium_stealth import stealth
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

def smart_sleep(min_sec=10, max_sec=15, reason=""):
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
    # Add these Chrome options to the init_driver() function
    options.add_argument("--no-first-run")
    options.add_argument("--disable-default-apps")
    options.add_argument("--remote-debugging-port=9222")
    
    # Enhanced user agent rotation
    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
    ]
    options.add_argument(f"--user-agent={random.choice(user_agents)}")
    
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    options.add_argument("--disable-logging")
    options.add_argument("--log-level=3")
    
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

        # Enhanced anti-detection
        driver.execute_script("""
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
            Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']});
        """)
        
        # ADD STEALTH MODE HERE - AFTER DRIVER CREATION
        try:
            from selenium_stealth import stealth
            stealth(driver,
                    languages=["en-US", "en"],
                    vendor="Google Inc.",
                    platform="Win32",
                    webgl_vendor="Intel Inc.",
                    renderer="Intel Iris OpenGL Engine",
                    fix_hairline=True,
                    )
            log_message("✓ Stealth mode applied successfully")
        except ImportError:
            log_message("⚠️ selenium-stealth not installed, using basic anti-detection")
            # Fallback anti-detection
            driver.execute_script("""
                Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
                Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']});
            """)
        
        log_message("✓ Chrome driver created successfully with WebDriver Manager")
        return driver
    except Exception as e:
        log_message(f"ℹ️ WebDriver Manager approach failed: {e}")
        log_message("🔄 Trying direct ChromeDriver creation...")

        try:
            driver = webdriver.Chrome(options=options)

            # Enhanced anti-detection
            driver.execute_script("""
                Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
                Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']});
            """)
            
            # ADD STEALTH MODE HERE TOO - FOR FALLBACK DRIVER
            try:
                from selenium_stealth import stealth
                stealth(driver,
                        languages=["en-US", "en"],
                        vendor="Google Inc.",
                        platform="Win32",
                        webgl_vendor="Intel Inc.",
                        renderer="Intel Iris OpenGL Engine",
                        fix_hairline=True,
                        )
                log_message("✓ Stealth mode applied successfully")
            except ImportError:
                log_message("⚠️ selenium-stealth not installed, using basic anti-detection")
                driver.execute_script("""
                    Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                    Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
                    Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']});
                """)
            
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
        # Wait for page to be fully loaded
        WebDriverWait(driver, 20).until(
            EC.any_of(
                EC.presence_of_element_located((By.XPATH, "//h1")),
                EC.presence_of_element_located((By.CSS_SELECTOR, "[data-value='Title']")),
                EC.presence_of_element_located((By.XPATH, "//div[contains(@class, 'lMbq3e')]"))
            )
        )

        # Extract name with multiple selectors
        name_selectors = [
            "//h1[contains(@class, 'DUwDvf')]",
            "//h1[@class='x3AX1-LfntMc-header-title-title']",
            "//div[@data-value='Title']//span",
            "//h1",
            "//div[contains(@class, 'lMbq3e')]//span[1]"
        ]
        
        for selector in name_selectors:
            try:
                name_elem = driver.find_element(By.XPATH, selector)
                if name_elem and name_elem.text.strip():
                    details["Name"] = clean_text(name_elem.text)
                    log_message(f"✓ Found name: {details['Name']}")
                    break
            except:
                continue

        # Extract address with improved selectors
        address_selectors = [
            "//button[@data-item-id='address']//div[contains(@class, 'fontBodyMedium')]",
            "//div[@data-value='Address']//span",
            "//button[contains(@aria-label, 'Address')]//div",
            "//div[contains(@class, 'Io6YTe') and contains(text(), ',')]"
        ]
        
        for selector in address_selectors:
            try:
                address_elem = driver.find_element(By.XPATH, selector)
                if address_elem and address_elem.text.strip():
                    details["Address"] = clean_text(address_elem.text)
                    log_message(f"✓ Found address: {details['Address']}")
                    break
            except:
                continue

        # Extract phone with better selectors
        phone_selectors = [
            "//button[@data-item-id='phone:tel:']//div[contains(@class, 'fontBodyMedium')]",
            "//button[contains(@aria-label, 'Phone')]//div",
            "//a[starts-with(@href, 'tel:')]",
            "//div[contains(text(), '+') and contains(text(), ' ')]"
        ]
        
        for selector in phone_selectors:
            try:
                phone_elem = driver.find_element(By.XPATH, selector)
                if phone_elem and phone_elem.text.strip():
                    phone_text = clean_text(phone_elem.text)
                    if any(char.isdigit() for char in phone_text):
                        details["Phone"] = phone_text
                        details["Has_Contact_Info"] = True
                        log_message(f"✓ Found phone: {details['Phone']}")
                        break
            except:
                continue

        # Extract rating and reviews with fallbacks
        try:
            rating_elem = driver.find_element(By.XPATH, "//div[contains(@class, 'F7nice')]//span[@aria-hidden='true']")
            if rating_elem:
                details["Rating"] = clean_text(rating_elem.text)
        except:
            try:
                rating_elem = driver.find_element(By.XPATH, "//span[@class='MW4etd']")
                if rating_elem:
                    details["Rating"] = clean_text(rating_elem.text)
            except:
                pass

        try:
            reviews_elem = driver.find_element(By.XPATH, "//div[contains(@class, 'F7nice')]//span[contains(text(), '(') and contains(text(), ')')]")
            if reviews_elem:
                reviews_text = clean_text(reviews_elem.text)
                details["Reviews"] = reviews_text
                # Extract number from parentheses
                import re
                numbers = re.findall(r'\(([\d,]+)\)', reviews_text)
                if numbers:
                    count = int(numbers[0].replace(',', ''))
                    details["Reviews_Count"] = count
                    details["Has_Sufficient_Reviews"] = count >= 25
        except:
            pass

        # Extract website
        try:
            website_elem = driver.find_element(By.XPATH, "//a[@data-item-id='authority']//div[contains(@class, 'fontBodyMedium')]")
            if website_elem:
                details["Website"] = clean_text(website_elem.text)
        except:
            try:
                website_elem = driver.find_element(By.XPATH, "//a[contains(@href, 'http') and not(contains(@href, 'google.com'))]")
                if website_elem:
                    details["Website"] = website_elem.get_attribute("href")
            except:
                pass

    except Exception as e:
        log_message(f"❌ Error extracting details: {e}")
        # Don't return here, continue with whatever we got
    
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

        search_query = f"{keyword} in {city}, {country}"
        maps_url = f"https://www.google.com/maps/search/{search_query.replace(' ', '+')}"
        
        log_message(f"🔍 Searching for: {search_query}")

        # Load the search page
        driver.get(maps_url)
        smart_sleep(8, 12, "for initial page load")

        # Wait for results with multiple attempts
        results_loaded = False
        for attempt in range(5):  # Increased attempts
            try:
                # Try multiple selectors for results
                selectors_to_try = [
                    "//div[@role='feed']",
                    "//div[@aria-label='Results for']",
                    "//div[contains(@class, 'Nv2PK')]",
                    "//div[@data-result-index]"
                ]
                
                for selector in selectors_to_try:
                    try:
                        WebDriverWait(driver, 10).until(
                            EC.presence_of_element_located((By.XPATH, selector))
                        )
                        results_loaded = True
                        log_message(f"✓ Found results with selector: {selector}")
                        break
                    except:
                        continue
                
                if results_loaded:
                    break
                    
                log_message(f"Attempt {attempt + 1}/5 failed, retrying...")
                time.sleep(5)
                
            except Exception as e:
                log_message(f"Attempt {attempt + 1} error: {e}")

        if not results_loaded:
            log_message("❌ Could not find any results")
            tasks[task_id]["error"] = "No results found"
            tasks[task_id]["running"] = False
            return

        # Process results with improved selectors
        results = []
        processed_urls = set()
        
        # Scroll and collect results
        for scroll_attempt in range(10):  # Reduced from 25 to 10
            if not tasks.get(task_id, {}).get("running", False):
                break
                
            # Find all clickable result items
            result_items = []
            
            # Try multiple selectors to find result items
            item_selectors = [
                "//div[@role='feed']//a[contains(@href, '/maps/place/')]",
                "//div[contains(@class, 'Nv2PK')]//a[contains(@href, '/maps/place/')]",
                "//a[contains(@href, '/maps/place/')]"
            ]
            
            for selector in item_selectors:
                try:
                    items = driver.find_elements(By.XPATH, selector)
                    if items:
                        result_items = items
                        break
                except:
                    continue
            
            if not result_items:
                log_message("No result items found, trying to scroll more...")
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(3)
                continue
            
            log_message(f"Found {len(result_items)} potential results")
            
            # Process each result
            for item in result_items[:5]:  # Limit to 5 per scroll to avoid timeouts
                if not tasks.get(task_id, {}).get("running", False):
                    break
                    
                try:
                    url = item.get_attribute("href")
                    if not url or url in processed_urls:
                        continue
                    
                    processed_urls.add(url)
                    
                    # Click and extract details
                    driver.execute_script("arguments[0].scrollIntoView(true);", item)
                    time.sleep(2)
                    
                    item.click()
                    smart_sleep(5, 8, "for business page to load")
                    
                    # Extract details
                    details = extract_restaurant_details(driver, url, task_id)
                    
                    if details["Name"] != "N/A":
                        business_data = {
                            "Name": details["Name"],
                            "Address": details["Address"],
                            "Phone": details["Phone"],
                            "Website": details["Website"],
                            "URL": url,
                            "City": city,
                            "Country": country,
                            "Rating": details["Rating"],
                            "Reviews": details["Reviews"],
                            "Reviews_Count": details["Reviews_Count"],
                            "Plus Code": details["Plus Code"],
                            "Category": details["Category"],
                            "Hours": details["Hours"],
                            "Has_Multiple_Locations": details["Has_Multiple_Locations"],
                            "Has_Contact_Info": details["Has_Contact_Info"],
                            "Has_Sufficient_Reviews": details["Has_Sufficient_Reviews"],
                            "Has_Working_Hours": details["Has_Working_Hours"],
                        }
                        
                        results.append(business_data)
                        tasks[task_id]["results"] = results
                        tasks[task_id]["progress"] = len(results)
                        
                        log_message(f"✅ Processed: {details['Name']} (Total: {len(results)})")
                    
                    # Go back to results
                    driver.back()
                    smart_sleep(3, 5, "after going back")
                    
                except Exception as e:
                    log_message(f"❌ Error processing result: {e}")
                    continue
            
            # Scroll for more results
            try:
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(3)
            except:
                break
        
        log_message(f"🎉 Scraping completed! Found {len(results)} businesses")
        
    except Exception as e:
        log_message(f"❌ Critical error: {e}")
        log_message(f"❌ Traceback: {traceback.format_exc()}")
        tasks[task_id]["error"] = str(e)
    finally:
        if driver:
            try:
                driver.quit()
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

                # Wait for results with multiple attempts
                results_loaded = False
                for attempt in range(3):
                    try:
                        selectors_to_try = [
                            "//div[@role='feed']",
                            "//div[@aria-label='Results for']",
                            "//div[contains(@class, 'Nv2PK')]",
                            "//div[@data-result-index]"
                        ]
                        
                        for selector in selectors_to_try:
                            try:
                                WebDriverWait(driver, 10).until(
                                    EC.presence_of_element_located((By.XPATH, selector))
                                )
                                results_loaded = True
                                log_message(f"✓ Found results with selector: {selector}")
                                break
                            except:
                                continue
                        
                        if results_loaded:
                            break
                            
                        log_message(f"Attempt {attempt + 1}/3 failed, retrying...")
                        time.sleep(3)
                        
                    except Exception as e:
                        log_message(f"Attempt {attempt + 1} error: {e}")

                if not results_loaded:
                    log_message(f"❌ Could not find any results for {postal_code}")
                    continue

                # Process results for this location
                processed_urls = set()
                location_results = 0
                
                # Scroll and collect results (limit scrolling for CSV processing)
                for scroll_attempt in range(5):  # Reduced scrolling for CSV processing
                    if not tasks.get(task_id, {}).get("running", False):
                        break
                        
                    # Find all clickable result items
                    result_items = []
                    
                    item_selectors = [
                        "//div[@role='feed']//a[contains(@href, '/maps/place/')]",
                        "//div[contains(@class, 'Nv2PK')]//a[contains(@href, '/maps/place/')]",
                        "//a[contains(@href, '/maps/place/')]"
                    ]
                    
                    for selector in item_selectors:
                        try:
                            items = driver.find_elements(By.XPATH, selector)
                            if items:
                                result_items = items
                                break
                        except:
                            continue
                    
                    if not result_items:
                        log_message("No result items found, trying to scroll more...")
                        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                        time.sleep(3)
                        continue
                    
                    log_message(f"Found {len(result_items)} potential results for {postal_code}")
                    
                    # Process each result (limit to prevent timeout)
                    for item in result_items[:3]:  # Process max 3 per scroll for CSV
                        if not tasks.get(task_id, {}).get("running", False):
                            break
                            
                        try:
                            url = item.get_attribute("href")
                            if not url or url in processed_urls:
                                continue
                            
                            processed_urls.add(url)
                            
                            # Click and extract details
                            driver.execute_script("arguments[0].scrollIntoView(true);", item)
                            time.sleep(2)
                            
                            item.click()
                            smart_sleep(3, 5, "for business page to load")
                            
                            # Extract details using the same function as scrape_Maps_location
                            details = extract_restaurant_details(driver, url, task_id)
                            
                            if details["Name"] != "N/A":
                                business_data = {
                                    "Postal Code": postal_code,
                                    "Name": details["Name"],
                                    "Address": details["Address"],
                                    "Phone": details["Phone"],
                                    "Website": details["Website"],
                                    "URL": url,
                                    "City": city,
                                    "Country": country,
                                    "Rating": details["Rating"],
                                    "Reviews": details["Reviews"],
                                    "Reviews_Count": details["Reviews_Count"],
                                    "Plus Code": details["Plus Code"],
                                    "Category": details["Category"],
                                    "Hours": details["Hours"],
                                    "Has_Multiple_Locations": details["Has_Multiple_Locations"],
                                    "Has_Contact_Info": details["Has_Contact_Info"],
                                    "Has_Sufficient_Reviews": details["Has_Sufficient_Reviews"],
                                    "Has_Working_Hours": details["Has_Working_Hours"],
                                }
                                
                                results.append(business_data)
                                location_results += 1
                                total_processed += 1
                                
                                # Update task progress
                                tasks[task_id]["results"] = results
                                tasks[task_id]["progress"] = total_processed
                                
                                log_message(f"✅ Processed: {details['Name']} from {postal_code} (Total: {total_processed})")
                            
                            # Go back to results
                            driver.back()
                            smart_sleep(2, 3, "after going back")
                            
                        except Exception as e:
                            log_message(f"❌ Error processing result from {postal_code}: {e}")
                            try:
                                driver.back()
                                time.sleep(2)
                            except:
                                pass
                            continue
                    
                    # Scroll for more results
                    try:
                        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                        time.sleep(3)
                    except:
                        break
                    
                    # Break if we've found enough results for this location
                    if location_results >= 5:  # Limit per location to manage time
                        break
                
                log_message(f"📍 Completed {postal_code}: Found {location_results} businesses")

            except Exception as e:
                log_message(f"❌ Error processing location {postal_code}: {e}")
                log_message(f"❌ Traceback: {traceback.format_exc()}")
                continue

        log_message(f"🎉 CSV Scraping completed! Total businesses found: {len(results)}")
        
        # Final update
        tasks[task_id]["results"] = results
        tasks[task_id]["progress"] = len(results)

    except Exception as e:
        log_message(f"❌ Critical error in scraping function: {e}")
        log_message(f"❌ Traceback: {traceback.format_exc()}")
        tasks[task_id]["error"] = str(e)
    finally:
        if driver:
            try:
                driver.quit()
                log_message("✓ Driver closed successfully")
            except Exception as e:
                log_message(f"⚠️ Error closing driver: {e}")
        
        if task_id in tasks:
            tasks[task_id]["running"] = False
            log_message(f"Task {task_id} completed with {len(tasks[task_id].get('results', []))} results")

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

    tasks[task_id] = {"running": True, "progress": 0, "results": [], "error": None, "postal_code": postal_code, "city": city, "country": country}
    threading.Thread(target=scrape_Maps, args=(task_id, location_data, keyword)).start()

    return {"message": "Processing started", "task_id": task_id}

@app.post("/search-by-location/")
async def search_by_location(keyword: str = Form(...), country: str = Form(...), city: str = Form(...), email: str = Form(...)):
    task_id = str(time.time())
    
    # Validate inputs
    if not keyword.strip() or not country.strip() or not city.strip():
        return JSONResponse(status_code=400, content={"error": "All fields are required"})
    
    tasks[task_id] = {
        "running": True, 
        "progress": 0, 
        "results": [], 
        "error": None,
        "keyword": keyword,
        "city": city,
        "country": country,
        "started_at": time.time()
    }
    
    try:
        threading.Thread(target=scrape_Maps_location, args=(task_id, keyword, country, city)).start()
        log_message(f"🚀 Started scraping task {task_id} for {keyword} in {city}, {country}")
    except Exception as e:
        tasks[task_id]["error"] = f"Failed to start scraping thread: {str(e)}"
        tasks[task_id]["running"] = False
        return JSONResponse(status_code=500, content={"error": tasks[task_id]["error"]})
    
    return {"message": "Processing started", "task_id": task_id}

@app.get("/progress/{task_id}")
async def get_progress(task_id: str):
    if task_id in tasks:
        task = tasks[task_id]
        
        # Calculate runtime
        runtime = 0
        if "started_at" in task:
            runtime = time.time() - task["started_at"]
        
        return {
            "progress": task.get("progress", 0),
            "results": task.get("results", []),
            "running": task.get("running", False),
            "error": task.get("error", None),
            "runtime_seconds": int(runtime),
            "keyword": task.get("keyword", ""),
            "city": task.get("city", ""),
            "country": task.get("country", "")
        }
    return JSONResponse(status_code=404, content={"error": "Task not found"})

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
