import asyncio
import os
import threading
import time
from flask import Flask, request, jsonify
from dotenv import load_dotenv
from crawl4ai import AsyncWebCrawler
from crawl4ai.async_configs import BrowserConfig, CrawlerRunConfig
from openai import OpenAI
from llm.openai import extract_sections_from_markdown_openai
from gcp.gcp_bucket import download_urls_from_gcs, upload_processed_garments_to_gcs, upload_image_mapping_to_gcs
from transformation.hardcoded_re import extract_product_id, extract_urls_from_markdown, between_size_and_material, extract_price_info, count_most_frequent_word

# Load environment variables
load_dotenv()

app = Flask(__name__)

# Thread-safe counter for tracking active processing sessions
_active_sessions = 0
_sessions_lock = threading.Lock()

# Global image mapping to collect URLs from all sessions
_global_image_mapping = {}
_image_mapping_lock = threading.Lock()

async def crawl_url(url, browser_config, run_config, client, max_retries=3):
    """Crawl a single URL with retry logic for better reliability."""
    for attempt in range(max_retries):
        try:
            async with AsyncWebCrawler(config=browser_config) as crawler:
                result = await crawler.arun(url=url, config=run_config)
                
                if result.success:
                    print(f"Successfully crawled {url} on attempt {attempt + 1}")
                    extracted_content = between_size_and_material(result.markdown)
                    gender = count_most_frequent_word(result.markdown)
                
                    if extracted_content is None:
                        print(f"Warning: No content extracted from {url} - pattern not found")
                        return None
                    else:
                        article_id = extract_product_id(url)
                        url_image = extract_urls_from_markdown(result.markdown)
                        discounted_price, original_price, discount_percentage = extract_price_info(result.markdown)
                        
                        # Thread-safe image mapping update
                        if url_image and article_id:
                            with _image_mapping_lock:
                                _global_image_mapping[article_id] = url_image
                        
                        extracted_content_cleaned = extract_sections_from_markdown_openai(
                            extracted_content, article_id, discounted_price, 
                            original_price, discount_percentage, gender, client
                        )
                        return extracted_content_cleaned
                        
                else:
                    print(f"Attempt {attempt + 1} failed for {url}: {result.error_message}")
                    if attempt == max_retries - 1:
                        print(f"All attempts failed for {url}")
                        return None
                        
        except Exception as e:
            print(f"Attempt {attempt + 1} failed for {url}: {str(e)}")
            if attempt == max_retries - 1:
                print(f"All attempts failed for {url}")
                return None
            # Wait before retrying
            await asyncio.sleep(2 ** attempt)  # Exponential backoff: 1s, 2s, 4s
    
    return None

def create_batches(items, batch_size):
    """Split a list into batches of specified size."""
    for i in range(0, len(items), batch_size):
        yield items[i:i + batch_size]

async def process_batch(urls, browser_config, run_config, client, batch_num, session_prefix):
    """Process a single batch of URLs."""
    print(f"{session_prefix} Processing batch {batch_num} with {len(urls)} URLs...")
    
    tasks = [
        crawl_url(url, browser_config, run_config, client)
        for url in urls
    ]
    
    batch_results = await asyncio.gather(*tasks)
    
    print(f"{session_prefix} Completed batch {batch_num}")
    
    return batch_results

async def process_hm_products(start_index, end_index, session_id=None, batch_size=5):
    """Main processing function that processes URLs from GCS with specified index range."""
    global _active_sessions
    
    with _sessions_lock:
        _active_sessions += 1
        current_session = _active_sessions
    
    session_prefix = f"[Session {session_id or current_session}]"
    print(f"{session_prefix} Starting product processing for URLs {start_index}-{end_index}")
    
    try:
        start_time = time.perf_counter()
        
        # Download URLs from GCS
        all_urls = download_urls_from_gcs()
        print(f"{session_prefix} Downloaded {len(all_urls)} total URLs from GCS")
        
        # Validate indices
        if start_index < 0 or end_index >= len(all_urls) or start_index > end_index:
            return {
                "success": False,
                "products_processed": 0,
                "message": f"Invalid index range. Available URLs: 0-{len(all_urls)-1}",
                "session_id": session_id or current_session
            }
        
        # Get the subset of URLs to process
        urls_to_process = all_urls[start_index:end_index + 1]
        print(f"{session_prefix} Processing {len(urls_to_process)} URLs (indices {start_index}-{end_index})")
        
        # Initialize OpenAI client
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
        # Setup crawler configs
        browser_config = BrowserConfig()
        run_config = CrawlerRunConfig()
        
        all_content = []
        
        # Process URLs in batches
        for batch_num, batch_urls in enumerate(create_batches(urls_to_process, batch_size), 1):
            batch_results = await process_batch(batch_urls, browser_config, run_config, client, batch_num, session_prefix)
            all_content.extend(batch_results)
            
            # Optional: Add a small delay between batches to be gentle on the server
            if batch_num < len(urls_to_process) // batch_size + (1 if len(urls_to_process) % batch_size else 0):
                print(f"{session_prefix} Waiting 2 seconds before next batch...")
                await asyncio.sleep(2)

        # Filter out None results and track failures
        valid_content = [content for content in all_content if content is not None]
        failed_count = len(all_content) - len(valid_content)
        
        print(f"{session_prefix} Successfully processed {len(valid_content)} out of {len(urls_to_process)} URLs")
        print(f"{session_prefix} Failed to extract content from {failed_count} URLs")

        # Upload processed garments to GCS (thread-safe)
        if valid_content:
            upload_processed_garments_to_gcs(valid_content)
            print(f"{session_prefix} Completed: uploaded {len(valid_content)} processed garments to GCS")
        
        # Upload image mapping if we have any
        with _image_mapping_lock:
            if _global_image_mapping:
                upload_image_mapping_to_gcs(_global_image_mapping)
                print(f"{session_prefix} Uploaded image mapping with {len(_global_image_mapping)} entries")

        elapsed = time.perf_counter() - start_time
        print(f"{session_prefix} Execution time: {elapsed:.2f} seconds")
        
        return {
            "success": True,
            "products_processed": len(valid_content),
            "products_failed": failed_count,
            "total_urls_in_range": len(urls_to_process),
            "processing_time_seconds": round(elapsed, 2),
            "message": f"Successfully processed indices {start_index}-{end_index}",
            "session_id": session_id or current_session
        }
    
    except Exception as e:
        print(f"{session_prefix} Error during processing: {str(e)}")
        return {
            "success": False,
            "products_processed": 0,
            "message": f"Processing failed: {str(e)}",
            "session_id": session_id or current_session
        }
    
    finally:
        with _sessions_lock:
            _active_sessions -= 1

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint for Cloud Run."""
    return jsonify({"status": "healthy"})

@app.route('/status', methods=['GET'])
def status_check():
    """Check the status of active processing sessions."""
    with _sessions_lock:
        return jsonify({
            "active_sessions": _active_sessions,
            "status": "running" if _active_sessions > 0 else "idle"
        })

@app.route('/info', methods=['GET'])
def info_check():
    """Get information about available URLs to process."""
    try:
        all_urls = download_urls_from_gcs()
        return jsonify({
            "total_urls_available": len(all_urls),
            "index_range": f"0-{len(all_urls)-1}" if all_urls else "No URLs available",
            "sample_urls": all_urls[:5] if all_urls else []
        })
    except Exception as e:
        return jsonify({"error": f"Failed to get URL info: {str(e)}"}), 500

@app.route('/process', methods=['POST'])
def process_endpoint():
    """API endpoint to trigger product processing with custom index ranges."""
    try:
        # Get JSON data from request
        data = request.get_json()
        
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400
        
        # Extract start_index and end_index from request
        start_index = data.get('start_index')
        end_index = data.get('end_index')
        session_id = data.get('session_id')  # Optional session identifier
        batch_size = data.get('batch_size', 5)  # Optional batch size, default 5
        
        if start_index is None or end_index is None:
            return jsonify({"error": "start_index and end_index are required"}), 400
        
        # Validate indices
        try:
            start_index = int(start_index)
            end_index = int(end_index)
            batch_size = int(batch_size)
        except ValueError:
            return jsonify({"error": "start_index, end_index, and batch_size must be integers"}), 400
        
        if start_index < 0 or end_index < start_index:
            return jsonify({"error": "Invalid index range. start_index must be >= 0 and end_index must be >= start_index"}), 400
        
        # Limit the range to prevent excessive load
        max_urls_per_request = 100
        if end_index - start_index + 1 > max_urls_per_request:
            return jsonify({"error": f"Index range too large. Maximum {max_urls_per_request} URLs per request"}), 400
        
        if batch_size < 1 or batch_size > 20:
            return jsonify({"error": "batch_size must be between 1 and 20"}), 400
        
        # Run the processing function
        result = asyncio.run(process_hm_products(start_index, end_index, session_id, batch_size))
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({"error": f"Internal server error: {str(e)}"}), 500

@app.route('/', methods=['GET'])
def root():
    """Root endpoint with usage instructions."""
    return jsonify({
        "message": "H&M Product Processor API - Supports Concurrent Processing",
        "endpoints": {
            "POST /process": "Process H&M product URLs with start_index and end_index parameters",
            "GET /health": "Health check endpoint",
            "GET /status": "Check active processing sessions",
            "GET /info": "Get information about available URLs to process"
        },
        "example_requests": [
            {
                "url": "/process",
                "method": "POST",
                "description": "Basic processing request",
                "body": {
                    "start_index": 0,
                    "end_index": 9
                }
            },
            {
                "url": "/process",
                "method": "POST", 
                "description": "Processing with session ID and custom batch size",
                "body": {
                    "start_index": 10,
                    "end_index": 19,
                    "session_id": "batch_1",
                    "batch_size": 3
                }
            }
        ],
        "notes": [
            "Multiple requests can run concurrently",
            "All processed data is saved to the same GCS location",
            "Image mappings are automatically collected and uploaded",
            "Maximum 100 URLs per request",
            "Use GET /info to see available URL range"
        ]
    })

if __name__ == "__main__":
    # For local development
    port = int(os.environ.get("PORT", 8081))  # Different port from scraper API
    app.run(host="0.0.0.0", port=port, debug=False)
