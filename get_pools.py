## Sample Data:

    # [{
    #     "objectid": 98,
    #     "locationid": 272,
    #     "complexname": "St. Lawrence Community Recreation Centre",
    #     "location_type": "Indoor Pool",
    #     "x": -79.36493,
    #     "y": 43.649806999999996,
    #     "address": "230 The Esplanade  ",
    #     "website": "https://www.toronto.ca/explore-enjoy/parks-recreation/places-spaces/parks-and-recreation-facilities/location/?id=272",
    #     "show_on_map": "Yes",
    #     "activity_type": "Lane Swim, Leisure Swim, Aquatic Fitness: Shallow, Leisure Swim: Preschool, Aquatic Fitness: Deep",
    #     "globalid": "64664193-128d-4651-a1fd-ae78c5cfae41",
    #     "amenities": "Tot Pool, Universal Change Room",
    #     "created_date": 1651850979759,
    #     "created_user": "gccagol",
    #     "last_edited_date": 1730837911000,
    #     "last_edited_user": "gccagol",
    #     "swim_data": [
    #         {
    #             "status": "active",
    #             "start_time": "2025-03-17T06:30:00",
    #             "end_time": "2025-03-17T08:45:00",
    #             "id": 1
    #         },
    #         {
    #             "status": "active",
    #             "start_time": "2025-03-17T11:00:00",
    #             "end_time": "2025-03-17T13:15:00",
    #             "id": 1
    #         }
    #     ]
    # }]

from fastapi import FastAPI, Query, BackgroundTasks
from fastapi.responses import Response
from fastapi.openapi.utils import get_openapi
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
from typing import List, Optional
import json
import os
import yaml
import asyncio
import subprocess
import threading
import time

app = FastAPI()

# Add CORS middleware to allow browser requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# Global variable to track refresh task
refresh_task_running = False

def run_scraper():
    """Run the scraper to refresh data"""
    print("Running scraper to refresh pool data...")
    try:
        result = subprocess.run(["python", "scrape.py"],
                              capture_output=True, text=True, timeout=1800)  # 30 min timeout
        if result.returncode == 0:
            print("Scraper completed successfully")
        else:
            print(f"Scraper failed with code {result.returncode}: {result.stderr}")
    except subprocess.TimeoutExpired:
        print("Scraper timed out after 30 minutes")
    except Exception as e:
        print(f"Error running scraper: {e}")

def background_refresh_task():
    """Background task that runs the scraper once daily"""
    global refresh_task_running
    while refresh_task_running:
        run_scraper()
        # Wait 24 hours (86400 seconds)
        time.sleep(86400)

def start_background_refresh():
    """Start the background refresh task"""
    global refresh_task_running
    if not refresh_task_running:
        refresh_task_running = True
        thread = threading.Thread(target=background_refresh_task, daemon=True)
        thread.start()
        print("Background refresh task started - data will refresh once daily")

def get_pools(start_date: Optional[datetime] = None, end_date: Optional[datetime] = None) -> List[dict]:
    ## Create the tmp directory if it doesn't exist
    if not os.path.exists('tmp'):
        os.makedirs('tmp')
    with open('tmp/good_list_cache.json', 'r') as file:
        good_list = json.load(file)
    matched_pools = []
    matched_pool_ids = set()
    for pool in good_list:
        for swim_data in pool['swim_data']:
            start_time = datetime.strptime(swim_data['start_time'], "%Y-%m-%dT%H:%M:%S")
            end_time = datetime.strptime(swim_data['end_time'], "%Y-%m-%dT%H:%M:%S")
            # Filter by start_date and end_date if provided
            if start_date and start_time < start_date:
                continue
            if end_date and end_time > end_date:
                continue
            if pool["locationid"] not in matched_pool_ids:
                matched_pools.append(pool)
    return matched_pools

@app.get("/pools", response_model=List[dict])
async def pools(
    start_date: Optional[str] = Query(None, description="Filter pools starting from this datetime (YYYY-MM-DDTHH:MM:SS)"),
    end_date: Optional[str] = Query(None, description="Filter pools ending before this datetime (YYYY-MM-DDTHH:MM:SS)"),
    simple: Optional[bool] = Query(False, description="Return a simplified response with pool name and times")
):
    """
    Endpoint to get a list of pools with lane swims today at or after the current time.
    Supports filtering by start_date and end_date with hour, minute, and second precision,
    and a simplified response format.
    """
    # Parse start_date and end_date if provided
    start_date_parsed = datetime.strptime(start_date, "%Y-%m-%dT%H:%M:%S") if start_date else None
    end_date_parsed = datetime.strptime(end_date, "%Y-%m-%dT%H:%M:%S") if end_date else None

    # Get filtered pools
    matched_pools = get_pools(start_date=start_date_parsed, end_date=end_date_parsed)

    # If simple is True, return a simplified response
    if simple:
        return [
            {
                "pool_name": pool["complexname"],
                "website": pool.get("website", ""),
                "address": pool.get("address", "").strip(),
                "coordinates": {"x": pool.get("x", 0), "y": pool.get("y", 0)},
                "times": [
                    {
                        "start_time": swim_data["start_time"],
                        "end_time": swim_data["end_time"],
                        "pool_length": swim_data.get("pool_length", "Unknown")
                    }
                    for swim_data in pool["swim_data"]
                    if (
                        (start_date_parsed is None or datetime.strptime(swim_data["end_time"], "%Y-%m-%dT%H:%M:%S") >= start_date_parsed) and
                        (end_date_parsed is None or datetime.strptime(swim_data["start_time"], "%Y-%m-%dT%H:%M:%S") <= end_date_parsed)
                    )
                ]
            }
            for pool in matched_pools
        ]

    # Return the full pool objects
    return matched_pools

# Generate OpenAPI schema and save it to openapi.yaml
@app.on_event("startup")
async def startup_event():
    # Generate OpenAPI schema
    openapi_schema = get_openapi(
        title="Toronto Swim Lane Tracker API",
        version="1.0.0",
        description="API for retrieving pool swim lane schedules.",
        routes=app.routes,
    )
    with open("openapi.yaml", "w") as file:
        yaml.dump(openapi_schema, file, default_flow_style=False)

    # Start background refresh task
    start_background_refresh()

@app.on_event("shutdown")
async def shutdown_event():
    global refresh_task_running
    refresh_task_running = False
    print("Background refresh task stopped")

# Serve the OpenAPI schema as a YAML file
@app.get("/openapi.yaml", response_class=Response, description="Get the OpenAPI schema in YAML format")
async def serve_openapi_yaml():
    """
    Endpoint to serve the OpenAPI schema as a YAML file.
    """
    with open("openapi.yaml", "r") as file:
        openapi_yaml = file.read()
    return Response(content=openapi_yaml, media_type="text/yaml")