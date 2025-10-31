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
import requests
import json
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import traceback
import logging
import datetime
import random
import requests
from .utils import calculate_boundary_points

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "https://map.uxlivinglab.online",
        "https://82.29.161.195"
    ],
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

def smart_sleep(min_sec=5, max_sec=8, reason=""):  # REDUCED default sleep times
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
    options.add_argument("--no-first-run")
    options.add_argument("--disable-default-apps")
    options.add_argument("--remote-debugging-port=9222")
    
    # ADDITIONAL PERFORMANCE OPTIMIZATIONS
    options.add_argument("--disable-images")  # Disable image loading for faster performance
    # Keep JavaScript enabled to ensure Maps UI loads fully
    options.add_argument("--disable-plugins")
    options.add_argument("--disable-java")
    options.add_argument("--disable-background-timer-throttling")
    options.add_argument("--disable-backgrounding-occluded-windows")
    options.add_argument("--disable-renderer-backgrounding")
    
    # Enhanced user agent rotation
    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ]
    options.add_argument(f"--user-agent={random.choice(user_agents)}")
    
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    options.add_argument("--disable-logging")
    options.add_argument("--log-level=3")
    
    # Enhanced memory and performance optimizations
    options.add_argument("--memory-pressure-off")
    options.add_argument("--max_old_space_size=8192")  # INCREASED memory
    options.add_argument("--aggressive-cache-discard")

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
            Object.defineProperty(navigator, 'permissions', {get: () => ({query: () => Promise.resolve({state: 'granted'})})});
        """)
        
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
        
        log_message("✓ Chrome driver created successfully with WebDriver Manager")
        return driver
    except Exception as e:
        log_message(f"ℹ️ WebDriver Manager approach failed: {e}")
        log_message("🔄 Trying direct ChromeDriver creation...")

        try:
            driver = webdriver.Chrome(options=options)
            # Same enhanced anti-detection code here
            driver.execute_script("""
                Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
                Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']});
            """)
            
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
        # Wait for page to be fully loaded with better conditions
        WebDriverWait(driver, 20).until(
            EC.any_of(
                EC.presence_of_element_located((By.XPATH, "//h1[contains(@class, 'DUwDvf')]")),
                EC.presence_of_element_located((By.XPATH, "//div[@data-value='Title']")),
                EC.presence_of_element_located((By.XPATH, "//h1[@data-attrid='title']"))
            )
        )

        # Extract name with improved validation
        name_selectors = [
            "//h1[contains(@class, 'DUwDvf') and not(contains(@class, 'review'))]",
            "//h1[@data-attrid='title']",
            "//div[@data-value='Title']//span[not(contains(text(), 'Results')) and not(contains(text(), 'reviews'))]",
            "//h1[not(contains(text(), 'Results')) and not(contains(text(), 'Map data'))]"
        ]
        
        for selector in name_selectors:
            try:
                name_elem = driver.find_element(By.XPATH, selector)
                if name_elem and name_elem.text.strip():
                    name_text = clean_text(name_elem.text)
                    # Validate that it's not a generic result
                    if (name_text and 
                        name_text.lower() not in ['results', 'map data', 'google', 'maps'] and
                        len(name_text) > 2 and
                        not name_text.isdigit()):
                        details["Name"] = name_text
                        log_message(f"✓ Found name: {details['Name']}")
                        break
            except:
                continue

        # If no valid name found, this is likely not a business page
        if details["Name"] == "N/A":
            log_message("❌ No valid business name found, skipping...")
            return details

        # Extract address with better validation
        address_selectors = [
            "//button[@data-item-id='address']//div[contains(@class, 'fontBodyMedium')]",
            "//div[@data-value='Address']//span[contains(text(), ',')]",
            "//button[contains(@aria-label, 'Address')]//div[contains(text(), ',')]",
            "//div[contains(@class, 'Io6YTe') and contains(text(), ',') and not(contains(text(), 'reviews'))]"
        ]
        
        for selector in address_selectors:
            try:
                address_elem = driver.find_element(By.XPATH, selector)
                if address_elem and address_elem.text.strip():
                    address_text = clean_text(address_elem.text)
                    # Validate address format
                    if address_text and ',' in address_text and len(address_text) > 10:
                        details["Address"] = address_text
                        log_message(f"✓ Found address: {details['Address']}")
                        break
            except:
                continue

        # Extract phone with strict validation
        phone_selectors = [
            "//button[@data-item-id='phone:tel:']//div[contains(@class, 'fontBodyMedium')]",
            "//button[contains(@aria-label, 'Phone')]//div[contains(text(), '+') or contains(text(), '(')]",
            "//a[starts-with(@href, 'tel:')]",
            "//span[contains(text(), '+') and (contains(text(), '-') or contains(text(), ' '))]"
        ]
        
        for selector in phone_selectors:
            try:
                phone_elem = driver.find_element(By.XPATH, selector)
                if phone_elem and phone_elem.text.strip():
                    phone_text = clean_text(phone_elem.text)
                    # Strict phone validation
                    if (phone_text and 
                        (phone_text.startswith('+') or phone_text.startswith('(')) and
                        any(char.isdigit() for char in phone_text) and
                        len(phone_text) >= 8 and
                        not phone_text.lower().startswith('0  26k')):  # Filter out the problematic pattern
                        details["Phone"] = phone_text
                        details["Has_Contact_Info"] = True
                        log_message(f"✓ Found phone: {details['Phone']}")
                        break
            except:
                continue

        # Extract rating with validation
        try:
            rating_elem = driver.find_element(By.XPATH, "//div[contains(@class, 'F7nice')]//span[@aria-hidden='true' and string-length(text()) <= 3]")
            if rating_elem and rating_elem.text.strip():
                rating_text = clean_text(rating_elem.text)
                try:
                    # Validate it's a number between 1-5
                    rating_float = float(rating_text)
                    if 1.0 <= rating_float <= 5.0:
                        details["Rating"] = rating_text
                except ValueError:
                    pass
        except:
            try:
                rating_elem = driver.find_element(By.XPATH, "//span[@class='MW4etd']")
                if rating_elem and rating_elem.text.strip():
                    rating_text = clean_text(rating_elem.text)
                    try:
                        rating_float = float(rating_text)
                        if 1.0 <= rating_float <= 5.0:
                            details["Rating"] = rating_text
                    except ValueError:
                        pass
            except:
                pass

        # Extract reviews count with validation
        try:
            reviews_elem = driver.find_element(By.XPATH, "//div[contains(@class, 'F7nice')]//span[contains(text(), '(') and contains(text, ')') and contains(text(), 'review')]")
            if not reviews_elem:
                reviews_elem = driver.find_element(By.XPATH, "//span[contains(text(), '(') and contains(text(), ')') and (contains(text(), 'review') or text()[matches(., '\\([0-9,]+\\)')])]")
            
            if reviews_elem and reviews_elem.text.strip():
                reviews_text = clean_text(reviews_elem.text)
                details["Reviews"] = reviews_text
                
                # Extract number from parentheses with validation
                import re
                numbers = re.findall(r'\(([0-9,]+)\)', reviews_text)
                if numbers:
                    try:
                        count = int(numbers[0].replace(',', ''))
                        if 0 <= count <= 1000000:  # Reasonable range
                            details["Reviews_Count"] = count
                            details["Has_Sufficient_Reviews"] = count >= 25
                    except ValueError:
                        pass
        except:
            pass

        # Extract website with validation
        try:
            website_elem = driver.find_element(By.XPATH, "//a[@data-item-id='authority']//div[contains(@class, 'fontBodyMedium')]")
            if website_elem and website_elem.text.strip():
                website_text = clean_text(website_elem.text)
                if website_text and not website_text.startswith('google.'):
                    details["Website"] = website_text
        except:
            try:
                website_link = driver.find_element(By.XPATH, "//a[contains(@href, 'http') and not(contains(@href, 'google.com')) and not(contains(@href, 'maps'))]")
                if website_link:
                    href = website_link.get_attribute("href")
                    if href and not href.startswith('https://www.google.'):
                        details["Website"] = href
            except:
                pass

        # Extract category/business type
        try:
            category_elem = driver.find_element(By.XPATH, "//button[contains(@class, 'DkEaL')]//span")
            if category_elem and category_elem.text.strip():
                category_text = clean_text(category_elem.text)
                if category_text and len(category_text) < 50:
                    details["Category"] = category_text
        except:
            pass

    except Exception as e:
        log_message(f"❌ Error extracting details: {e}")
    
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
        for attempt in range(5):
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
        
        # INCREASED SCROLLING - Scroll and collect results
        for scroll_attempt in range(50):  # INCREASED from 10 to 50
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
            
            # INCREASED PROCESSING - Process each result
            for item in result_items[:15]:  # INCREASED from 5 to 15 per scroll
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
            
            # Enhanced scrolling strategy
            try:
                # Multiple scroll techniques
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(2)
                
                # Try scrolling the results panel specifically
                feed_element = driver.find_element(By.XPATH, "//div[@role='feed']")
                driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight", feed_element)
                time.sleep(2)
                
                # Check if we've reached the end
                current_height = driver.execute_script("return document.body.scrollHeight")
                if scroll_attempt > 0:
                    if hasattr(scrape_Maps_location, 'last_height') and current_height == scrape_Maps_location.last_height:
                        no_new_content_count = getattr(scrape_Maps_location, 'no_new_content_count', 0) + 1
                        scrape_Maps_location.no_new_content_count = no_new_content_count
                        if no_new_content_count >= 5:  # Stop if no new content for 5 scrolls
                            log_message("No new content found, stopping scroll")
                            break
                    else:
                        scrape_Maps_location.no_new_content_count = 0
                scrape_Maps_location.last_height = current_height
                
            except Exception as e:
                log_message(f"Error during scrolling: {e}")
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
        global_processed_urls = set()

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
                            "//div[@role='feed']//a[contains(@href, '/maps/place/')]",
                            "//div[@aria-label='Results for']//a[contains(@href, '/maps/place/')]",
                            "//div[contains(@class, 'Nv2PK')]//a[contains(@href, '/maps/place/')]"
                        ]
                        
                        for selector in selectors_to_try:
                            try:
                                elements = driver.find_elements(By.XPATH, selector)
                                if len(elements) > 0:
                                    results_loaded = True
                                    log_message(f"✓ Found {len(elements)} results with selector: {selector}")
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
                location_results = 0
                
                # INCREASED SCROLLING for CSV processing
                for scroll_attempt in range(15):  # INCREASED from 3 to 15
                    if not tasks.get(task_id, {}).get("running", False):
                        break
                    
                    # Find clickable result items
                    result_items = driver.find_elements(By.XPATH, "//div[@role='feed']//a[contains(@href, '/maps/place/')]")
                    
                    if not result_items:
                        log_message("No result items found, scrolling...")
                        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                        time.sleep(3)
                        continue
                    
                    log_message(f"Found {len(result_items)} potential results for {postal_code}")
                    
                    # INCREASED PROCESSING - Process each result
                    items_to_process = result_items[:10]  # INCREASED from 5 to 10 per scroll
                    
                    for item_index, item in enumerate(items_to_process):
                        if not tasks.get(task_id, {}).get("running", False):
                            break
                            
                        try:
                            url = item.get_attribute("href")
                            if not url or url in global_processed_urls:
                                log_message(f"Skipping duplicate or invalid URL: {url}")
                                continue
                            
                            global_processed_urls.add(url)
                            
                            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", item)
                            time.sleep(1)
                            
                            driver.execute_script("arguments[0].click();", item)
                            smart_sleep(5, 8, "for business page to load")
                            
                            details = extract_restaurant_details(driver, url, task_id)
                            
                            if (details["Name"] != "N/A" and 
                                details["Name"].lower() not in ['results', 'map data', 'google'] and
                                len(details["Name"]) > 2):
                                
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
                                
                                tasks[task_id]["results"] = results
                                tasks[task_id]["progress"] = total_processed
                                
                                log_message(f"✅ Processed: {details['Name']} from {postal_code} (Total: {total_processed})")
                            else:
                                log_message(f"❌ Invalid business data, skipping: {details['Name']}")
                            
                            driver.back()
                            smart_sleep(2, 3, "after going back")
                            
                            WebDriverWait(driver, 10).until(
                                EC.presence_of_element_located((By.XPATH, "//div[@role='feed']//a[contains(@href, '/maps/place/')]"))
                            )
                            
                        except Exception as e:
                            log_message(f"❌ Error processing result from {postal_code}: {e}")
                            try:
                                driver.back()
                                time.sleep(2)
                            except:
                                pass
                            continue
                    
                    # REMOVED LIMIT - Allow unlimited results per location
                    # Break if we've found enough results for this location
                    # if location_results >= 3:  # REMOVED THIS LIMIT
                    #     break
                    
                    # Enhanced scrolling
                    try:
                        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                        time.sleep(2)
                        
                        # Try scrolling the results panel
                        feed_element = driver.find_element(By.XPATH, "//div[@role='feed']")
                        driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight", feed_element)
                        time.sleep(2)
                    except:
                        break
                
                log_message(f"📍 Completed {postal_code}: Found {location_results} businesses")

            except Exception as e:
                log_message(f"❌ Error processing location {postal_code}: {e}")
                continue

        log_message(f"🎉 CSV Scraping completed! Total businesses found: {len(results)}")
        
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

# CRUD/Datacube configuration
CRUD_BASE_URL = os.getenv("CRUD_BASE_URL", "")            # e.g. https://datacube.uxlivinglab.online/
CRUD_COORDS_PATH = os.getenv("CRUD_COORDS_PATH", "/api/crud")
CRUD_RESULTS_PATH = os.getenv("CRUD_RESULTS_PATH", "/api/crud")
CRUD_API_KEY = os.getenv("CRUD_API_KEY", "")
DATABASE_ID = os.getenv("DATABASE_ID", "")
CRUD_COLLECTION_NAME = os.getenv("CRUD_COLLECTION_NAME", "google_review_data")

def _post_to_crud(path, document):
    """Post a single document to the CRUD API using Api-Key auth."""
    if not CRUD_BASE_URL or not DATABASE_ID:
        log_message("CRUD config missing; skipping save")
        return False
    url = f"{CRUD_BASE_URL.rstrip('/')}{path}"
    headers = {"Content-Type": "application/json"}
    if CRUD_API_KEY:
        headers["Authorization"] = f"Api-Key {CRUD_API_KEY}"
    payload = {
        "database_id": DATABASE_ID,
        "collection_name": CRUD_COLLECTION_NAME,
        "data": [document]
    }
    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=30)
        if 200 <= resp.status_code < 300:
            return True
        log_message(f"CRUD POST failed {resp.status_code}: {resp.text}")
        return False
    except Exception as e:
        log_message(f"CRUD POST exception: {e}")
        return False

INSCRIBER_URL = os.getenv("INSCRIBER_URL", "http://inscriber:8002/api/geo-query-cube/")
DATABASE_ID = os.getenv("DATABASE_ID", "")

def get_city_coordinates(country: str, city: str):
    try:
        country_files = {f.lower(): f for f in os.listdir(JSON_FOLDER) if f.endswith(".json")}
        country_filename = country.lower() + ".json"
        if country_filename not in country_files:
            return None
        file_path = os.path.join(JSON_FOLDER, country_files[country_filename])
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        for entry in data:
            if entry.get("ASCII Name", "").lower() == city.lower():
                try:
                    return float(entry.get("latitude")), float(entry.get("longitude"))
                except Exception:
                    return None
        return None
    except Exception:
        return None

def fetch_inscriber_tiles(bounds):
    try:
        payload = {
            "top_left": list(bounds[0]),
            "top_right": list(bounds[1]),
            "bottom_left": list(bounds[2]),
            "bottom_right": list(bounds[3])
        }
        resp = requests.post(INSCRIBER_URL, json=payload, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        if isinstance(data, list):
            return [(float(p[0]), float(p[1])) for p in data]
        if isinstance(data, dict) and "raw_coordinates" in data:
            flat = []
            for block in data["raw_coordinates"]:
                if isinstance(block, list):
                    for item in block:
                        lat = item.get("latitude") if isinstance(item, dict) else (item[0] if isinstance(item, (list, tuple)) and len(item) >= 2 else None)
                        lon = item.get("longitude") if isinstance(item, dict) else (item[1] if isinstance(item, (list, tuple)) and len(item) >= 2 else None)
                        if lat is not None and lon is not None:
                            flat.append((float(lat), float(lon)))
            return flat
        return []
    except Exception as e:
        log_message(f"⚠️ Inscriber fetch failed: {e}")
        return []

def build_target_coordinates(centers, relative_tiles):
    if not relative_tiles:
        return centers
    targets = []
    for c_lat, c_lon in centers:
        for d_lat, d_lon in relative_tiles:
            targets.append((c_lat + d_lat, c_lon + d_lon))
    return targets

def scrape_by_coordinates(task_id, keyword, target_coords):
    driver = None
    try:
        driver = init_driver()
        if not driver:
            log_message("❌ Failed to initialize driver")
            tasks[task_id]["running"] = False
            tasks[task_id]["error"] = "Failed to initialize web driver"
            return

        results = []
        processed_urls = set()

        for idx, (lat, lon) in enumerate(target_coords):
            if not tasks.get(task_id, {}).get("running", False):
                break
            try:
                maps_url = f"https://www.google.com/maps/search/{requests.utils.quote(keyword)}/@{lat},{lon},14z"
                log_message(f"🔍 Searching around {lat:.6f},{lon:.6f} ({idx+1}/{len(target_coords)})")
                driver.get(maps_url)
                smart_sleep(6, 10, "for results to load")

                loaded = False
                for _ in range(3):
                    try:
                        elements = driver.find_elements(By.XPATH, "//div[@role='feed']//a[contains(@href, '/maps/place/')]")
                        if len(elements) > 0:
                            loaded = True
                            break
                        time.sleep(2)
                    except Exception:
                        time.sleep(2)
                if not loaded:
                    continue

                # Aggressively scroll the results feed to load more items
                try:
                    feed = driver.find_element(By.XPATH, "//div[@role='feed']")
                    for _ in range(6):  # increase as needed
                        driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight;", feed)
                        time.sleep(1.2)
                except Exception:
                    pass

                items = driver.find_elements(By.XPATH, "//div[@role='feed']//a[contains(@href, '/maps/place/')]")
                for item in items[:30]:  # process more items per coordinate
                    if not tasks.get(task_id, {}).get("running", False):
                        break
                    try:
                        url = item.get_attribute("href")
                        if not url or url in processed_urls:
                            continue
                        processed_urls.add(url)
                        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", item)
                        time.sleep(1)
                        driver.execute_script("arguments[0].click();", item)
                        smart_sleep(4, 7, "for business page to load")
                        details = extract_restaurant_details(driver, url, task_id)
                        if details["Name"] != "N/A":
                            business_data = {
                                "Name": details["Name"],
                                "Address": details["Address"],
                                "Phone": details["Phone"],
                                "Website": details["Website"],
                                "URL": url,
                                "City": "",
                                "Country": "",
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
                                "Latitude": f"{lat}",
                                "Longitude": f"{lon}",
                            }
                            results.append(business_data)
                            tasks[task_id]["results"] = results
                            tasks[task_id]["progress"] = len(results)
                        driver.back()
                        smart_sleep(2, 3, "after going back")
                    except Exception:
                        try:
                            driver.back()
                            time.sleep(1)
                        except Exception:
                            pass
                        continue
            except Exception as e:
                log_message(f"❌ Error at coordinate {lat},{lon}: {e}")
                continue

        log_message(f"🎉 Coordinate-based scraping completed! Total businesses found: {len(results)}")

    except Exception as e:
        log_message(f"❌ Critical error in coordinate scraping: {e}")
        tasks[task_id]["error"] = str(e)
    finally:
        if driver:
            try:
                driver.quit()
                log_message("✓ Driver closed successfully")
            except Exception:
                pass
        if task_id in tasks:
            tasks[task_id]["running"] = False
            log_message(f"Task {task_id} completed with {len(tasks[task_id].get('results', []))} results")

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
async def upload_csv(file: UploadFile, keyword: str = Form(...), email: str = Form(...), radius_km: float = Form(5.0)):
    task_id = str(time.time())
    df = pd.read_csv(file.file)
    centers = []
    lat_col = next((c for c in df.columns if str(c).strip().lower()=="latitude"), None)
    lon_col = next((c for c in df.columns if str(c).strip().lower()=="longitude"), None)
    if not lat_col or not lon_col:
        return JSONResponse(status_code=400, content={"error": "CSV must contain 'latitude' and 'longitude' columns"})
    for _, row in df.iterrows():
        if pd.isna(row[lat_col]) or pd.isna(row[lon_col]):
            continue
        try:
            centers.append((float(row[lat_col]), float(row[lon_col])))
        except Exception:
            continue

    bounds = calculate_boundary_points(float(radius_km))
    tiles = fetch_inscriber_tiles(bounds)
    target_coords = build_target_coordinates(centers, tiles)

    tasks[task_id] = {"running": True, "progress": 0, "results": [], "error": None, "centers": centers, "bounds": bounds, "tiles": tiles, "target_coords": target_coords, "keyword": keyword, "email": email, "radius_km": radius_km, "started_at": time.time()}
    threading.Thread(target=scrape_by_coordinates, args=(task_id, keyword, target_coords)).start()

    return {"message": "Processing started", "task_id": task_id}

@app.post("/search-by-location/")
async def search_by_location(keyword: str = Form(...), country: str = Form(...), city: str = Form(...), email: str = Form(...), radius_km: float = Form(5.0)):
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
    
    center = get_city_coordinates(country, city)
    if not center:
        tasks[task_id]["error"] = "Could not determine coordinates for selected city"
        tasks[task_id]["running"] = False
        return JSONResponse(status_code=400, content={"error": tasks[task_id]["error"]})

    bounds = calculate_boundary_points(float(radius_km))
    tiles = fetch_inscriber_tiles(bounds)
    target_coords = build_target_coordinates([center], tiles)

    tasks[task_id]["center"] = center
    tasks[task_id]["bounds"] = bounds
    tasks[task_id]["tiles"] = tiles
    tasks[task_id]["target_coords"] = target_coords
    tasks[task_id]["email"] = email
    tasks[task_id]["radius_km"] = radius_km

    try:
        threading.Thread(target=scrape_by_coordinates, args=(task_id, keyword, target_coords)).start()
        log_message(f"🚀 Started coordinate scraping task {task_id} for {keyword} around {center}")
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
