import os
import json
import time
import traceback
import requests
from decouple import config


# ============================================================
# Load environment variables safely
# ============================================================

try:
    DATABASE_ID = config("DATABASE_ID")
    BASE_DATACUBE_URL = config("BASE_DATACUBE_URL")
    CRUD_URL = BASE_DATACUBE_URL + "api/crud"
    API_KEY = config("API_KEY")
    INDEX_COLLECTION_NAME = config("INDEX_COLLECTION_NAME")

    HEADERS = {
        "Authorization": f"Api-Key {API_KEY}",
        "Content-Type": "application/json"
    }

    print("Environment variables loaded:")
    print("DATABASE_ID:", DATABASE_ID)
    print("INDEX_COLLECTION_NAME:", INDEX_COLLECTION_NAME)
    print("API_KEY present:", bool(API_KEY))

except Exception:
    print("\n=== ERROR LOADING ENV VARIABLES ===")
    traceback.print_exc()
    print("===================================\n")
    raise



# ============================================================
# Datacube Generic Query
# ============================================================

def get_data_datacube(collection_name=None, filters=None, page_size=200):

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
        traceback.print_exc()
        raise Exception(f"Datacube request failed: {e}")



# ============================================================
# Normalize Point
# ============================================================

def _normalize_point(point):
    if isinstance(point, (list, tuple)):
        if len(point) != 2:
            raise ValueError("Point list must be [latitude, longitude]")
        return {"latitude": point[0], "longitude": point[1]}

    if isinstance(point, dict) and "latitude" in point and "longitude" in point:
        return point

    raise ValueError("Invalid point format. Must be [lat, lon] or {latitude, longitude}")



# ============================================================
# Fetch Latitude Collections
# ============================================================

def get_latitude_collections():
    start = time.time()

    try:
        result = get_data_datacube(collection_name=INDEX_COLLECTION_NAME)
        duration = time.time() - start

        collections = result.get("result", {}).get("collections", [])
        collections.sort()

        print(f"\n=== Datacube index fetch time: {duration:.2f} seconds ===")
        print(f"Collections returned: {len(collections)}")

        return collections

    except Exception as e:
        duration = time.time() - start
        print(f"\n=== Datacube index fetch FAILED after {duration:.2f} seconds ===")
        raise Exception(f"Failed to fetch latitude index: {e}")



# ============================================================
# Main bounding box → Send to Inscriber
# ============================================================

def query_by_four_corners_datacube(top_left, top_right, bottom_left, bottom_right):

    total_start = time.time()

    # Normalize
    top_left = _normalize_point(top_left)
    top_right = _normalize_point(top_right)
    bottom_left = _normalize_point(bottom_left)
    bottom_right = _normalize_point(bottom_right)

    payload = {
        "top_left": [top_left["latitude"], top_left["longitude"]],
        "top_right": [top_right["latitude"], top_right["longitude"]],
        "bottom_left": [bottom_left["latitude"], bottom_left["longitude"]],
        "bottom_right": [bottom_right["latitude"], bottom_right["longitude"]],
    }

    INSCRIBER_URL = os.getenv("INSCRIBER_URL")

    try:
        response = requests.post(INSCRIBER_URL, json=payload)
        response.raise_for_status()

        data = response.json()

        return {
            "count": len(data.get("documents", data)),
            "documents": data.get("documents", data),
            "collections_scanned": ["inscriber_endpoint"]
        }

    except Exception as e:
        traceback.print_exc()
        return {"error": str(e)}
