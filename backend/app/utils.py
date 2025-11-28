import csv
import io
import logging
import datetime
import requests
from typing import List, Dict, Any
from decouple import config

inscriber_url = config("INSCRIBER_URL")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def log_message(message):
    """Add message to logs and print it"""
    timestamp = datetime.datetime.now().strftime('%H:%M:%S')
    log_entry = f"[{timestamp}] {message}"
    print(log_entry)
    logger.info(log_entry)

def parse_csv(file_content: bytes) -> List[str]:
    """
    Parse CSV file content and extract postal codes.
    
    Args:
        file_content: Raw bytes content of the uploaded CSV file
        
    Returns:
        List of postal codes from the CSV
    """
    csv_text = file_content.decode('utf-8')
    reader = csv.DictReader(io.StringIO(csv_text))
    
    postal_codes = []
    for row in reader:
        if 'postal_code' in row:
            postal_codes.append(str(row['postal_code']).strip())
    
    return postal_codes

def format_results_for_csv(results: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    """
    Format search results for CSV export.
    
    Args:
        results: List of result dictionaries
        
    Returns:
        Formatted list of dictionaries for CSV export
    """
    formatted_results = []
    
    for result in results:
        formatted_result = {
            "Name": result.get("name", ""),
            "Address": result.get("address", ""),
            "Phone": result.get("phone", ""),
            "Website": result.get("website", ""),
            "Rating": result.get("rating", ""),
            "Reviews": result.get("reviews", ""),
            "Postal Code": result.get("postal_code", "")
        }
        formatted_results.append(formatted_result)
    
    return formatted_results

def calculate_boundary_points(d):

    # d: distance specified by the user in KM

    lat = 0.000000000000000  
    lon = 0.000000000000000
    t = 0.00899321605918700 

    top_left = tuple((lat + d*t, lon - d*t))
    top_right = tuple((lat + d*t, lon + d*t))
    bottom_left = tuple((lat - d*t, lon - d*t))
    bottom_right = tuple((lat - d*t, lon + d*t))

    print(f"Top Left: {top_left}, Top Right: {top_right}, Bottom Left: {bottom_left}, Bottom Right: {bottom_right}")

    top_mid = tuple((lat + d*t, lon))
    bottom_mid = tuple((lat - d*t, lon))
    left_mid = tuple((lat, lon - d*t))
    right_mid = tuple((lat, lon + d*t))

    return top_left, top_right, bottom_left, bottom_right

def fetch_inscriber_tiles(bounds):
    log_message("🔄 Requesting tiles from inscriber")
    try:
        payload = {
            "top_left": bounds[0],
            "top_right": bounds[1],
            "bottom_left": bounds[2],
            "bottom_right": bounds[3]
        }

        resp = requests.post(inscriber_url, json=payload, timeout=(10, 300))
        resp.raise_for_status()

        data = resp.json()

        # Log how many points were returned
        if isinstance(data, list):
            log_message(f"🧩 Received {len(data)} tiles from inscriber")
        else:
            log_message("🧩 Received non-list response from inscriber")

        return data  #return json

    except Exception as e:
        log_message(f"⚠️ Inscriber fetch failed: {e}")
        return []
    

def apply_center_offset(center, inscribed_points):
    center_lat, center_lon = center
    final_points = []

    for item in inscribed_points:
        lat_offset = float(item["latitude"])
        lon_offset = float(item["longitude"])

        final_lat = center_lat + lat_offset
        final_lon = center_lon + lon_offset

        final_points.append({
            "latitude": final_lat,
            "longitude": final_lon
        })

    return final_points
