# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

LaneDuck is a Python FastAPI application that tracks Toronto public swimming pool lane swim schedules. It consists of two main components:

1. **Data scraper** (`scrape.py`) - Fetches pool location data from Toronto's ArcGIS API and individual pool schedules
2. **FastAPI service** (`get_pools.py`) - Serves pool data via REST API with filtering capabilities

## Architecture

### Data Flow
- `scrape.py` fetches all 373 pool locations from Toronto's public API
- For each location, it fetches both current week and next week schedule data
- Only pools with actual lane swim sessions are included in the final data
- Data is saved to `tmp/good_list_cache.json` for the API to consume
- `get_pools.py` serves this data via REST endpoints
- The API automatically refreshes data once daily by running the scraper in the background

### Key Components
- **Pool location fetching**: Uses ArcGIS REST API to get all Toronto pool locations
- **Schedule scraping**: Fetches individual pool schedules from toronto.ca endpoints
- **Data processing**: Converts raw schedule data into standardized datetime format
- **API service**: FastAPI app with `/pools` endpoint supporting date filtering and response simplification

## Development Commands

### Running the scraper
```bash
python scrape.py                    # Always fetches fresh data from all 373 Toronto pool locations
```

### Running the API service
```bash
uvicorn get_pools:app --host 127.0.0.1 --port 3000
```

### API Usage
- Base endpoint: `/pools`
- Query parameters:
  - `start_date`: Filter by start datetime (YYYY-MM-DDTHH:MM:SS)
  - `end_date`: Filter by end datetime (YYYY-MM-DDTHH:MM:SS)
  - `simple`: Return simplified response with just pool names and times
- OpenAPI schema available at `/openapi.yaml`

## Dependencies

The project uses Python 3 with these key dependencies (imported in code):
- `fastapi` - Web framework
- `uvicorn` - ASGI server
- `requests` - HTTP client for API calls
- `tqdm` - Progress bars for scraping
- `pyyaml` - YAML handling for OpenAPI schema

## Data Structure

Pool data is stored as objects with:
- Basic pool info (name, location, address, amenities)
- `swim_data` array containing lane swim sessions with:
  - `status`: "active" for available sessions
  - `start_time`/`end_time`: ISO datetime strings
  - `id`: Session identifier
  - `pool_length`: "25m", "50m", or "Unknown"

## Known Limitations

- Does not account for women's only or age 65+ lane times
- Some indoor pools may be incorrectly labeled as outdoor if facility has both