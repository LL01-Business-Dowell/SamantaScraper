from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import time
from typing import List, Dict, Any
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def setup_selenium_driver():
    """
    Set up and return a Selenium WebDriver for Chrome in headless mode.
    """
    try:
        # Chrome options
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        
        # In Docker, the chromedriver is installed at /usr/local/bin/chromedriver
        service = Service('/usr/local/bin/chromedriver')
        
        driver = webdriver.Chrome(service=service, options=chrome_options)
        return driver
    except Exception as e:
        logger.error(f"Error setting up Selenium driver: {str(e)}")
        raise

def perform_google_maps_search(driver, search_query: str, postal_code: str) -> List[Dict[str, Any]]:
    """
    Perform a search on Google Maps and extract results.
    
    Args:
        driver: Selenium WebDriver
        search_query: Query string to search
        postal_code: Postal code for this search
        
    Returns:
        List of dictionaries with business details
    """
    results = []
    
    try:
        # Go to Google Maps
        driver.get("https://www.google.com/maps")
        
        # Wait for the search box to be visible and click on it
        wait = WebDriverWait(driver, 10)
        search_box = wait.until(EC.element_to_be_clickable((By.ID, "searchboxinput")))
        search_box.clear()
        search_box.send_keys(search_query)
        search_box.send_keys(Keys.ENTER)
        
        # Wait for results to load
        time.sleep(3)
        
        # Wait for the results
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div[role='feed']")))
        
        # Extract results
        result_elements = driver.find_elements(By.CSS_SELECTOR, "div[role='feed'] > div")
        
        # Loop through each result to extract details
        for result in result_elements[:20]:  # Limit to first 20 results to avoid long execution
            try:
                # Click on the result to show details
                result.click()
                time.sleep(1)
                
                # Wait for details panel
                wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.xALUmb")))
                
                # Extract details
                name = ""
                address = ""
                phone = ""
                website = ""
                rating = ""
                reviews = ""
                
                # Name
                try:
                    name_element = driver.find_element(By.CSS_SELECTOR, "h1.DUwDvf")
                    name = name_element.text
                except:
                    pass
                
                # Address
                try:
                    address_element = driver.find_element(By.CSS_SELECTOR, "button[data-item-id='address']")
                    address = address_element.text
                except:
                    pass
                
                # Phone
                try:
                    phone_element = driver.find_element(By.CSS_SELECTOR, "button[data-tooltip='Copy phone number']")
                    phone = phone_element.text
                except:
                    pass
                
                # Website
                try:
                    website_element = driver.find_element(By.CSS_SELECTOR, "a[data-item-id='authority']")
                    website = website_element.get_attribute("href")
                except:
                    pass
                
                # Rating
                try:
                    rating_element = driver.find_element(By.CSS_SELECTOR, "div.F7nice")
                    rating_text = rating_element.text
                    rating = rating_text.split()[0]
                    reviews = rating_text.split("(")[1].split(")")[0] if "(" in rating_text else ""
                except:
                    pass
                
                # Add to results if name exists
                if name:
                    results.append({
                        "name": name,
                        "address": address,
                        "phone": phone,
                        "website": website,
                        "rating": rating,
                        "reviews": reviews,
                        "postal_code": postal_code
                    })
                
                # Go back to results
                driver.back()
                time.sleep(1)
                
            except Exception as e:
                logger.error(f"Error processing result: {str(e)}")
                continue
        
        return results
    
    except Exception as e:
        logger.error(f"Error during Google Maps search: {str(e)}")
        return results