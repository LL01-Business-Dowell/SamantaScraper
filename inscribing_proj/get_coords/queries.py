import traceback
print("\n=== LOADING QUERIES.PY ===")

import json
import requests
from decouple import config


# ============================================================
# ENVIRONMENT VARIABLES (loaded correctly for Docker)
# ============================================================

# DATABASE_ID = config("DATABASE_ID")
# DATABASE_NAME = config("DATABASE_NAME")
# INDEX_COLLECTION_NAME = config("INDEX_COLLECTION_NAME")

# API_KEY = config("API_KEY")
# BASE_DATACUBE_URL = config("BASE_DATACUBE_URL")

# CRUD_COORDS_PATH = config("CRUD_COORDS_PATH")       # e.g. /api/crud
# CRUD_RESULTS_PATH = config("CRUD_RESULTS_PATH")     # currently same as coords path

# CRUD_URL = f"{BASE_DATACUBE_URL.rstrip('/')}{CRUD_COORDS_PATH}"


# HEADERS = {
#     "Authorization": f"Api-Key {API_KEY}",
#     "Content-Type": "application/json"
# }

try:
    # your existing code...
    DATABASE_ID = config("DATABASE_ID")
    DATABASE_NAME = config("DATABASE_NAME")
    INDEX_COLLECTION_NAME = config("INDEX_COLLECTION_NAME")

    API_KEY = config("API_KEY")
    BASE_DATACUBE_URL = config("BASE_DATACUBE_URL")

    CRUD_COORDS_PATH = config("CRUD_COORDS_PATH")
    CRUD_RESULTS_PATH = config("CRUD_RESULTS_PATH")

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
# Query Datacube (Generic)
# ============================================================

def get_data_datacube(collection_name=None, filters=None, page_size=200):
    """
    Fetch documents from Datacube using filters.
    Always JSON-encode filters and NEVER use mutable defaults.
    """
    if collection_name is None:
        collection_name = INDEX_COLLECTION_NAME

    if filters is None:
        filters = {}

    params = {
        "database_id": DATABASE_ID,
        "collection_name": collection_name,
        "filters": json.dumps(filters),    # VALID Datacube format
        "page": 1,
        "page_size": page_size,
    }

    try:
        response = requests.get(CRUD_URL, params=params, headers = HEADERS)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        raise Exception(f"Datacube request failed: {e}")


# ============================================================
# Get Index Collections (List of latitude_XXXXX)
# ============================================================

def get_latitude_collections():
    """
    Calls the Datacube index collection to fetch all latitude sub-collections.
    Sorted so that binary search works correctly.
    """
    try:
        result = get_data_datacube(collection_name=INDEX_COLLECTION_NAME)
        collections = result.get("result", {}).get("collections", [])
        collections.sort()  # ensure ordered scan
        return collections
    except Exception as e:
        raise Exception(f"Failed to fetch latitude index: {e}")


# ============================================================
# Binary Search
# ============================================================

def binary_search(arr, value):
    """Finds index in sorted array using binary search."""
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

    return high  # returns nearest lower index


# ============================================================
# Geo Query Using Datacube (Main Entry Function)
# ============================================================

def query_by_four_corners_datacube(top_left, top_right, bottom_left, bottom_right):
    """
    Your main function used by the Django API.
    Finds all documents inside a bounding box using Datacube.
    """

    # Extract bounding box values
    top_lat = top_left['latitude']
    bottom_lat = bottom_left['latitude']
    left_lng = top_left['longitude']
    right_lng = top_right['longitude']

    # Get all datacube collections for latitudes
    latitude_collections = get_latitude_collections()

    # Extract numeric latitude values for sorting (collections like latitude_37.421)
    numeric_lats = [float(x.replace("latitude_", "")) for x in latitude_collections]

    # Binary search for bounding collections
    start_index = binary_search(numeric_lats, top_lat)
    end_index = binary_search(numeric_lats, bottom_lat)

    if start_index == -1 or end_index == -1:
        return {"error": "Latitude range not found in index"}

    selected_collections = latitude_collections[start_index:end_index + 1]

    results = []

    # Query all latitude collections in the bounding range
    for coll_name in selected_collections:
        filters = {
            "longitude": {
                "$gte": left_lng,
                "$lte": right_lng
            }
        }

        data = get_data_datacube(collection_name=coll_name, filters=filters)

        # Each collection has "documents" under "result"
        docs = data.get("result", {}).get("documents", [])
        results.extend(docs)

    return {
        "count": len(results),
        "documents": results
    }
