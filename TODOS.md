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
- We already sort by closest so this shouldn't be hard

**Data available**: Pool objects already contain `x` and `y` coordinates
---

## Data Accuracy Issues

### 5. Fix week numbering inconsistency in Toronto API
**Priority**: High
**Effort**: Medium

Currently we assume week1.json = current week and week2.json = next week, but Toronto's API doesn't always follow this pattern. Some pools may have different week numbering or date ranges.

**Issues**:
- Week1 might not always be the current calendar week
- Some pools may have different scheduling periods
- Date ranges in the API response should be validated against actual calendar dates

**Solution approaches**:
- Parse the actual date ranges from the API response data
- Validate dates against current calendar week before processing
- Add date range detection to determine which week file contains current/future dates
- Consider fetching multiple week files and filtering by actual dates
- Add logging to track when week numbering doesn't match expectations

**Current logic**: `scrape.py:181` assumes `[(1, 0), (2, 1)]` where week1=current, week2=next

---

## Technical Debt

### 6. Update FastAPI event handlers
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