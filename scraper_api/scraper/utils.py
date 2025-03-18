import time
import random
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

def init_driver():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    return webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

def scrape_google_maps(search_query):
    driver = init_driver()
    url = f"https://www.google.com/maps/search/{search_query.replace(' ', '+')}"
    driver.get(url)
    time.sleep(random.randint(3, 5))

    business_data = []

    results = driver.find_elements("xpath", "//a[contains(@href, '/place/')]")
    for result in results:
        business_data.append(result.get_attribute("href"))

    driver.quit()
    return {"query": search_query, "results": business_data}
