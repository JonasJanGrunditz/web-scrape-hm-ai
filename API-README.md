# H&M Scraper API

This is a Cloud Run API service for scraping H&M product URLs with configurable page ranges.

## Files

- `main_api.py` - Flask API application for Cloud Run
- `Dockerfile.api` - Docker configuration for the API service
- `cloudbuild-api.yaml` - Cloud Build configuration for API deployment
- `deploy-api.sh` - Deployment script

## API Endpoints

### POST /scrape
Scrapes H&M products for the specified page range.

**Request Body:**
```json
{
  "start_page": 1,
  "end_page": 5
}
```

**Response:**
```json
{
  "success": true,
  "urls_found": 150,
  "message": "Successfully scraped pages 1-5"
}
```

### GET /health
Health check endpoint.

**Response:**
```json
{
  "status": "healthy"
}
```

### GET /
Root endpoint with API documentation.

## Deployment

### Using the deployment script:
```bash
./deploy-api.sh YOUR_PROJECT_ID
```

### Manual deployment:
```bash
gcloud builds submit --config=cloudbuild-api.yaml
```

## Testing the API

Once deployed, you can test the API:

```bash
# Get the service URL
SERVICE_URL=$(gcloud run services describe hm-scraper-api --region=europe-west1 --format="value(status.url)")

# Test health endpoint
curl $SERVICE_URL/health

# Test scraping endpoint
curl -X POST $SERVICE_URL/scrape \
  -H 'Content-Type: application/json' \
  -d '{"start_page": 1, "end_page": 3}'
```

## Local Development

To run the API locally:

```bash
cd scraper
pip install -r requirements.txt
python main_api.py
```

The API will be available at `http://localhost:8080`.

## Configuration

The API uses the same GCP bucket configuration as the original scraper. Make sure your Cloud Run service has the necessary permissions to write to Google Cloud Storage.

## Differences from Original

- **API Interface**: Instead of command-line execution, the scraper is triggered via HTTP API
- **Dynamic Page Range**: `start_page` and `end_page` are provided as API parameters instead of environment variables
- **Production Ready**: Uses gunicorn for production deployment
- **Health Checks**: Includes health check endpoint for Cloud Run
- **Error Handling**: Better error handling and response formatting
