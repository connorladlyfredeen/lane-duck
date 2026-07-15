#!/bin/bash

# LaneDuck Deployment Script
# Automates deployment to GCloud server

set -e  # Exit on any error

# Configuration
SERVER="connorladly-1"
ZONE="us-west1-b"
PROJECT="connorladlydotcom"
REMOTE_DIR="~/lane-duck"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🦆 LaneDuck Deployment Script${NC}"
echo "================================"

# Check if we're on main branch
CURRENT_BRANCH=$(git branch --show-current)
if [ "$CURRENT_BRANCH" != "main" ]; then
    echo -e "${RED}❌ Error: Deployments can only be run from the main branch${NC}"
    echo "Current branch: $CURRENT_BRANCH"
    echo "Please switch to main branch first: git checkout main"
    exit 1
fi

echo -e "${GREEN}✅ On main branch - proceeding with deployment${NC}"

# Step 1: Upload assets to remote server
echo -e "${YELLOW}📦 Step 1: Uploading assets to server...${NC}"

# Upload Python files
echo "Uploading Python backend files..."
gcloud compute scp get_pools.py scrape.py prerender.py obs.py pool_lengths.json "$SERVER:$REMOTE_DIR/" \
    --zone "$ZONE" --project "$PROJECT"

# Upload frontend
echo "Uploading frontend files..."
gcloud compute scp index.html "$SERVER:$REMOTE_DIR/" \
    --zone "$ZONE" --project "$PROJECT"

# Upload documentation
echo "Uploading documentation..."
gcloud compute scp README.md CLAUDE.md TODOS.md "$SERVER:$REMOTE_DIR/" \
    --zone "$ZONE" --project "$PROJECT"

# Upload configuration files
echo "Uploading configuration files..."
gcloud compute scp .gitignore openapi.yaml sitemap.xml og-image.png requirements.txt .env.example "$SERVER:$REMOTE_DIR/" \
    --zone "$ZONE" --project "$PROJECT"

echo -e "${GREEN}✅ Assets uploaded successfully${NC}"

# Step 1.5: Restart PM2 service
echo -e "${YELLOW}🔄 Restarting PM2 service...${NC}"
gcloud compute ssh "$SERVER" --zone "$ZONE" --project "$PROJECT" \
    --command "pm2 reload lane-duck"
echo -e "${GREEN}✅ PM2 service restarted${NC}"

# Step 2: Test endpoints
echo -e "${YELLOW}🧪 Step 2: Testing endpoints...${NC}"

# Test frontend
echo "Testing frontend at www.connorladly.com/lane-duck..."
FRONTEND_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "https://www.connorladly.com/lane-duck" || echo "000")

if [ "$FRONTEND_STATUS" = "200" ]; then
    echo -e "${GREEN}✅ Frontend endpoint responding (200)${NC}"
else
    echo -e "${RED}❌ Frontend endpoint failed (HTTP $FRONTEND_STATUS)${NC}"
    exit 1
fi

# Test API
echo "Testing API at www.connorladly.com/api/toronto-pools/pools..."
API_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "https://www.connorladly.com/api/toronto-pools/pools" || echo "000")

if [ "$API_STATUS" = "200" ]; then
    echo -e "${GREEN}✅ API endpoint responding (200)${NC}"
else
    echo -e "${RED}❌ API endpoint failed (HTTP $API_STATUS)${NC}"
    echo "Checking if backend service is running..."

    # Check if backend is running and restart if needed
    gcloud compute ssh "$SERVER" --zone "$ZONE" --project "$PROJECT" \
        --command "cd $REMOTE_DIR && pkill -f uvicorn || true && nohup uvicorn get_pools:app --host 127.0.0.1 --port 3000 > pools.log 2>&1 &"

    echo "Backend service restarted. Waiting 5 seconds..."
    sleep 5

    # Test API again
    API_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "https://www.connorladly.com/api/toronto-pools/pools" || echo "000")

    if [ "$API_STATUS" = "200" ]; then
        echo -e "${GREEN}✅ API endpoint now responding (200)${NC}"
    else
        echo -e "${RED}❌ API endpoint still failing (HTTP $API_STATUS)${NC}"
        exit 1
    fi
fi

# Success message
echo ""
echo -e "${GREEN}🎉 Deployment completed successfully!${NC}"
echo ""
echo "Frontend: https://www.connorladly.com/lane-duck"
echo "API: https://www.connorladly.com/api/toronto-pools/pools"
echo ""
echo -e "${BLUE}📋 Next steps:${NC}"
echo "• Visit the frontend to test the application"
echo "• Check server logs if needed: gcloud compute ssh $SERVER --zone $ZONE --project $PROJECT --command 'tail -f ~/lane-duck/pools.log'"
echo "• Monitor nginx logs: gcloud compute ssh $SERVER --zone $ZONE --project $PROJECT --command 'sudo tail -f /var/log/nginx/error.log'"