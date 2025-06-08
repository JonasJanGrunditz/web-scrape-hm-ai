import asyncio
import os
import re
import threading
from flask import Flask, request, jsonify
from crawl4ai import AsyncWebCrawler
from crawl4ai.async_configs import BrowserConfig, CrawlerRunConfig
from gcp.gcp_bucket import upload_urls_to_gcs

app = Flask(__name__)

# Thread-safe counter for tracking active scraping sessions
_active_sessions = 0
_sessions_lock = threading.Lock()

def filter_garment_urls(links):
    """Extract garment product URLs from a list of internal links."""
    garment_urls = []
    for link in links:
        href = link.get('href', '')
        if re.search(r"productpage", href):
            garment_urls.append(href)
    return garment_urls

async def crawl_products(url, browser_config, run_config):
    """Perform the web crawl and return the result."""
    async with AsyncWebCrawler(config=browser_config) as crawler:
        return await crawler.arun(url=url, config=run_config)

async def scrape_hm_products(start_page, end_page, session_id=None):
    """Main scraping function that can be called with custom page ranges."""
    global _active_sessions
    
    with _sessions_lock:
        _active_sessions += 1
        current_session = _active_sessions
    
    session_prefix = f"[Session {session_id or current_session}]"
    print(f"{session_prefix} Starting scrape for pages {start_page}-{end_page}")
    
    try:
        # Configure the crawler
        browser_config = BrowserConfig(verbose=True)
        run_config = CrawlerRunConfig(
            word_count_threshold=10,
            excluded_tags=['form', 'header'],
            exclude_external_links=True,
            process_iframes=True,
            remove_overlay_elements=True,
        )
        
        all_urls = []
        
        for index in range(start_page, end_page + 1):
            try:
                # Run the crawl on the product page
                result = await crawl_products(
                    f"https://www2.hm.com/sv_se/dam/produkter/se-alla.html?page={index}",
                    browser_config,
                    run_config
                )

                if result.success:
                    # Filter garment URLs from the internal links
                    garment_urls = filter_garment_urls(result.links.get("internal", []))
                    all_urls.extend(garment_urls)
                    print(f"{session_prefix} Successfully scraped page {index}, found {len(garment_urls)} URLs")
                else:
                    print(f"{session_prefix} Crawl failed for page {index}: {result.error_message}")
            except Exception as e:
                print(f"{session_prefix} Error scraping page {index}: {str(e)}")
        
        # Upload to GCS (this is now thread-safe and appends to existing data)
        if all_urls:
            upload_urls_to_gcs(all_urls)
            print(f"{session_prefix} Completed: uploaded {len(all_urls)} URLs to GCS")
            return {
                "success": True, 
                "urls_found": len(all_urls), 
                "message": f"Successfully scraped pages {start_page}-{end_page}",
                "session_id": session_id or current_session
            }
        else:
            print(f"{session_prefix} Completed: no URLs found")
            return {
                "success": False, 
                "urls_found": 0, 
                "message": "No URLs found",
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
    """Check the status of active scraping sessions."""
    with _sessions_lock:
        return jsonify({
            "active_sessions": _active_sessions,
            "status": "running" if _active_sessions > 0 else "idle"
        })

@app.route('/scrape', methods=['POST'])
def scrape_endpoint():
    """API endpoint to trigger scraping with custom page ranges."""
    try:
        # Get JSON data from request
        data = request.get_json()
        
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400
        
        # Extract start_page and end_page from request
        start_page = data.get('start_page')
        end_page = data.get('end_page')
        session_id = data.get('session_id')  # Optional session identifier
        
        if start_page is None or end_page is None:
            return jsonify({"error": "start_page and end_page are required"}), 400
        
        # Validate page numbers
        try:
            start_page = int(start_page)
            end_page = int(end_page)
        except ValueError:
            return jsonify({"error": "start_page and end_page must be integers"}), 400
        
        if start_page < 1 or end_page < start_page:
            return jsonify({"error": "Invalid page range. start_page must be >= 1 and end_page must be >= start_page"}), 400
        
        # Limit the page range to prevent excessive load
        max_pages_per_request = 50
        if end_page - start_page + 1 > max_pages_per_request:
            return jsonify({"error": f"Page range too large. Maximum {max_pages_per_request} pages per request"}), 400
        
        # Run the scraping function
        result = asyncio.run(scrape_hm_products(start_page, end_page, session_id))
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({"error": f"Internal server error: {str(e)}"}), 500

@app.route('/', methods=['GET'])
def root():
    """Root endpoint with usage instructions."""
    return jsonify({
        "message": "H&M Scraper API - Supports Concurrent Scraping",
        "endpoints": {
            "POST /scrape": "Scrape H&M products with start_page and end_page parameters",
            "GET /health": "Health check endpoint",
            "GET /status": "Check active scraping sessions"
        },
        "example_requests": [
            {
                "url": "/scrape",
                "method": "POST",
                "description": "Basic scraping request",
                "body": {
                    "start_page": 1,
                    "end_page": 5
                }
            },
            {
                "url": "/scrape",
                "method": "POST", 
                "description": "Scraping with session ID for tracking",
                "body": {
                    "start_page": 10,
                    "end_page": 15,
                    "session_id": "batch_1"
                }
            }
        ],
        "notes": [
            "Multiple requests can run concurrently",
            "All URLs are saved to the same GCS location",
            "Duplicate URLs are automatically filtered out",
            "Maximum 50 pages per request"
        ]
    })

if __name__ == "__main__":
    # For local development
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=False)
