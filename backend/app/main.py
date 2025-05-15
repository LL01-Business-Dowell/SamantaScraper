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

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173",
                   "https://map.uxlivinglab.online"],  # React frontend URL
    allow_credentials=True,
    allow_methods=["*"],  # Allow all HTTP methods (GET, POST, etc.)
    allow_headers=["*"],  # Allow all headers
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
        
        options = Options()
        options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--window-size=1920,1080")

        # Docker-specific ChromeDriver configuration
        chrome_binary = os.getenv("GOOGLE_CHROME_BIN", "/usr/bin/google-chrome")
        chromedriver_path = os.getenv("CHROMEDRIVER_PATH", "/usr/local/bin/chromedriver")
        
        logger.info(f"Using Chrome binary at: {chrome_binary}")
        logger.info(f"Using ChromeDriver at: {chromedriver_path}")
        
        options.binary_location = chrome_binary
        service = Service(chromedriver_path)
        
        driver = webdriver.Chrome(service=service, options=options)
        yield driver
    except Exception as e:
        logger.error(f"Failed to initialize WebDriver: {str(e)}")
        logger.error(traceback.format_exc())
        raise
    finally:
        if driver:
            try:
                driver.quit()
            except Exception as e:
                logger.error(f"Error closing WebDriver: {str(e)}")


def scrape_google_maps(task_id, location_data, keyword):
    """Thread function to scrape Google Maps based on location data."""
    try:
        with init_driver() as driver:
            results = []

            for idx, (postal_code, city, country) in enumerate(location_data):
                if not tasks.get(task_id, {}).get("running", False):
                    logger.info(f"Task {task_id} canceled. Exiting scraping process.")
                    return

                search_query = f"{keyword} in {postal_code}, {city}, {country}"
                google_maps_url = f"https://www.google.com/maps/search/{search_query.replace(' ', '+')}"

                try:
                    logger.info(f"Searching: {google_maps_url}")
                    driver.get(google_maps_url)
                    time.sleep(3)

                    from selenium.webdriver.common.by import By
                    
                    business_links = []
                    elements = driver.find_elements(By.CSS_SELECTOR, 'a[href*="/maps/place/"]')
                    business_links = [e.get_attribute("href") for e in elements[:20]]

                    for url in business_links:
                        if not tasks.get(task_id, {}).get("running", False):
                            logger.info(f"Task {task_id} canceled. Exiting business details extraction.")
                            return

                        driver.get(url)
                        time.sleep(2)

                        try:
                            name = clean_text(driver.find_element(By.CSS_SELECTOR, "h1").text)
                            
                            # Use safer methods to find elements that might not exist
                            address = "Not Available"
                            try:
                                address_elem = driver.find_element(By.CSS_SELECTOR, '[data-item-id="address"]')
                                address = clean_text(address_elem.text)
                            except Exception:
                                logger.warning(f"Address not found for {url}")
                            
                            phone = "Not Available"
                            try:
                                phone_elem = driver.find_element(By.CSS_SELECTOR, '[data-tooltip="Copy phone number"]')
                                phone = clean_text(phone_elem.text)
                            except Exception:
                                logger.warning(f"Phone not found for {url}")

                            website = "Not Available"
                            try:
                                website_element = driver.find_element(By.CSS_SELECTOR, 'a[href^="http"][data-item-id="authority"]')
                                website = clean_text(website_element.get_attribute("href"))
                            except Exception:
                                logger.warning(f"Website not found for {url}")

                            results.append({
                                "Postal Code": postal_code,
                                "Name": name,
                                "Address": address,
                                "Phone": phone,
                                "Website": website,
                                "URL": url,
                                "City": city,
                                "Country": country
                            })
                        except Exception as e:
                            logger.error(f"Error processing business {url}: {str(e)}")
                            continue

                except Exception as e:
                    logger.error(f"Error accessing {google_maps_url}: {str(e)}")
                    continue

                tasks[task_id]["progress"] = (idx + 1) / len(location_data) * 100
                tasks[task_id]["results"] = results

    except Exception as e:
        logger.error(f"Error in scrape_google_maps for task {task_id}: {str(e)}")
        logger.error(traceback.format_exc())
    finally:
        tasks[task_id]["running"] = False


def scrape_google_maps_location(task_id, keyword, country, city):
    """Thread function to scrape Google Maps based on location."""
    try:
        with init_driver() as driver:
            if not tasks.get(task_id, {}).get("running", False):
                logger.info(f"Task {task_id} canceled. Exiting scraping process.")
                return

            search_query = f"{keyword} in {city}, {country}"
            google_maps_url = f"https://www.google.com/maps/search/{search_query.replace(' ', '+')}"

            try:
                from selenium.webdriver.common.by import By
                
                logger.info(f"Searching location: {google_maps_url}")
                driver.get(google_maps_url)
                time.sleep(3)

                extracted_urls = set()
                results = []
                total_count = 0

                for _ in range(10):  # Limit the number of scrolls to avoid infinite loops
                    if not tasks.get(task_id, {}).get("running", False):
                        logger.info(f"Task {task_id} canceled. Exiting scraping process.")
                        return

                    elements = driver.find_elements(By.CSS_SELECTOR, 'a[href*="/maps/place/"]')
                    new_links = {e.get_attribute("href") for e in elements} - extracted_urls

                    for url in new_links:
                        if not tasks.get(task_id, {}).get("running", False):
                            logger.info(f"Task {task_id} canceled. Exiting business details extraction.")
                            return

                        extracted_urls.add(url)

                        driver.get(url)
                        time.sleep(2)

                        try:
                            name = clean_text(driver.find_element(By.CSS_SELECTOR, "h1").text)
                            
                            # Use safer methods to find elements that might not exist
                            address = "Not Available"
                            try:
                                address_elem = driver.find_element(By.CSS_SELECTOR, '[data-item-id="address"]')
                                address = clean_text(address_elem.text)
                            except Exception:
                                logger.warning(f"Address not found for {url}")
                            
                            phone = "Not Available"
                            try:
                                phone_elem = driver.find_element(By.CSS_SELECTOR, '[data-tooltip="Copy phone number"]')
                                phone = clean_text(phone_elem.text)
                            except Exception:
                                logger.warning(f"Phone not found for {url}")

                            website = "Not Available"
                            try:
                                website_elements = driver.find_elements(By.CSS_SELECTOR, 'a[href^="http"][data-item-id="authority"]')
                                if website_elements:
                                    website = clean_text(website_elements[0].get_attribute("href"))
                            except Exception:
                                logger.warning(f"Website not found for {url}")

                            business_data = {
                                "Name": name,
                                "Address": address,
                                "Phone": phone,
                                "Website": website,
                                "URL": url,
                                "City": city,
                                "Country": country
                            }
                            results.append(business_data)

                            total_count += 1
                            tasks[task_id]["progress"] = total_count
                            tasks[task_id]["results"] = results

                        except Exception as e:
                            logger.error(f"Error processing business {url}: {str(e)}")
                            continue

                    if elements:
                        driver.execute_script("arguments[0].scrollIntoView();", elements[-1])
                        time.sleep(2)

                    end_marker = driver.find_elements(By.XPATH, "//div[contains(text(), 'You\'ve reached the end of the list.')]")
                    if end_marker:
                        logger.info("Reached the end of search results.")
                        break

            except Exception as e:
                logger.error(f"Error accessing {google_maps_url}: {str(e)}")

    except Exception as e:
        logger.error(f"Error in scrape_google_maps_location for task {task_id}: {str(e)}")
        logger.error(traceback.format_exc())
    finally:
        tasks[task_id]["running"] = False
        logger.info(f"Task {task_id} completed.")


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


@app.post("/upload/")
async def upload_csv(file: UploadFile = File(...), keyword: str = Form(...), email: str = Form(...)):
    try:
        task_id = str(time.time())
        
        # Add some logging
        logger.info(f"Starting upload task {task_id}")
        logger.info(f"File: {file.filename}, Keyword: {keyword}, Email: {email}")
        
        # Validate file
        if not file.filename.endswith('.csv'):
            raise HTTPException(status_code=400, detail="Only CSV files are allowed")
            
        # Read CSV with better error handling
        try:
            contents = await file.read()
            df = pd.read_csv(pd.io.common.BytesIO(contents))
            file.file.close()  # Close the file after reading
        except Exception as e:
            logger.error(f"Error reading CSV: {str(e)}")
            raise HTTPException(status_code=400, detail=f"Error reading CSV file: {str(e)}")

        # Validate CSV structure
        required_columns = 3  # Postal code, city, country
        if df.shape[1] < required_columns:
            raise HTTPException(
                status_code=400, 
                detail=f"CSV must have at least {required_columns} columns: postal code, city, country"
            )

        location_data = []
        for index, row in df.iterrows():
            postal_code = str(row.iloc[0]) if not pd.isna(row.iloc[0]) else ""
            city = str(row.iloc[1]) if not pd.isna(row.iloc[1]) else ""
            country = str(row.iloc[2]) if not pd.isna(row.iloc[2]) else ""

            location_data.append([postal_code, city, country])

        tasks[task_id] = {"running": True, "progress": 0, "results": []}

        # Start scraping in a separate thread
        threading.Thread(target=scrape_google_maps, args=(task_id, location_data, keyword), daemon=True).start()

        return {"message": "Processing started", "task_id": task_id}
    
    except HTTPException:
        raise  # Re-raise HTTPExceptions as they're already formatted correctly
    except Exception as e:
        logger.error(f"Unhandled error in upload_csv: {str(e)}")
        logger.error(traceback.format_exc())
        return JSONResponse(status_code=500, content={"error": f"An unexpected error occurred: {str(e)}"})


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

        tasks[task_id] = {"running": True, "progress": 0, "results": []}

        # Start scraping in a separate thread
        threading.Thread(target=scrape_google_maps_location, args=(task_id, keyword, country, city), daemon=True).start()

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
            return {
                "progress": task.get("progress", 0),
                "results": task.get("results", []),
                "running": task.get("running", False),
            }
        return JSONResponse(status_code=404, content={"error": "Task not found"})
    except Exception as e:
        logger.error(f"Error fetching progress for task {task_id}: {str(e)}")
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


@app.get("/download/{task_id}")
def download_results(task_id: str):
    try:
        if task_id not in tasks or not tasks[task_id]["results"]:
            return JSONResponse(status_code=404, content={"error": "No results found"})

        def iter_csv():
            # Create header row with all columns
            yield "Postal Code,Name,Address,Phone,Website,URL,City,Country\n"
            
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
                
                yield f"{postal_code},{name},{address},{phone},{website},{url},{city},{country}\n"

        return StreamingResponse(iter_csv(), media_type="text/csv", 
                               headers={"Content-Disposition": f"attachment; filename=results_{task_id}.csv"})
    except Exception as e:
        logger.error(f"Error downloading results for task {task_id}: {str(e)}")
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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
