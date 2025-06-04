#!/bin/bash

# Deployment script for H&M Scraper API to Cloud Run
# Usage: ./deploy-api.sh [PROJECT_ID]

set -e

# Check if PROJECT_ID is provided
if [ -z "$1" ]; then
    echo "Usage: $0 <PROJECT_ID>"
    echo "Example: $0 my-gcp-project"
    exit 1
fi

PROJECT_ID=$1
REGION="europe-west1"
SERVICE_NAME="hm-scraper-api"

echo "Deploying H&M Scraper API to Cloud Run..."
echo "Project ID: $PROJECT_ID"
echo "Region: $REGION"
echo "Service Name: $SERVICE_NAME"

# Submit the build to Cloud Build
echo "Starting Cloud Build..."
gcloud builds submit \
    --project=$PROJECT_ID \
    --config=cloudbuild-api-fixed.yaml

echo "Deployment completed!"
echo "Service URL:"
gcloud run services describe $SERVICE_NAME \
    --project=$PROJECT_ID \
    --region=$REGION \
    --format="value(status.url)"

echo ""
echo "Test the API with:"
echo "curl -X POST [SERVICE_URL]/scrape -H 'Content-Type: application/json' -d '{\"start_page\": 1, \"end_page\": 3}'"
