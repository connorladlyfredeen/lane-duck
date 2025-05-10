# LaneDuck 🦆

Scraper and endpoint to get the list of lane swim times at toronto pools
so you can "duck" into a lane whenever is most convenient for you

## Running the service

To scrape the most up to date lane info run `python scrape.py`

To run the service run `uvicorn get_pools:app --host 127.0.0.1 --port 3000`

You can see the api schema by hitting  `/openapi.yaml`

## Limitations

- Does not factor in women's only or age 65+ lane times
- For some reason the city of Toronto duplicates some pools
- Some indoor pools are labelled as outdoor (i.e. Giovani Caboto on Saint Claire)
