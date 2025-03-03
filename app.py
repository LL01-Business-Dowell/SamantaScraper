import time
import csv
import os
import random
import pandas as pd
import re
import json
import requests
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# Discord webhook URL for notifications
DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/1346054612855296000/GNuZ9GXWEfaVmmeSDp6ZBws9akL_BztMENNVY0Aa-zIbA9vzGN1HDRvoZf9cfsj7yyYF"

# Function to send enhanced notifications to Discord
def send_discord_notification(message, title=None, color=5814783, fields=None, thumbnail=None, footer=None):
    """
    Send an enhanced notification to Discord via webhook
    
    Args:
        message (str): The message to send
        title (str, optional): The title of the embed
        color (int, optional): The color of the embed sidebar (decimal)
        fields (list, optional): List of field dicts with name, value, inline keys
        thumbnail (str, optional): URL to thumbnail image
        footer (str, optional): Footer text
    """
    timestamp = datetime.now().isoformat()
    current_time = datetime.now().strftime("%H:%M:%S - %d/%m/%Y")
    
    embed = {
        "description": message,
        "color": color,
        "timestamp": timestamp
    }
    
    if title:
        embed["title"] = title
    
    # Add author with avatar
    embed["author"] = {
        "name": "Samanta Scraper",
        "icon_url": "https://dowellfileuploader.uxlivinglab.online/hr/logo-2-min-min.png"  # You can replace with your own icon
    }
    
    # Add fields if provided
    if fields:
        embed["fields"] = fields
    
    # Add thumbnail if provided
    if thumbnail:
        embed["thumbnail"] = {"url": thumbnail}
    
    # Add footer with timestamp
    embed["footer"] = {
        "text": footer if footer else f"Scraped at {current_time}"
    }
    
    data = {"embeds": [embed]}
        
    try:
        response = requests.post(
            DISCORD_WEBHOOK_URL,
            data=json.dumps(data),
            headers={"Content-Type": "application/json"}
        )
        if response.status_code != 204:
            print(f"Failed to send Discord notification: {response.status_code}")
    except Exception as e:
        print(f"Error sending Discord notification: {str(e)}")

# Define color constants for better readability
COLOR_SUCCESS = 3066993  # Green
COLOR_INFO = 3447003     # Blue
COLOR_WARNING = 16776960 # Yellow
COLOR_ERROR = 15158332   # Red

# Folder configurations
CSV_FOLDER = "output"
os.makedirs(CSV_FOLDER, exist_ok=True)
input_file = "pincode.csv"
output_urls_file = f"{CSV_FOLDER}/business_urls.csv"
output_details_file = f"{CSV_FOLDER}/business_details.csv"

# Send startup notification
send_discord_notification(
    "Web scraper has been initialized and is ready to process data.",
    "🚀 Scraper Started", 
    COLOR_SUCCESS,
    fields=[
        {"name": "Input File", "value": input_file, "inline": True},
        {"name": "Output Directory", "value": CSV_FOLDER, "inline": True},
        {"name": "Target", "value": "Home Appliances businesses in Singapore", "inline": False}
    ],
    footer="Scraper Version 1.0"
)

# Check if input file exists
if not os.path.exists(input_file):
    message = f"Input file '{input_file}' not found! Creating sample file..."
    print(message)
    
    # Create a sample pincode file if it doesn't exist
    with open(input_file, "w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(["postalCode"])
        writer.writerow(["018936"])  # Marina Bay Sands
        writer.writerow(["238823"])  # Orchard Road
        writer.writerow(["049483"])  # Raffles Place
    
    send_discord_notification(
        f"Created a sample input file with Singapore postal codes.",
        "⚠️ Input File Created", 
        COLOR_WARNING,
        fields=[
            {"name": "File Path", "value": input_file, "inline": True},
            {"name": "Sample Postcodes", "value": "018936, 238823, 049483", "inline": True},
            {"name": "Action", "value": "Replace with your own postal codes for production use", "inline": False}
        ]
    )

df = pd.read_csv(input_file)
postal_codes = df["postalCode"].astype(str).unique()

send_discord_notification(
    f"Loaded postal codes from input file and ready to begin processing.",
    "📋 Data Loaded", 
    COLOR_INFO,
    fields=[
        {"name": "Total Postal Codes", "value": str(len(postal_codes)), "inline": True},
        {"name": "First Few Codes", "value": ", ".join(postal_codes[:3]) + ("..." if len(postal_codes) > 3 else ""), "inline": True}
    ]
)

def init_driver():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-gpu")
    
    # Use installed Chrome in Docker
    if os.environ.get('GOOGLE_CHROME_BIN'):
        options.binary_location = os.environ.get('GOOGLE_CHROME_BIN')
    
    # Try different paths for chromedriver
    chromedriver_paths = [
        os.environ.get('CHROMEDRIVER_PATH'),
        '/usr/local/bin/chromedriver',
        '/usr/local/bin/chromedriver-linux64/chromedriver'
    ]
    
    for path in chromedriver_paths:
        if path and os.path.exists(path):
            print(f"Using chromedriver at: {path}")
            send_discord_notification(
                f"WebDriver initialized successfully.",
                "🔧 WebDriver Ready", 
                COLOR_INFO,
                fields=[
                    {"name": "ChromeDriver Path", "value": path, "inline": False},
                    {"name": "Mode", "value": "Headless", "inline": True},
                    {"name": "Window Size", "value": "1920x1080", "inline": True}
                ]
            )
            return webdriver.Chrome(service=Service(path), options=options)
    
    # Fallback to webdriver manager
    print("No chromedriver found in predefined paths, using webdriver-manager")
    send_discord_notification(
        "WebDriver Manager will be used to download the appropriate ChromeDriver.",
        "⚙️ WebDriver Manager", 
        COLOR_INFO,
        fields=[
            {"name": "Fallback Method", "value": "webdriver-manager", "inline": True},
            {"name": "Reason", "value": "No ChromeDriver found in predefined paths", "inline": True}
        ]
    )
    return webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

send_discord_notification(
    "Setting up WebDriver for browser automation...",
    "🌐 Setup In Progress", 
    COLOR_INFO
)

driver = init_driver()
business_urls = set()

def clean_text(text):
    if text:
        text = re.sub(r"[^\x20-\x7E]", "", text)
        return text.strip()
    return "N/A"

def get_google_maps_urls(postal_code, max_retries=3):
    search_query = f"Home Appliances in {postal_code}, Singapore"
    search_url = f"https://www.google.com/maps/search/{search_query.replace(' ', '+')}"
    
    print(f"\nSearching for: {search_query} (Pincode: {postal_code})")
    
    send_discord_notification(
        f"Searching Google Maps for businesses in this area.",
        f"🔍 Search Started", 
        COLOR_INFO,
        fields=[
            {"name": "Search Query", "value": search_query, "inline": False},
            {"name": "Postal Code", "value": postal_code, "inline": True},
            {"name": "Country", "value": "Singapore", "inline": True}
        ]
    )

    for attempt in range(max_retries):
        try:
            driver.get(search_url)
            time.sleep(random.randint(5, 8))

            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//a[contains(@href, '/place/')]"))
            )
        except Exception as e:
            error_msg = f"Error on attempt {attempt+1}/{max_retries} for {postal_code}: {str(e)}"
            print(error_msg)
            
            if attempt == max_retries - 1:
                send_discord_notification(
                    f"All retry attempts failed for this postal code.",
                    "❌ Search Failed", 
                    COLOR_ERROR,
                    fields=[
                        {"name": "Postal Code", "value": postal_code, "inline": True},
                        {"name": "Attempts", "value": f"{attempt+1}/{max_retries}", "inline": True},
                        {"name": "Error", "value": f"```{str(e)}```", "inline": False}
                    ]
                )
            continue

        try:
            results_container = driver.find_elements(By.XPATH, "//div[@role='feed']")
            if not results_container:
                message = f"No results container found for {postal_code}, skipping..."
                print(message)
                
                send_discord_notification(
                    f"Could not find results container element in the page.",
                    "⚠️ No Results Container", 
                    COLOR_WARNING,
                    fields=[
                        {"name": "Postal Code", "value": postal_code, "inline": True},
                        {"name": "Action", "value": "Skipping this postal code", "inline": True}
                    ]
                )
                return []

            for _ in range(10):
                driver.execute_script("arguments[0].scrollTop += 1000;", results_container[0])
                time.sleep(random.uniform(2, 4))

            urls = []
            elements = driver.find_elements(By.XPATH, "//a[contains(@href, '/place/')]")
            count = 0
            for element in elements:
                url = element.get_attribute("href")
                if url and url not in business_urls:
                    business_urls.add(url)
                    urls.append(url)
                    count += 1
                if count >= 5:
                    break

            if urls:
                message = f"Found {len(urls)} businesses for Pincode {postal_code}"
                print(message)
                
                send_discord_notification(
                    f"Successfully found business listings for this postal code.",
                    "✅ Search Results", 
                    COLOR_SUCCESS,
                    fields=[
                        {"name": "Postal Code", "value": postal_code, "inline": True},
                        {"name": "Businesses Found", "value": str(len(urls)), "inline": True},
                        {"name": "URLs", "value": f"First few: {urls[0][:50]}...", "inline": False}
                    ]
                )
                return urls
        except Exception as e:
            error_msg = f"Error processing results for {postal_code}: {str(e)}"
            print(error_msg)
            
            send_discord_notification(
                f"Error while processing search results.",
                "❌ Processing Error", 
                COLOR_ERROR,
                fields=[
                    {"name": "Postal Code", "value": postal_code, "inline": True},
                    {"name": "Attempt", "value": f"{attempt+1}/{max_retries}", "inline": True},
                    {"name": "Error", "value": f"```{str(e)}```", "inline": False}
                ]
            )
            continue

    message = f"No valid results for {postal_code} after {max_retries} attempts"
    print(message)
    
    send_discord_notification(
        f"Could not find any valid business results after multiple attempts.",
        "⚠️ No Results Found", 
        COLOR_WARNING,
        fields=[
            {"name": "Postal Code", "value": postal_code, "inline": True},
            {"name": "Attempts", "value": str(max_retries), "inline": True},
            {"name": "Action", "value": "Moving to next postal code", "inline": False}
        ]
    )
    return []

send_discord_notification(
    f"Beginning URL collection process for all postal codes.",
    "🔄 Collection Started", 
    COLOR_INFO,
    fields=[
        {"name": "Total Postal Codes", "value": str(len(postal_codes)), "inline": True},
        {"name": "Target Business Type", "value": "Home Appliances", "inline": True},
        {"name": "Output File", "value": output_urls_file, "inline": False}
    ]
)

with open(output_urls_file, "w", newline="", encoding="utf-8") as file:
    writer = csv.writer(file)
    writer.writerow(["Business URL"])
    
    for index, postal_code in enumerate(postal_codes):
        urls = get_google_maps_urls(postal_code)
        for url in urls:
            writer.writerow([url])
        file.flush()
        
        # Calculate progress percentage and create progress bar
        progress_percent = round(((index+1)/len(postal_codes))*100, 1)
        progress_bar = "█" * int(progress_percent/10) + "░" * (10-int(progress_percent/10))
        
        message = f"Completed processing for Pincode {postal_code} ({index+1}/{len(postal_codes)})"
        print(message)
        
        # Send progress update every 5 postcodes or at beginning/end
        if (index + 1) % 5 == 0 or index == 0 or index == len(postal_codes) - 1:
            send_discord_notification(
                f"Processing postal codes...",
                "📊 Collection Progress", 
                COLOR_INFO,
                fields=[
                    {"name": "Completed", "value": f"{index+1}/{len(postal_codes)}", "inline": True},
                    {"name": "Percentage", "value": f"{progress_percent}%", "inline": True},
                    {"name": "Progress", "value": f"`{progress_bar}`", "inline": False},
                    {"name": "Latest Postal Code", "value": postal_code, "inline": True},
                    {"name": "URLs Found", "value": str(len(urls)), "inline": True}
                ]
            )
        
        if (index + 1) % 10 == 0:
            restart_msg = "Restarting WebDriver to prevent session timeout..."
            print(restart_msg)
            
            send_discord_notification(
                "Performing routine maintenance to ensure stability.",
                "♻️ WebDriver Restart", 
                COLOR_INFO,
                fields=[
                    {"name": "Reason", "value": "Preventing session timeout", "inline": True},
                    {"name": "Progress", "value": f"{index+1}/{len(postal_codes)}", "inline": True}
                ]
            )
            
            driver.quit()
            driver = init_driver()

driver.quit()

send_discord_notification(
    "Successfully completed the URL collection phase of the scraper.",
    "✅ URL Collection Complete", 
    COLOR_SUCCESS,
    fields=[
        {"name": "URLs Collected", "value": str(len(business_urls)), "inline": True},
        {"name": "Output File", "value": output_urls_file, "inline": True},
        {"name": "Next Phase", "value": "Business details collection", "inline": False}
    ]
)

def get_google_maps_details(url):
    try:
        driver.get(url)
        time.sleep(random.randint(3, 6))

        details = {
            "Name": "N/A",
            "Address": "N/A",
            "Phone": "N/A",
            "Rating": "N/A",
            "Reviews": "N/A",
            "Plus Code": "N/A",
            "Website": "N/A",
            "Google Maps URL": url
        }
        
        # Try to get name
        try:
            if driver.find_elements(By.XPATH, "//h1[contains(@class, 'DUwDvf')]"):
                details["Name"] = clean_text(driver.find_element(By.XPATH, "//h1[contains(@class, 'DUwDvf')]").text)
        except:
            pass
            
        # Try to get address
        try:
            if driver.find_elements(By.XPATH, "//button[@data-tooltip='Copy address']"):
                details["Address"] = clean_text(driver.find_element(By.XPATH, "//button[@data-tooltip='Copy address']").text)
        except:
            pass
            
        # Try to get phone
        try:
            if driver.find_elements(By.XPATH, "//button[@data-tooltip='Copy phone number']"):
                details["Phone"] = clean_text(driver.find_element(By.XPATH, "//button[@data-tooltip='Copy phone number']").text)
        except:
            pass
            
        # Try to get rating
        try:
            if driver.find_elements(By.XPATH, "//span[@class='MW4etd']"):
                details["Rating"] = clean_text(driver.find_element(By.XPATH, "//span[@class='MW4etd']").text)
        except:
            pass
            
        # Try to get reviews
        try:
            if driver.find_elements(By.XPATH, "//span[@class='UY7F9']"):
                details["Reviews"] = clean_text(driver.find_element(By.XPATH, "//span[@class='UY7F9']").text)
        except:
            pass
            
        # Try to get plus code
        try:
            if driver.find_elements(By.XPATH, "//button[@data-tooltip='Copy plus code']"):
                details["Plus Code"] = clean_text(driver.find_element(By.XPATH, "//button[@data-tooltip='Copy plus code']").text)
        except:
            pass
            
        # Try to get website
        try:
            if driver.find_elements(By.XPATH, "//a[contains(@aria-label, 'Visit') or contains(@href, 'http')]"):
                details["Website"] = clean_text(driver.find_element(By.XPATH, "//a[contains(@aria-label, 'Visit') or contains(@href, 'http')]").get_attribute("href"))
        except:
            pass
        
        return details
    except Exception as e:
        error_msg = f"Error scraping details for {url}: {str(e)}"
        print(error_msg)
        
        send_discord_notification(
            f"Failed to retrieve business details.",
            "❌ Details Extraction Error", 
            COLOR_ERROR,
            fields=[
                {"name": "URL", "value": url[:50] + "...", "inline": False},
                {"name": "Error", "value": f"```{str(e)}```", "inline": False}
            ]
        )
        
        return {
            "Name": "Error",
            "Address": "Error",
            "Phone": "Error",
            "Rating": "Error",
            "Reviews": "Error", 
            "Plus Code": "Error",
            "Website": "Error",
            "Google Maps URL": url
        }

driver = init_driver()

# Check if business_urls.csv exists
if os.path.exists(output_urls_file):
    with open(output_urls_file, "r", encoding="utf-8") as file:
        reader = csv.reader(file)
        next(reader)  # Skip header
        urls = [row[0] for row in reader]
    
    total_urls = len(urls)
    message = f"Found {total_urls} URLs to process for details..."
    print(message)
    
    send_discord_notification(
        f"Starting the business details extraction phase.",
        "🔄 Details Extraction Started", 
        COLOR_INFO,
        fields=[
            {"name": "Total URLs", "value": str(total_urls), "inline": True},
            {"name": "Output File", "value": output_details_file, "inline": True},
            {"name": "Expected Duration", "value": f"~{round(total_urls*5/60, 1)} hours", "inline": False}
        ]
    )
    
    with open(output_details_file, "w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(["Name", "Address", "Phone", "Rating", "Reviews", "Plus Code", "Website", "Google Maps URL"])
        
        for index, url in enumerate(urls):
            details = get_google_maps_details(url)
            writer.writerow([
                details["Name"], 
                details["Address"], 
                details["Phone"], 
                details["Rating"], 
                details["Reviews"], 
                details["Plus Code"], 
                details["Website"], 
                details["Google Maps URL"]
            ])
            file.flush()
            
            # Calculate progress
            progress_percent = round(((index+1)/total_urls)*100, 1)
            progress_bar = "█" * int(progress_percent/10) + "░" * (10-int(progress_percent/10))
            progress = f"({index+1}/{total_urls}) - {progress_percent}%"
            
            message = f"Processed business: {details['Name']} {progress}"
            print(message)
            
            # Send notification every 5 businesses or for the first and last
            if (index + 1) % 5 == 0 or index == 0 or index == total_urls - 1:
                # Create rating stars for visual appeal
                rating_stars = ""
                if details["Rating"] != "N/A" and details["Rating"] != "Error":
                    try:
                        rating_value = float(details["Rating"])
                        rating_stars = "⭐" * int(rating_value) + ("☆" if rating_value % 1 >= 0.5 else "")
                    except:
                        rating_stars = ""
                
                send_discord_notification(
                    f"Extracting business information...",
                    "📊 Details Progress", 
                    COLOR_INFO,
                    fields=[
                        {"name": "Business", "value": details["Name"], "inline": True},
                        {"name": "Phone", "value": details["Phone"], "inline": True},
                        {"name": "Rating", "value": f"{details['Rating']} {rating_stars}", "inline": False},
                        {"name": "Progress", "value": f"`{progress_bar}` {progress}", "inline": False},
                        {"name": "Address", "value": details["Address"][:50] + ("..." if len(details["Address"]) > 50 else ""), "inline": False}
                    ]
                )

            if (index + 1) % 20 == 0:
                restart_msg = f"♻️ Restarting WebDriver to prevent session timeout... ({index+1}/{total_urls})"
                print(restart_msg)
                
                send_discord_notification(
                    "Performing routine maintenance to ensure stability.",
                    "♻️ WebDriver Restart", 
                    COLOR_INFO,
                    fields=[
                        {"name": "Reason", "value": "Preventing session timeout", "inline": True},
                        {"name": "Progress", "value": f"{index+1}/{total_urls}", "inline": True}
                    ]
                )
                
                driver.quit()
                driver = init_driver()
else:
    error_msg = f"URLs file {output_urls_file} not found. Skipping business details collection."
    print(error_msg)
    
    send_discord_notification(
        f"Cannot find the URLs file needed for details extraction.",
        "❌ Missing File Error", 
        COLOR_ERROR,
        fields=[
            {"name": "Missing File", "value": output_urls_file, "inline": True},
            {"name": "Impact", "value": "Details collection phase will be skipped", "inline": True},
            {"name": "Resolution", "value": "Run the URL collection phase first", "inline": False}
        ]
    )

driver.quit()

# Final completion notification with summary statistics
if os.path.exists(output_details_file):
    try:
        # Get some basic stats from the output file
        df_results = pd.read_csv(output_details_file)
        valid_results = len(df_results[df_results["Name"] != "Error"])
        avg_rating = df_results[df_results["Rating"] != "N/A"][df_results["Rating"] != "Error"]["Rating"].astype(float).mean()
        has_website = len(df_results[df_results["Website"] != "N/A"][df_results["Website"] != "Error"])
        has_phone = len(df_results[df_results["Phone"] != "N/A"][df_results["Phone"] != "Error"])
        
        completion_msg = f"Scraping complete! Data saved to {output_details_file}"
        print(completion_msg)
        
        send_discord_notification(
            f"Successfully completed all scraping tasks!",
            "🎉 Scraping Complete", 
            COLOR_SUCCESS,
            fields=[
                {"name": "Total Businesses", "value": str(len(df_results)), "inline": True},
                {"name": "Valid Entries", "value": f"{valid_results} ({round(valid_results/len(df_results)*100)}%)", "inline": True},
                {"name": "Average Rating", "value": f"{round(avg_rating, 2)} ⭐" if not pd.isna(avg_rating) else "N/A", "inline": False},
                {"name": "With Websites", "value": f"{has_website} ({round(has_website/len(df_results)*100)}%)", "inline": True},
                {"name": "With Phone", "value": f"{has_phone} ({round(has_phone/len(df_results)*100)}%)", "inline": True},
                {"name": "Output File", "value": output_details_file, "inline": False}
            ],
            footer="Scraping completed successfully"
        )
    except Exception as e:
        # Simpler completion message if stats calculation fails
        completion_msg = f"Scraping complete! Data saved to {output_details_file}"
        print(completion_msg)
        
        send_discord_notification(
            f"Successfully completed all scraping tasks!",
            "🎉 Scraping Complete", 
            COLOR_SUCCESS,
            fields=[
                {"name": "Output File", "value": output_details_file, "inline": False}
            ]
        )
else:
    # If no output file exists
    completion_msg = "Scraping process completed but no output file was generated."
    print(completion_msg)
    
    send_discord_notification(
        "Scraping process has ended but no output file was generated.",
        "⚠️ Process Complete - No Output", 
        COLOR_WARNING
    )

