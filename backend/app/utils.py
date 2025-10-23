import csv
import io
from typing import List, Dict, Any

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