from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.responses import StreamingResponse
import pandas as pd
import time
import threading
import re
import os
import json
import traceback
import logging
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import contextmanager
from typing import List, Dict, Any, Optional

# Configure more detailed logging
logging.basicConfig(
    level=logging.DEBUG,  # Change to DEBUG for more detailed logs
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),  # Log to console
        logging.FileHandler("scraper.log")  # Log to file for persistence
    ]
)
logger = logging.getLogger(__name__)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173",
                   "https://map.uxlivinglab.online"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

tasks = {}


def clean_text(text):
    """Removes special characters and excessive whitespace from text."""
    if not text:
        return ""
    return re.sub(r'[^\w\s,.-]', '', text).strip()


@contextmanager
def init_driver():
    """Initializes and returns a Selenium WebDriver instance within a context manager."""
    driver = None
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.service import Service
        from selenium.webdriver.chrome.options import Options
        
        logger.debug("Initializing Chrome WebDriver...")
        
        options = Options()
        options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--window-size=1920,1080")
        
        # User agent to avoid detection
        options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36")

        # Docker-specific ChromeDriver configuration
        chrome_binary = os.getenv("GOOGLE_CHROME_BIN", "/usr/bin/google-chrome")
        chromedriver_path = os.getenv("CHROMEDRIVER_PATH", "/usr/local/bin/chromedriver")
        
        logger.info(f"Using Chrome binary at: {chrome_binary}")
        logger.info(f"Using ChromeDriver at: {chromedriver_path}")
        
        # Check if the Chrome binary and ChromeDriver actually exist
        if not os.path.exists(chrome_binary):
            logger.error(f"Chrome binary not found at: {chrome_binary}")
        if not os.path.exists(chromedriver_path):
            logger.error(f"ChromeDriver not found at: {chromedriver_path}")
        
        options.binary_location = chrome_binary
        service = Service(chromedriver_path)
        
        driver = webdriver.Chrome(service=service, options=options)
        logger.debug("WebDriver initialized successfully")
        yield driver
    except Exception as e:
        logger.error(f"Failed to initialize WebDriver: {str(e)}")
        logger.error(traceback.format_exc())
        raise
    finally:
        if driver:
            try:
                driver.quit()
                logger.debug("WebDriver closed successfully")
            except Exception as e:
                logger.error(f"Error closing WebDriver: {str(e)}")


def scrape_google_maps_location(task_id, keyword, country, city):
    """Thread function to scrape Google Maps based on location."""
    try:
        logger.info(f"Starting scrape_google_maps_location task: {task_id}")
        logger.info(f"Parameters - Keyword: {keyword}, Country: {country}, City: {city}")
        
        # Update task status
        if task_id not in tasks:
            logger.error(f"Task {task_id} not found in tasks dictionary")
            return
            
        tasks[task_id]["running"] = True
        tasks[task_id]["progress"] = 0
        tasks[task_id]["results"] = []
        
        with init_driver() as driver:
            logger.info("Driver initialized successfully")
            
            if not tasks.get(task_id, {}).get("running", False):
                logger.info(f"Task {task_id} canceled. Exiting scraping process.")
                return

            # Safely encode the search query
            import urllib.parse
            search_query = f"{keyword} in {city}, {country}"
            encoded_query = urllib.parse.quote_plus(search_query)
            google_maps_url = f"https://www.google.com/maps/search/{encoded_query}"

            try:
                from selenium.webdriver.common.by import By
                from selenium.webdriver.support.ui import WebDriverWait
                from selenium.webdriver.support import expected_conditions as EC
                
                logger.info(f"Navigating to: {google_maps_url}")
                driver.get(google_maps_url)
                
                # Take a screenshot for debugging
                screenshot_path = f"debug_screenshot_{task_id}.png"
                driver.save_screenshot(screenshot_path)
                logger.info(f"Saved initial page screenshot to {screenshot_path}")
                
                # Wait for page to load
                logger.debug("Waiting for page to load...")
                time.sleep(5)
                
                # Check if we hit a CAPTCHA or other blocking page
                page_source = driver.page_source
                if "Our systems have detected unusual traffic" in page_source:
                    logger.error("Google CAPTCHA detected! Scraping cannot continue.")
                    tasks[task_id]["error"] = "CAPTCHA detected. Please try again later."
                    tasks[task_id]["running"] = False
                    return
                
                # Try different selectors to find place listings
                logger.debug("Looking for business listings...")
                elements = []
                
                # Multiple selector strategies
                selectors = [
                    'a[href*="/maps/place/"]',
                    'div[role="article"]',
                    'div[jsaction*="placeCard.place"]',
                    'div.section-result',
                    'div[data-result-index]'
                ]
                
                for selector in selectors:
                    elements = driver.find_elements(By.CSS_SELECTOR, selector)
                    if elements:
                        logger.info(f"Found {len(elements)} elements with selector: {selector}")
                        break
                
                if not elements:
                    logger.error("No business listings found on the page")
                    driver.save_screenshot(f"no_elements_{task_id}.png")
                    logger.debug(f"Page source: {driver.page_source[:1000]}...")  # First 1000 chars
                    tasks[task_id]["error"] = "No business listings found"
                    tasks[task_id]["running"] = False
                    return
                
                extracted_urls = set()
                results = []
                total_count = 0

                for element in elements[:20]:  # Limit to first 20 results for testing
                    if not tasks.get(task_id, {}).get("running", False):
                        logger.info(f"Task {task_id} canceled. Exiting scraping process.")
                        return
                    
                    # Try to get URL from element
                    url = None
                    try:
                        # Try different strategies to get the URL
                        if element.tag_name == 'a':
                            url = element.get_attribute("href")
                        else:
                            # Try to find a link inside this element
                            link_elem = element.find_element(By.CSS_SELECTOR, 'a[href*="/maps/place/"]')
                            url = link_elem.get_attribute("href")
                    except Exception as e:
                        logger.warning(f"Could not get URL from element: {str(e)}")
                        continue
                    
                    if not url or url in extracted_urls:
                        continue
                        
                    extracted_urls.add(url)
                    logger.info(f"Processing URL: {url}")

                    try:
                        driver.get(url)
                        time.sleep(3)
                        
                        # Take screenshot of business page
                        driver.save_screenshot(f"business_{total_count}_{task_id}.png")
                        
                        # Get business name
                        name = "Not Available"
                        try:
                            name_candidates = [
                                driver.find_element(By.CSS_SELECTOR, "h1").text,
                                driver.find_element(By.CSS_SELECTOR, "div[role='heading'][aria-level='1']").text,
                                driver.find_element(By.CSS_SELECTOR, ".section-hero-header-title").text
                            ]
                            for candidate in name_candidates:
                                if candidate:
                                    name = clean_text(candidate)
                                    break
                        except Exception as e:
                            logger.warning(f"Name not found: {str(e)}")
                        
                        # Get business address
                        address = "Not Available"
                        try:
                            address_candidates = [
                                driver.find_element(By.CSS_SELECTOR, '[data-item-id="address"]').text,
                                driver.find_element(By.CSS_SELECTOR, 'button[data-item-id*="address"]').text,
                                driver.find_element(By.CSS_SELECTOR, 'button[aria-label*="Address"]').text
                            ]
                            for candidate in address_candidates:
                                if candidate:
                                    address = clean_text(candidate)
                                    break
                        except Exception as e:
                            logger.warning(f"Address not found: {str(e)}")
                        
                        # Get business phone
                        phone = "Not Available"
                        try:
                            phone_candidates = [
                                driver.find_element(By.CSS_SELECTOR, '[data-tooltip="Copy phone number"]').text,
                                driver.find_element(By.CSS_SELECTOR, 'button[data-item-id*="phone"]').text,
                                driver.find_element(By.CSS_SELECTOR, 'button[aria-label*="Phone"]').text
                            ]
                            for candidate in phone_candidates:
                                if candidate:
                                    phone = clean_text(candidate)
                                    break
                        except Exception as e:
                            logger.warning(f"Phone not found: {str(e)}")

                        # Get business website
                        website = "Not Available"
                        try:
                            website_candidates = [
                                driver.find_element(By.CSS_SELECTOR, 'a[href^="http"][data-item-id="authority"]').get_attribute("href"),
                                driver.find_element(By.CSS_SELECTOR, 'a[data-item-id*="website"]').get_attribute("href"),
                                driver.find_element(By.CSS_SELECTOR, 'a[aria-label*="website"]').get_attribute("href")
                            ]
                            for candidate in website_candidates:
                                if candidate:
                                    website = clean_text(candidate)
                                    break
                        except Exception as e:
                            logger.warning(f"Website not found: {str(e)}")

                        business_data = {
                            "Name": name,
                            "Address": address,
                            "Phone": phone,
                            "Website": website,
                            "URL": url,
                            "City": city,
                            "Country": country
                        }
                        
                        logger.info(f"Business data extracted: {business_data}")
                        results.append(business_data)

                        total_count += 1
                        tasks[task_id]["progress"] = total_count
                        tasks[task_id]["results"] = results

                    except Exception as e:
                        logger.error(f"Error processing business {url}: {str(e)}")
                        logger.error(traceback.format_exc())
                        continue

            except Exception as e:
                logger.error(f"Error accessing {google_maps_url}: {str(e)}")
                logger.error(traceback.format_exc())
                tasks[task_id]["error"] = f"Error accessing Google Maps: {str(e)}"

    except Exception as e:
        logger.error(f"Error in scrape_google_maps_location for task {task_id}: {str(e)}")
        logger.error(traceback.format_exc())
        tasks[task_id]["error"] = f"Scraping error: {str(e)}"
    finally:
        tasks[task_id]["running"] = False
        logger.info(f"Task {task_id} completed with {len(tasks[task_id].get('results', []))} results.")


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
JSON_FOLDER = os.path.join(BASE_DIR, "data", "countries")


@app.get("/status")
def get_status():
    return {"status": "running"}


@app.get("/countries")
def get_countries():
    try:
        if not os.path.exists(JSON_FOLDER):
            logger.error(f"JSON_FOLDER does not exist: {JSON_FOLDER}")
            return JSONResponse(status_code=500, content={"error": f"JSON_FOLDER not found: {JSON_FOLDER}"})
            
        countries = sorted([f[:-5] for f in os.listdir(JSON_FOLDER) if f.endswith(".json")])
        return {"countries": countries}

    except Exception as e:
        logger.error(f"Error in get_countries: {str(e)}")
        logger.error(traceback.format_exc())
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.get("/cities/{country}")
def get_cities(country: str):
    try:
        if not os.path.exists(JSON_FOLDER):
            logger.error(f"JSON_FOLDER does not exist: {JSON_FOLDER}")
            return JSONResponse(status_code=500, content={"error": f"JSON_FOLDER not found: {JSON_FOLDER}"})

        country_files = {f.lower(): f for f in os.listdir(JSON_FOLDER) if f.endswith(".json")}

        country_filename = country.lower() + ".json"
        if country_filename not in country_files:
            return JSONResponse(status_code=404, content={"error": f"Country '{country}' not found"})

        file_path = os.path.join(JSON_FOLDER, country_files[country_filename])

        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        cities = [
            city["ASCII Name"]
            for city in data
            if int(city.get("Population", "0").replace(",", "")) > 100000
        ]

        if not cities:
            return JSONResponse(status_code=200, content={"message": "No cities with population greater than 100000"})

        return {"cities": cities}

    except ValueError as e:
        logger.error(f"Invalid population data: {str(e)}")
        return JSONResponse(status_code=500, content={"error": f"Invalid population data: {str(e)}"})

    except json.JSONDecodeError:
        logger.error(f"Invalid JSON format in file: {file_path}")
        return JSONResponse(status_code=500, content={"error": "Invalid JSON format in file"})

    except Exception as e:
        logger.error(f"Error in get_cities: {str(e)}")
        logger.error(traceback.format_exc())
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.post("/search-by-location/")
async def search_by_location(keyword: str = Form(...), country: str = Form(...), city: str = Form(...), email: str = Form(...)):
    try:
        task_id = str(time.time())
        
        # Add some logging
        logger.info(f"Starting location search task {task_id}")
        logger.info(f"Keyword: {keyword}, Country: {country}, City: {city}, Email: {email}")

        # Validate inputs
        if not keyword or not country or not city:
            raise HTTPException(status_code=400, detail="Keyword, country, and city are required")

        tasks[task_id] = {
            "running": True, 
            "progress": 0, 
            "results": [],
            "error": None,
            "keyword": keyword,
            "country": country,
            "city": city,
            "email": email,
            "start_time": time.time()
        }

        # Start scraping in a separate thread
        thread = threading.Thread(target=scrape_google_maps_location, args=(task_id, keyword, country, city), daemon=True)
        thread.start()
        logger.info(f"Thread started for task {task_id}")

        return {"message": "Processing started", "task_id": task_id}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unhandled error in search_by_location: {str(e)}")
        logger.error(traceback.format_exc())
        return JSONResponse(status_code=500, content={"error": f"An unexpected error occurred: {str(e)}"})


@app.get("/progress/{task_id}")
async def get_progress(task_id: str):
    try:
        if task_id in tasks:
            task = tasks[task_id]
            response = {
                "progress": task.get("progress", 0),
                "results": task.get("results", []),
                "running": task.get("running", False),
                "error": task.get("error", None),
                "elapsed_time": time.time() - task.get("start_time", time.time())
            }
            
            # Log detailed response information
            logger.debug(f"Progress response for task {task_id}: {json.dumps(response, default=str)}")
            
            return response
        
        logger.warning(f"Task {task_id} not found")
        return JSONResponse(status_code=404, content={"error": "Task not found"})
    except Exception as e:
        logger.error(f"Error fetching progress for task {task_id}: {str(e)}")
        logger.error(traceback.format_exc())
        return JSONResponse(status_code=500, content={"error": f"An error occurred: {str(e)}"})


@app.post("/cancel/{task_id}")
def cancel_task(task_id: str):
    try:
        if task_id in tasks:
            tasks[task_id]["running"] = False
            time.sleep(1)
            del tasks[task_id]
            return {"message": f"Task {task_id} has been canceled"}
        return JSONResponse(status_code=404, content={"error": "Task not found"})
    except Exception as e:
        logger.error(f"Error canceling task {task_id}: {str(e)}")
        return JSONResponse(status_code=500, content={"error": f"An error occurred: {str(e)}"})


@app.get("/download-search/{task_id}")
def download_search_results(task_id: str):
    try:
        if task_id not in tasks or not tasks[task_id]["results"]:
            return JSONResponse(status_code=404, content={"error": "No results found"})

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
    except Exception as e:
        logger.error(f"Error downloading search results for task {task_id}: {str(e)}")
        return JSONResponse(status_code=500, content={"error": f"An error occurred: {str(e)}"})


# This endpoint will help with debugging by showing all active tasks
@app.get("/debug/tasks")
def get_all_tasks():
    task_info = {}
    for task_id, task in tasks.items():
        # Create a copy without the potentially large results array
        task_copy = task.copy()
        if "results" in task_copy:
            task_copy["result_count"] = len(task_copy["results"])
            del task_copy["results"]
        task_info[task_id] = task_copy
    
    return {"tasks": task_info}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
