# H&M Product Processor API

This is a Cloud Run API service for processing H&M product URLs and extracting detailed product information. It reads URLs from the GCS bucket (populated by the scraper API) and processes them with configurable index ranges.

## Overview

The Product Processor API works in conjunction with the H&M Scraper API:

1. **Scraper API** (`main_api.py`) → Collects product URLs → Saves to GCS
2. **Product Processor API** (`product_api.py`) → Reads URLs from GCS → Processes product details → Saves to GCS

## Files

- `product_api.py` - Flask API application for product processing
- `Dockerfile.product-api` - Docker configuration for the product API service
- `cloudbuild-product-api.yaml` - Cloud Build configuration for deployment
- `deploy-product-api.sh` - Deployment script
- `concurrent_product_example.py` - Example script for concurrent processing

## API Endpoints

### POST /process
Processes H&M product URLs for the specified index range.

**Request Body:**
```json
{
  "start_index": 0,
  "end_index": 9,
  "session_id": "batch_1",
  "batch_size": 5
}
```

**Response:**
```json
{
  "success": true,
  "products_processed": 8,
  "products_failed": 2,
  "total_urls_in_range": 10,
  "processing_time_seconds": 45.2,
  "message": "Successfully processed indices 0-9",
  "session_id": "batch_1"
}
```

### GET /info
Get information about available URLs to process.

**Response:**
```json
{
  "total_urls_available": 1523,
  "index_range": "0-1522",
  "sample_urls": ["url1", "url2", "url3", "url4", "url5"]
}
```

### GET /status
Check the status of active processing sessions.

**Response:**
```json
{
  "active_sessions": 2,
  "status": "running"
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

## Key Features

- ✅ **Index-based processing**: Process specific ranges of URLs by index
- ✅ **Thread-safe operations**: Multiple requests can run simultaneously
- ✅ **Automatic data appending**: New processed data is added without overwriting
- ✅ **Image mapping collection**: Automatically collects and saves product images
- ✅ **Session tracking**: Optional session IDs for monitoring
- ✅ **Batch processing**: Configurable batch sizes for optimal performance
- ✅ **Comprehensive error handling**: Robust retry logic and error reporting

## Data Processing

The API processes each product URL to extract:

- **Article ID**: Unique product identifier
- **Sizes & Availability**: Available sizes and stock information
- **Description & Fit**: Product description and fit details
- **Material**: Fabric composition and material information
- **Category**: Product category (e.g., "klänningar")
- **Color**: Product color
- **Attributes**: Product attributes (e.g., "kortärmad", "v-ringad")
- **Pricing**: Discounted price, original price, discount percentage
- **Gender**: Target demographic (DAM, HERR, BARN, etc.)
- **Images**: Product image URLs (saved separately)

## Storage Locations

All processed data is automatically saved to GCS:

- **Processed Products**: `web-scrape-ai/garments-info/products-info_test.txt`
- **Image Mappings**: `web-scrape-ai/image_mapping1.json`
- **Source URLs**: `web-scrape-ai/garments/urls.txt` (read from, populated by scraper API)

## Deployment

### Using the deployment script:
```bash
./deploy-product-api.sh YOUR_PROJECT_ID
```

### Manual deployment:
```bash
gcloud builds submit --config=cloudbuild-product-api.yaml
```

## Testing the API

Once deployed, you can test the API:

```bash
# Get the service URL
SERVICE_URL=$(gcloud run services describe hm-product-processor-api --region=europe-west1 --format="value(status.url)")

# Check available URLs
curl $SERVICE_URL/info

# Test processing endpoint
curl -X POST $SERVICE_URL/process \
  -H 'Content-Type: application/json' \
  -d '{"start_index": 0, "end_index": 9, "session_id": "test_batch"}'

# Check status
curl $SERVICE_URL/status
```

## Local Development

To run the API locally:

```bash
cd scraper
pip install -r requirements.txt
python product_api.py
```

The API will be available at `http://localhost:8081`.

## Concurrent Processing Example

Use the provided example script to process multiple URL ranges concurrently:

```bash
python concurrent_product_example.py
```

This script will:
1. Check available URLs
2. Create multiple concurrent processing tasks
3. Monitor progress and provide summary statistics

## Usage Workflow

1. **First**: Run the Scraper API to collect URLs
   ```bash
   curl -X POST [SCRAPER_URL]/scrape -d '{"start_page": 1, "end_page": 10}'
   ```

2. **Then**: Check available URLs for processing
   ```bash
   curl [PROCESSOR_URL]/info
   ```

3. **Finally**: Process the URLs in batches
   ```bash
   curl -X POST [PROCESSOR_URL]/process -d '{"start_index": 0, "end_index": 50}'
   ```

## Configuration

### Environment Variables
- `OPENAI_API_KEY`: Required for product data extraction
- `PORT`: API port (default: 8081)

### Request Limits
- Maximum 100 URLs per request
- Batch size: 1-20 (default: 5)
- Request timeout: 30 minutes

## Error Handling

The API includes comprehensive error handling:
- Retry logic for network failures (3 attempts with exponential backoff)
- Validation of index ranges
- Thread-safe operations for concurrent requests
- Detailed error messages and logging

## Monitoring

- **Active Sessions**: Track concurrent processing sessions
- **Processing Statistics**: Success/failure rates, timing information
- **Resource Usage**: Memory and CPU optimized for Cloud Run

## Integration with Scraper API

This Product Processor API is designed to work seamlessly with the H&M Scraper API:

- **Input**: Reads URLs from GCS bucket populated by scraper
- **Processing**: Extracts detailed product information
- **Output**: Saves processed data to separate GCS location
- **Independence**: Can run independently once URLs are available
