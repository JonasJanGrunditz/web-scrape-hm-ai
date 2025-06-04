import asyncio
import os
import re
from flask import Flask, request, jsonify
from crawl4ai import AsyncWebCrawler
from crawl4ai.async_configs import BrowserConfig, CrawlerRunConfig
from gcp.gcp_bucket import upload_urls_to_gcs

app = Flask(__name__)

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

async def scrape_hm_products(start_page, end_page):
    """Main scraping function that can be called with custom page ranges."""
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
                print(f"Successfully scraped page {index}, found {len(garment_urls)} URLs")
            else:
                print(f"Crawl failed for page {index}: {result.error_message}")
        except Exception as e:
            print(f"Error scraping page {index}: {str(e)}")
    
    # Upload to GCS
    if all_urls:
        upload_urls_to_gcs(all_urls)
        return {"success": True, "urls_found": len(all_urls), "message": f"Successfully scraped pages {start_page}-{end_page}"}
    else:
        return {"success": False, "urls_found": 0, "message": "No URLs found"}

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint for Cloud Run."""
    return jsonify({"status": "healthy"})

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
        
        # Run the scraping function
        result = asyncio.run(scrape_hm_products(start_page, end_page))
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({"error": f"Internal server error: {str(e)}"}), 500

@app.route('/', methods=['GET'])
def root():
    """Root endpoint with usage instructions."""
    return jsonify({
        "message": "H&M Scraper API",
        "endpoints": {
            "POST /scrape": "Scrape H&M products with start_page and end_page parameters",
            "GET /health": "Health check endpoint"
        },
        "example_request": {
            "url": "/scrape",
            "method": "POST",
            "body": {
                "start_page": 1,
                "end_page": 5
            }
        }
    })

if __name__ == "__main__":
    # For local development
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=False)
