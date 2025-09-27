# Future TODOs for LaneDuck

## Performance Improvements

### 1. Cache the pool data in memory to reduce disk reads
**Priority**: Medium
**Effort**: Low

Currently the API reads from `tmp/good_list_cache.json` on every request. This could be optimized by:
- Loading data into memory on startup and daily refresh
- Using FastAPI's dependency injection or a global variable
- Implementing proper cache invalidation when background task updates data
- Consider using Redis or similar for production deployments

**Benefits**: Faster API response times, reduced I/O operations

---

## Data Enhancement

### 2. Sort out how we can determine pool length
**Priority**: High
**Effort**: Medium

Currently we extract pool length from swim program titles, but many pools show "Unknown". Potential solutions:
- Research if Toronto has a separate facilities API with pool specifications
- Crowdsource pool length data from users
- Cross-reference with other municipal databases
- Manual research and hardcode known pool lengths
- Add a configuration file for pool metadata overrides

**Current logic**: Extracts from titles like "Lane Swim: Long Course (50m)" vs "Lane Swim: Short Course (25m)"

---

## User Experience Features

### 3. Add location filtering to get pools nearby
**Priority**: High
**Effort**: Medium

Allow users to find pools within a certain distance of their location:
- Add geolocation support to the frontend
- Implement distance calculation using pool coordinates (x, y fields)
- Add query parameters for lat/lng and radius to API
- Consider adding neighborhood/district filtering as alternative
- Add map view showing pool locations

**Data available**: Pool objects already contain `x` and `y` coordinates

### 4. Add links from the pools to their website
**Priority**: Low
**Effort**: Low

Each pool object already contains a `website` field with Toronto's facility page URL:
- Add website links to the frontend pool cards
- Consider adding "Get Directions" links using coordinates
- Add facility phone numbers if available in the data
- Link to Toronto's pool-specific schedule pages

**Data available**: `website` field contains URLs like `https://www.toronto.ca/explore-enjoy/parks-recreation/places-spaces/parks-and-recreation-facilities/location/?id=272`

---

## Technical Debt

### 5. Update FastAPI event handlers
**Priority**: Low
**Effort**: Low

Current code uses deprecated `@app.on_event("startup")` and `@app.on_event("shutdown")`. Should migrate to the newer lifespan event handlers for better FastAPI compatibility.

### 6. Add proper error handling for missing cache file
**Priority**: Medium
**Effort**: Low

Currently the API will crash if `tmp/good_list_cache.json` doesn't exist. Should:
- Check if file exists before reading
- Return appropriate error messages
- Consider auto-running scraper if no cache exists
- Add health check endpoint

---

## Additional Features to Consider

- **Pool amenities display**: Show amenities like "Tot Pool", "Universal Change Room" from existing data
- **Mobile responsiveness**: Ensure the web UI works well on mobile devices
- **Favorites system**: Let users save preferred pools
- **Notifications**: Alert users when favorite pools have new sessions
- **Historical data**: Track and display pool closure patterns
- **API rate limiting**: Add rate limiting for production use
- **Docker deployment**: Containerize the application for easier deployment