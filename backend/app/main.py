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
import os
import json
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import traceback
import requests

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


def clean_text(text):
    """Removes special characters and excessive whitespace from text."""
    return re.sub(r'[^\w\s,.-]', '', text).strip()


def init_driver():
    """Initializes and returns a Selenium WebDriver instance."""
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--window-size=1920,1080")

    # Docker-specific ChromeDriver configuration
    options.binary_location = os.getenv(
        "GOOGLE_CHROME_BIN", "/usr/bin/google-chrome")
    service = Service(os.getenv("CHROMEDRIVER_PATH",
                      "/usr/local/bin/chromedriver"))

    # ✅ Added return statement
    return webdriver.Chrome(service=service, options=options)


def scrape_google_maps(task_id, location_data, keyword):
    driver = init_driver()
    results = []

    for idx, (postal_code, city, country) in enumerate(location_data):
        if not tasks.get(task_id, {}).get("running", False):
            print(f"Task {task_id} canceled. Exiting scraping process.")
            driver.quit()
            return 

        search_query = f"{keyword} in {postal_code}, {city}, {country}"
        google_maps_url = f"https://www.google.com/maps/search/{search_query.replace(' ', '+')}"

        try:
            driver.get(google_maps_url)
            time.sleep(3)

            business_links = []
            elements = driver.find_elements(
                By.CSS_SELECTOR, 'a[href*="/maps/place/"]')
            business_links = [e.get_attribute("href") for e in elements[:20]]

            for url in business_links:
                if not tasks.get(task_id, {}).get("running", False):
                    print(
                        f"Task {task_id} canceled. Exiting business details extraction.")
                    driver.quit()
                    return 

                driver.get(url)
                time.sleep(2)

                try:
                    name = clean_text(driver.find_element(
                        By.CSS_SELECTOR, "h1").text)
                    address = clean_text(driver.find_element(
                        By.CSS_SELECTOR, '[data-item-id="address"]').text)
                    phone = clean_text(driver.find_element(
                        By.CSS_SELECTOR, '[data-tooltip="Copy phone number"]').text)

                    website = "Not Available"
                    website_element = driver.find_element(
                        By.CSS_SELECTOR, 'a[href^="http"][data-item-id="authority"]')
                    if website_element:
                        website = clean_text(
                            website_element.get_attribute("href"))

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
                    print(f"Error processing business {url}: {e}")
                    continue

        except Exception as e:
            print(f"Error accessing {google_maps_url}: {e}")
            continue 

        tasks[task_id]["progress"] = (idx + 1) / len(location_data) * 100
        tasks[task_id]["results"] = results

    driver.quit()
    tasks[task_id]["running"] = False


def scrape_google_maps_location(task_id, keyword, country, city):
    driver = init_driver()

    if not tasks.get(task_id, {}).get("running", False):
        print(f"Task {task_id} canceled. Exiting scraping process.")
        driver.quit()
        return 

    search_query = f"{keyword} in {city}, {country}"
    google_maps_url = f"https://www.google.com/maps/search/{search_query.replace(' ', '+')}"

    try:
        driver.get(google_maps_url)
        time.sleep(3)

        extracted_urls = set()
        results = []
        total_count = 0

        while True:
            if not tasks.get(task_id, {}).get("running", False):
                print(f"Task {task_id} canceled. Exiting scraping process.")
                driver.quit()
                return

            elements = driver.find_elements(
                By.CSS_SELECTOR, 'a[href*="/maps/place/"]')
            new_links = {e.get_attribute("href")
                         for e in elements} - extracted_urls

            for url in new_links:
                if not tasks.get(task_id, {}).get("running", False):
                    print(
                        f"Task {task_id} canceled. Exiting business details extraction.")
                    driver.quit()
                    return 

                extracted_urls.add(url)

                driver.get(url)
                time.sleep(2)

                try:
                    name = clean_text(driver.find_element(
                        By.CSS_SELECTOR, "h1").text)
                    address = clean_text(driver.find_element(
                        By.CSS_SELECTOR, '[data-item-id="address"]').text)
                    phone = clean_text(driver.find_element(
                        By.CSS_SELECTOR, '[data-tooltip="Copy phone number"]').text)

                    website = "Not Available"
                    website_element = driver.find_elements(
                        By.CSS_SELECTOR, 'a[href^="http"][data-item-id="authority"]')
                    if website_element:
                        website = clean_text(
                            website_element[0].get_attribute("href"))

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
                    print(f"Error processing business {url}: {e}")
                    continue 

            if elements:
                driver.execute_script(
                    "arguments[0].scrollIntoView();", elements[-1])
                time.sleep(2) 

            end_marker = driver.find_elements(
                By.XPATH, "//div[contains(text(), 'You\'ve reached the end of the list.')]")
            if end_marker:
                print("Reached the end of search results.")
                break

    except Exception as e:
        print(f"Error accessing {google_maps_url}: {e}")

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
    
@app.get("/search")
def search(query: str):
    try:
        country_files = [f for f in os.listdir(JSON_FOLDER) if f.endswith(".json")]


        for filename in country_files:
            file_path = os.path.join(JSON_FOLDER, filename)
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)

                for item in data:
                    city_name = (
                        item.get("ASCII Name", "") or item.get("Name", "")
                    ).lower()
                    alt_names = item.get("Alternate Names", "").lower()
                    if query.lower() in city_name or query.lower() in alt_names:
                        return {
                            "match_type": "city name",
                            "match": item
                        }

        for filename in country_files:
            file_path = os.path.join(JSON_FOLDER, filename)
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)

                for item in data:
                    if query.lower() == item.get("Country name EN", "").lower():
                        return {
                            "match_type": "country",
                            "match": item
                        }

        return JSONResponse(
            status_code=404,
            content={"error": "No match found. Please verify your search."}
        )

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

    threading.Thread(target=scrape_google_maps, args=(
        task_id, location_data, keyword)).start()

    return {"message": "Processing started", "task_id": task_id}


@app.post("/search-by-location/")
async def upload_csv(keyword: str = Form(...), country: str = Form(...), city: str = Form(...), email: str = Form(...)):
    task_id = str(time.time())

    tasks[task_id] = {"running": True, "progress": 0, "results": []}

    threading.Thread(target=scrape_google_maps_location, args=(
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
    uvicorn.run(app, host="127.0.0.1", port=8080)


@app.get("/search")
def search(query: str):
    try:
        url = "https://map.uxlivinglab.online/"
        response = requests.get(url)

        # Debugging: Print raw response content
        print(f"Raw response text: {response.text}")
        print(f"Response status code: {response.status_code}")

        if response.status_code != 200:
            return {"error": "Failed to fetch data"}

        try:
            data = response.json()
        except requests.exceptions.JSONDecodeError as e:
            print(f"JSON decode error: {str(e)}")
            return {"error": "Failed to decode JSON response"}

        # Debugging: Print the data structure
        print(f"Data received: {data}")

        for item in data:
            name = item.get("Name", "")
            ascii_name = item.get("ASCII Name", "")
            country = item.get("Country name EN", "")
            alt_names = item.get("Alternate Names", "")

            # Debugging: Print what we're checking
            print(f"Checking {name}, {ascii_name}, {country}, {alt_names}")

            if (
                query.lower() in name.lower() or
                query.lower() in ascii_name.lower() or
                query.lower() in country.lower() or
                query.lower() in alt_names.lower()
            ):
                return {"match": item}

        return {"error": f"No result found for '{query}'"}

    except Exception as e:
        print(f"Error: {str(e)}")
        return {"error": f"Internal server error: {str(e)}"}

