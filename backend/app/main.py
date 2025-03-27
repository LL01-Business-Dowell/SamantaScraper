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

app = FastAPI()

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
    options.binary_location = os.getenv("GOOGLE_CHROME_BIN", "/usr/bin/google-chrome")
    service = Service(os.getenv("CHROMEDRIVER_PATH", "/usr/local/bin/chromedriver"))
    
    return webdriver.Chrome(service=service, options=options)  # ✅ Added return statement

def scrape_google_maps(task_id, postal_codes, keyword, location):
    """Scrapes Google Maps search results for business information."""
    driver = init_driver()
    results = []
    
    for idx, postal_code in enumerate(postal_codes):
        if not tasks[task_id]["running"]:
            break  # Stop if canceled

        search_query = f"{keyword} in {postal_code}, {location}"
        google_maps_url = f"https://www.google.com/maps/search/{search_query.replace(' ', '+')}"
        
        try:
            driver.get(google_maps_url)
            time.sleep(3)

            business_links = []
            elements = driver.find_elements(By.CSS_SELECTOR, 'a[href*="/maps/place/"]')
            business_links = [e.get_attribute("href") for e in elements[:20]]

            for url in business_links:
                if not tasks[task_id]["running"]:
                    break

                driver.get(url)
                time.sleep(2)
                
                try:
                    name = clean_text(driver.find_element(By.CSS_SELECTOR, "h1").text)
                    address = clean_text(driver.find_element(By.CSS_SELECTOR, '[data-item-id="address"]').text)
                    phone = clean_text(driver.find_element(By.CSS_SELECTOR, '[data-tooltip="Copy phone number"]').text)
                    
                    website = "Not Available"
                    website_element = driver.find_element(By.CSS_SELECTOR, 'a[href^="http"][data-item-id="authority"]')
                    if website_element:
                        website = clean_text(website_element.get_attribute("href"))

                    results.append({
                        "Postal Code": postal_code,
                        "Name": name,
                        "Address": address,
                        "Phone": phone,
                        "Website": website,
                        "URL": url
                    })
                except Exception as e:
                    print(f"Error processing business {url}: {e}")
                    continue  # Skip this entry and move to the next

        except Exception as e:
            print(f"Error accessing {google_maps_url}: {e}")
            continue  # Skip this postal code and move to the next

        tasks[task_id]["progress"] = (idx + 1) / len(postal_codes) * 100
        tasks[task_id]["results"] = results

    driver.quit()
    tasks[task_id]["running"] = False

@app.post("/upload/")
async def upload_csv(file: UploadFile, keyword: str = Form(...), location: str = Form(...)):
    """Handles CSV file upload and starts the scraping process."""
    task_id = str(time.time())
    df = pd.read_csv(file.file)
    postal_codes = df.iloc[:, 0].dropna().astype(str).tolist()

    tasks[task_id] = {"running": True, "progress": 0, "results": []}

    threading.Thread(target=scrape_google_maps, args=(task_id, postal_codes, keyword, location)).start()

    return {"message": "Processing started", "task_id": task_id}

@app.get("/progress/{task_id}")
async def get_progress(task_id: str):
    """Returns the progress of an ongoing scraping task."""
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
    """Cancels an ongoing scraping task."""
    if task_id in tasks:
        tasks[task_id]["running"] = False
        return {"message": "Task canceled"}
    return {"error": "Task not found"}

@app.get("/download/{task_id}")
def download_results(task_id: str):
    """Allows users to download scraped results as a CSV file."""
    if task_id not in tasks or not tasks[task_id]["results"]:
        return {"error": "No results found"}
    
    def iter_csv():
        yield "Postal Code,Name,Address,Phone,Website,URL\n"
        for row in tasks[task_id]["results"]:
            yield f"{row['Postal Code']},{row['Name']},{row['Address']},{row['Phone']},{row['Website']},{row['URL']}\n"
    
    return StreamingResponse(iter_csv(), media_type="text/csv", headers={"Content-Disposition": f"attachment; filename=results_{task_id}.csv"})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
