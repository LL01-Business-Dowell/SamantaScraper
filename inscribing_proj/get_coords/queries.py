import traceback
import json
import requests
from decouple import config
import time

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

    # ---- Extract bounding box ----
    top_lat = top_left["latitude"]
    bottom_lat = bottom_left["latitude"]
    left_lng = top_left["longitude"]
    right_lng = top_right["longitude"]

    # Convert latitudes to integer “bands”
    top_lat_band = int(top_lat)
    bottom_lat_band = int(bottom_lat)

    # ---- Fetch latitude index ----
    # latitude_collections = get_latitude_collections()
    index_start = time.time()
    latitude_collections = get_latitude_collections()
    index_duration = time.time() - index_start
    print(f"\n=== Time to fetch latitude index: {index_duration:.2f} seconds ===")
    print(f"Collections returned: {len(latitude_collections)}")

    # Convert index keys to integer bands
    numeric_lats = [int(float(c.replace("latitude_", ""))) for c in latitude_collections]

    # Binary search with integer bands
    start_index = binary_search(numeric_lats, top_lat_band)
    end_index = binary_search(numeric_lats, bottom_lat_band)

    # if start_index < 0 or end_index < 0:
    #     return {"error": "Latitude range not found in index"}

    if start_index < 0 or end_index < 0:
        total_duration = time.time() - total_start
        print(f"\n=== ERROR: Latitude range not found (after {total_duration:.2f} sec) ===")
        return {"error": "Latitude range not found in index"}

    selected = latitude_collections[start_index:end_index + 1]

    data_start = time.time()
    results = []

    # ---- Query each selected collection ----
    for coll in selected:
        filters = {
            "longitude": {
                "$gte": left_lng,
                "$lte": right_lng,
            }
        }

        data = get_data_datacube(collection_name=coll, filters=filters)
        docs = data.get("result", {}).get("documents", [])
        results.extend(docs)
    
    data_duration = time.time() - data_start
    print(f"\n=== Time to fetch data from Datacube: {data_duration:.2f} seconds ===")

    # ---- Final total time ----
    total_duration = time.time() - total_start
    print(f"\n=== TOTAL Datacube query time: {total_duration:.2f} seconds ===")

    return {
        "count": len(results),
        "documents": results,
        "collections_scanned": selected
    }

