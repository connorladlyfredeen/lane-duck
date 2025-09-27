# LaneDuck 🦆

Scraper and endpoint to get the list of lane swim times at toronto pools
so you can "duck" into a lane whenever is most convenient for you

## Python Implementation

### Running the service

To scrape the most up to date lane info run `python scrape.py`

To run the service run `uvicorn get_pools:app --host 127.0.0.1 --port 3000`

The service automatically refreshes pool data once daily by running the scraper in the background.

You can see the api schema by hitting  `/openapi.yaml`

### Limitations

- Does not factor in women's only or age 65+ lane times
- Some indoor pools are labelled as outdoor if they have both
 (i.e. Giovani Caboto on Saint Claire)

