import argparse
import requests
import json
import random
import re
import os
import time
from tqdm.cli import tqdm
import logging
import os

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.WARNING)

## Create the tmp directory if it doesn't exist
if not os.path.exists('tmp'):
    os.makedirs('tmp')

CACHE_FILE = "tmp/good_list_cache.json"

def fetch_locations():
    url = 'https://services3.arcgis.com/b9WvedVPoizGfvfD/arcgis/rest/services/V_Swim_Locations_2022/FeatureServer/0/query?f=json&where=Show_On_Map%20=%20%27Yes%27&returnGeometry=true&spatialRel=esriSpatialRelIntersects&outFields=*&outSR=102100&resultOffset=0&resultRecordCount=5000'
    response = requests.get(url)
    response.raise_for_status()
    return response.json()['features']

def fetch_locations_with_retries(max_retries=3, backoff_factor=2):
    retries = 0
    delay = 1  # Initial delay in seconds

    while retries < max_retries:
        try:
            return fetch_locations()  # Attempt to fetch locations
        except Exception as e:
            retries += 1
            logger.info(f"Attempt {retries} failed: {e}")
            if retries < max_retries:
                logger.info(f"Retrying in {delay} seconds...")
                time.sleep(delay)
                delay *= backoff_factor  # Exponential backoff
            else:
                logger.warning("All retries failed.")
                raise

def process_locations(locations):
    # Return all locations - we'll filter based on actual schedule data later
    location_list = []
    for location in locations:
        location_list.append(location['attributes'])

    logger.info(f"Total locations to process: {len(location_list)}")
    return location_list

def load_good_list_from_cache():
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, 'r') as file:
            return json.load(file)
    return None

def save_good_list_to_cache(good_list):
    with open(CACHE_FILE, 'w') as file:
        json.dump(good_list, file)

def fetch_with_retries(url, max_retries=3, backoff_factor=2):
    retries = 0
    delay = 1  # Initial delay in seconds

    while retries < max_retries:
        try:
            response = requests.get(url)
            if response.status_code == 404:
                logger.info(f"404 returned for URL {url}.")
                return response
            response.raise_for_status()
            return response
        except Exception as e:
            retries += 1
            logger.info(f"Attempt {retries} failed for URL {url}: {e}")
            if retries < max_retries:
                logger.info(f"Retrying in {delay} seconds...")
                time.sleep(delay)
                delay *= backoff_factor
            else:
                logger.warning(f"All retries failed for URL {url}.")
                raise

from datetime import datetime, timedelta

def convert_to_new_format(obj, week_offset=0, swim_type_title=None):
    """
    Converts the input dictionary into the specified format.

    Args:
        obj (dict): Input dictionary with fields like id, day, title, status, etc.
        week_offset (int): 0 for current week, 1 for next week
        swim_type_title (str): The swim type title (e.g., "Lane Swim: Long Course (50m)")

    Returns:
        dict: Reformatted dictionary with datetime objects and structured fields.
    """
    # Map days of the week to integers (Monday=0, Sunday=6)
    days_of_week = {
        "monday": 0,
        "tuesday": 1,
        "wednesday": 2,
        "thursday": 3,
        "friday": 4,
        "saturday": 5,
        "sunday": 6
    }

    # Get the current date and calculate the start of the week (Monday)
    today = datetime.now()
    start_of_week = today - timedelta(days=today.weekday())  # Monday of the current week

    # Add week offset for next week data
    start_of_week = start_of_week + timedelta(weeks=week_offset)

    # Determine the date for the given day
    day_name = obj.get("day", "").lower()
    day_offset = days_of_week.get(day_name, 0)
    day_date = start_of_week + timedelta(days=day_offset)

    # Extract start and end times from the "title" field
    time_range = obj.get("title", "").split(" - ")
    start_time_str = time_range[0] if len(time_range) > 0 else None
    end_time_str = time_range[1] if len(time_range) > 1 else None

    # Combine the date and times into datetime objects
    start_datetime = datetime.strptime(f"{day_date.date()} {start_time_str}", "%Y-%m-%d %I:%M %p") if start_time_str else None
    end_datetime = datetime.strptime(f"{day_date.date()} {end_time_str}", "%Y-%m-%d %I:%M %p") if end_time_str else None

    # Extract pool length from swim type title
    pool_length = None
    if swim_type_title:
        if "Long Course (50m)" in swim_type_title:
            pool_length = "50m"
        elif "Short Course (25m)" in swim_type_title:
            pool_length = "25m"
        else:
            pool_length = "Unknown"  # Default for regular "Lane Swim"

    # Return the reformatted dictionary
    return {
        "status": obj.get("status", "").lower(),
        "start_time": start_datetime.strftime("%Y-%m-%dT%H:%M:%S") if start_datetime else None,
        "end_time": end_datetime.strftime("%Y-%m-%dT%H:%M:%S") if end_datetime else None,
        "id": int(obj.get("id", 0)),
        "pool_length": pool_length
    }


def process_swim_data(raw_swim_data: dict, week_offset=0) -> dict:
    swim_data_objs = [program["days"] for program in raw_swim_data['programs'] if program['program'] == 'Swim - Drop-In']
    if len(swim_data_objs) == 0:
        return []
    elif len(swim_data_objs) > 1:
        logger.warning(f"Warning: Found {len(swim_data_objs)} swim data objects. Using the first one.")
    swim_data_objs = swim_data_objs[0]
    flattened_swim_sessions = []
    for swim_data_obj in swim_data_objs:
        if swim_data_obj['title'] in {'Lane Swim', 'Lane Swim: Long Course (50m)', 'Lane Swim: Short Course (25m)'} and swim_data_obj['status'] == 'active':
            filtered_sessions = [session for session in swim_data_obj['times'] if session['status'] == 'active']
            swim_type_title = swim_data_obj['title']
            flattened_swim_sessions.extend([convert_to_new_format(session, week_offset, swim_type_title) for session in filtered_sessions])
    logger.info(f"Found {len(flattened_swim_sessions)} active lane swim sessions for week offset {week_offset}.")
    return flattened_swim_sessions

    

def process_locations_with_data(locations, good_list_file):
    updated_good_list = []

    for location in tqdm(locations):
        location_id = location['locationid']
        logger.info(f"Processing location: {location_id}")

        all_swim_data = []

        # Fetch both current week and next week (reverting to simple assumption for now)
        for week_num, week_offset in [(1, 0), (2, 1)]:
            url = f"https://www.toronto.ca/data/parks/live/locations/{location_id}/swim/week{week_num}.json"

            try:
                response = fetch_with_retries(url)
                # Decode the response explicitly as UTF-16
                raw_response = response.content.decode('utf-16', errors='replace')

                # Remove invalid characters at the start of the response
                cleaned_response = re.sub(r'^[^\{]*', '', raw_response)

                if cleaned_response == "":
                    logger.info(f"Empty response for location {location_id} week {week_num}.")
                    continue

                # Parse the cleaned JSON
                data = json.loads(cleaned_response)

                # Process the swim data for this week
                week_swim_data = process_swim_data(data, week_offset)
                all_swim_data.extend(week_swim_data)

            except json.JSONDecodeError as e:
                logger.warning(f"JSON decoding failed for location {location_id} week {week_num}: {e}")
            except Exception as e:
                logger.error(f"Failed to fetch data for location {location_id} week {week_num}: {e}")

            # Wait between requests
            time.sleep(0.25 + random.uniform(0, 0.25))

        # Only include locations that have actual lane swim data
        if all_swim_data:
            location['swim_data'] = all_swim_data
            updated_good_list.append(location)
        else:
            logger.info(f"No lane swim data found for location {location_id}, skipping.")

        # Wait between locations
        time.sleep(0.25 + random.uniform(0, 0.25))

    # Save the updated good list to the file
    with open(good_list_file, 'w', encoding='utf-8') as f:
        json.dump(updated_good_list, f, ensure_ascii=False, indent=4)
    logger.info(f"Updated good list saved to {good_list_file}")

def main():
    logger.info("Fetching fresh data from Toronto API...")

    # Always fetch fresh location data
    locations = fetch_locations_with_retries()
    location_list = process_locations(locations)

    # Process all locations with detailed data and filter by actual schedule content
    process_locations_with_data(location_list, CACHE_FILE)

if __name__ == "__main__":
    main()