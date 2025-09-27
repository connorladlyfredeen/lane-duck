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
 
 ### Run in the background
 `nohup uvicorn get_pools:app --host 127.0.0.1 --port 3000 > pools.log 2>&1 &`

## Deployment

### Automated Deployment
Use the deployment script to automatically upload assets, restart nginx, and test endpoints:

```bash
./deploy.sh
```

The script will:
1. Upload all project files to the GCloud server
2. Run `nginx-restart` on the server
3. Test both frontend and API endpoints for 200 responses
4. Restart the backend service if the API is not responding

### Manual Deployment
If you prefer manual deployment:

```bash
# Upload files
gcloud compute scp *.py *.html *.md connorladly-1:~/lane-duck/ --zone "us-west1-b" --project "connorladlydotcom"

# Restart nginx
gcloud compute ssh connorladly-1 --zone "us-west1-b" --project "connorladlydotcom" --command "nginx-restart"

# Start backend service
gcloud compute ssh connorladly-1 --zone "us-west1-b" --project "connorladlydotcom" --command "cd lane-duck && nohup uvicorn get_pools:app --host 127.0.0.1 --port 3000 > pools.log 2>&1 &"
```
