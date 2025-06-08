#!/bin/bash

# Deployment script for H&M Product Processor API to Cloud Run
# Usage: ./deploy-product-api.sh [PROJECT_ID]

set -e

# Check if PROJECT_ID is provided
if [ -z "$1" ]; then
    echo "Usage: $0 <PROJECT_ID>"
    echo "Example: $0 my-gcp-project"
    exit 1
fi

PROJECT_ID=$1
REGION="europe-west1"
SERVICE_NAME="hm-product-processor-api"

echo "Deploying H&M Product Processor API to Cloud Run..."
echo "Project ID: $PROJECT_ID"
echo "Region: $REGION"
echo "Service Name: $SERVICE_NAME"

# Submit the build to Cloud Build
echo "Starting Cloud Build..."
gcloud builds submit \
    --project=$PROJECT_ID \
    --config=cloudbuild-product-api.yaml

echo "Deployment completed!"
echo "Service URL:"
gcloud run services describe $SERVICE_NAME \
    --project=$PROJECT_ID \
    --region=$REGION \
    --format="value(status.url)"

echo ""
echo "Test the API with:"
echo "# Get info about available URLs:"
echo "curl [SERVICE_URL]/info"
echo ""
echo "# Process URLs 0-9:"
echo "curl -X POST [SERVICE_URL]/process -H 'Content-Type: application/json' -d '{\"start_index\": 0, \"end_index\": 9}'"
