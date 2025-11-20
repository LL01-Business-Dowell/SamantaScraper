import traceback
import json
import requests
from decouple import config
import time
import os

print("\n=== LOADING QUERIES.PY ===")

# ============================================================
# Load ENV VARIABLES
# ============================================================

try:
    DATABASE_ID = config("DATABASE_ID")
    DATABASE_NAME = config("DATABASE_NAME")
    INDEX_COLLECTION_NAME = config("INDEX_COLLECTION_NAME")

    API_KEY = config("API_KEY")
    BASE_DATACUBE_URL = config("BASE_DATACUBE_URL")

    CRUD_COORDS_PATH = config("CRUD_COORDS_PATH", default="/api/crud")
    CRUD_RESULTS_PATH = config("CRUD_RESULTS_PATH", default="/api/crud")

    CRUD_URL = f"{BASE_DATACUBE_URL.rstrip('/')}{CRUD_COORDS_PATH}"

    HEADERS = {
        "Authorization": f"Api-Key {API_KEY}",
        "Content-Type": "application/json"
    }

    print("Environment variables loaded:")
    print("DATABASE_ID:", DATABASE_ID)
    print("INDEX_COLLECTION_NAME:", INDEX_COLLECTION_NAME)
    print("API_KEY present:", bool(API_KEY))

except Exception as e:
    print("\n=== ERROR LOADING ENV VARIABLES ===")
    traceback.print_exc()
    print("===================================\n")
    raise


# ============================================================
# Utility: Normalize coordinates
# ============================================================

def _normalize_point(point):
    """
    Accept either:
    [lat, lon] → convert to {"latitude": lat, "longitude": lon}
    {"latitude": ..., "longitude": ...} → passthrough
    """
    if isinstance(point, (list, tuple)):
        if len(point) != 2:
            raise ValueError("Point list must be [latitude, longitude]")
        return {"latitude": point[0], "longitude": point[1]}

    if isinstance(point, dict):
        if "latitude" in point and "longitude" in point:
            return point

    raise ValueError("Invalid point format. Must be [lat, lon] or {latitude, longitude}")


# ============================================================
# Datacube Generic Query
# ============================================================

def get_data_datacube(collection_name=None, filters=None, page_size=200):
    """
    Call Datacube Fetch API.
    """
    if collection_name is None:
        collection_name = INDEX_COLLECTION_NAME

    if filters is None:
        filters = {}

    params = {
        "database_id": DATABASE_ID,
        "collection_name": collection_name,
        "filters": json.dumps(filters),
        "page": 1,
        "page_size": page_size,
    }

    try:
        response = requests.get(CRUD_URL, params=params, headers=HEADERS)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        raise Exception(f"Datacube request failed: {e}")


# ============================================================
# Fetch list of latitude collections
# ============================================================

def get_latitude_collections():
    start = time.time()

    try:
        result = get_data_datacube(collection_name=INDEX_COLLECTION_NAME)
        duration = time.time() - start

        collections = result.get("result", {}).get("collections", [])

        print(f"\n=== Datacube index fetch time: {duration:.2f} seconds ===")
        print(f"Collections returned: {len(collections)}")

        collections.sort()
        return collections

    except Exception as e:
        duration = time.time() - start
        print(f"\n=== Datacube index fetch FAILED after {duration:.2f} seconds ===")

        raise Exception(f"Failed to fetch latitude index: {e}")


# ============================================================
# Binary Search Helper
# ============================================================

def binary_search(arr, value):
    low, high = 0, len(arr) - 1

    while low <= high:
        mid = (low + high) // 2
        mid_val = arr[mid]

        if mid_val == value:
            return mid
        elif mid_val < value:
            low = mid + 1
        else:
            high = mid - 1

    return high  # nearest lower index


# ============================================================
# Main: Datacube Bounding Box Query
# ============================================================

def query_by_four_corners_datacube(top_left, top_right, bottom_left, bottom_right):
    total_start = time.time()

    # ---- Normalize inputs ----
    top_left = _normalize_point(top_left)
    top_right = _normalize_point(top_right)
    bottom_left = _normalize_point(bottom_left)
    bottom_right = _normalize_point(bottom_right)

    print("\n=== Normalized Coordinates ===")
    print("TL:", top_left)
    print("TR:", top_right)
    print("BL:", bottom_left)
    print("BR:", bottom_right)

    # ---- Build payload for inscriber ----
    payload = {
        "top_left": [top_left["latitude"], top_left["longitude"]],
        "top_right": [top_right["latitude"], top_right["longitude"]],
        "bottom_left": [bottom_left["latitude"], bottom_left["longitude"]],
        "bottom_right": [bottom_right["latitude"], bottom_right["longitude"]],
    }

    INSCRIBER_URL = os.getenv("INSCRIBER_URL")

    try:
        print("\n=== Sending payload to inscriber ===")
        print("URL:", INSCRIBER_URL)
        print("Payload:", json.dumps(payload, indent=2))

        data_start = time.time()
        response = requests.post(INSCRIBER_URL, json=payload)
        data_duration = time.time() - data_start

        print(f"\n=== Time to fetch data from inscriber: {data_duration:.2f} seconds ===")
        response.raise_for_status()
        inscriber_result = response.json()

        # ---- Wrap inscriber response to match original format ----
        results = {
            "count": len(inscriber_result.get("documents", inscriber_result)),  # fallback if key not present
            "documents": inscriber_result.get("documents", inscriber_result),
            "collections_scanned": ["inscriber_endpoint"]
        }

    except Exception as e:
        data_duration = time.time() - data_start
        print(f"\n=== ERROR fetching data from inscriber after {data_duration:.2f} seconds ===")
        traceback.print_exc()
        return {"error": str(e)}

    # ---- Final total time ----
    total_duration = time.time() - total_start
    print(f"\n=== TOTAL Datacube query time: {total_duration:.2f} seconds ===")

    return results



