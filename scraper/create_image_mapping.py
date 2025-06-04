import json
import asyncio
import os
from dotenv import load_dotenv
from crawl4ai import AsyncWebCrawler
from crawl4ai.async_configs import BrowserConfig, CrawlerRunConfig
from gcp.gcp_bucket import download_urls_from_gcs, upload_urls_to_gcs
from product import extract_product_id, extract_urls_from_markdown
from gcp.gcp_bucket import upload_image_mapping_to_gcs
from transformation.hardcoded_re import extract_product_id, extract_urls_from_markdown

# Load environment variables
load_dotenv()

async def extract_image_url_from_page(url, browser_config, run_config, max_retries=3):
    """Extract image URL from a single page with retry logic."""
    for attempt in range(max_retries):
        try:
            async with AsyncWebCrawler(config=browser_config) as crawler:
                result = await crawler.arun(url=url, config=run_config)
                
                if result.success:
                    print(f"Successfully crawled {url} on attempt {attempt + 1}")
                    try:
                        image_url = extract_urls_from_markdown(result.markdown)
                        
                        return image_url
                    except (IndexError, AttributeError):
                        print(f"Warning: No image URL found in markdown for {url}")
                        return None
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
            await asyncio.sleep(2 ** attempt)
    
    return None



async def create_image_mapping():
    """Create mapping of article ID to image URL and upload to GCP."""
    

    # Download URLs from GCP bucket
    garment_urls = download_urls_from_gcs()[:1]
    
    print(f"Downloaded {len(garment_urls)} URLs from GCP bucket")
    
    # Setup crawler configs
    browser_config = BrowserConfig()
    run_config = CrawlerRunConfig()
    
    # Dictionary to store article_id -> image_url mapping
    image_mapping = {}
    
    # Process each URL
    for i, url in enumerate(garment_urls, 1):
        print(f"Processing URL {i}/{len(garment_urls)}: {url}")
        
        # Extract article ID from URL
        article_id = extract_product_id(url)
        if not article_id:
            print(f"Warning: Could not extract article ID from {url}")
            continue
        
        # Extract image URL from page content
        image_url = await extract_image_url_from_page(url, browser_config, run_config)
        
        if image_url:
            image_mapping[article_id] = image_url
            print(f"Mapped article {article_id} -> {image_url}")
        else:
            print(f"Warning: Could not extract image URL for article {article_id}")
        
        # Small delay to be gentle on the server
        if i < len(garment_urls):
            await asyncio.sleep(1)
    
    print(f"Created mapping for {len(image_mapping)} articles")
    
    # Upload to GCP bucket using the new function
    success = upload_image_mapping_to_gcs(image_mapping)

    if not success:
        # Save locally as backup 
        with open("image_mapping_backup.json", "w") as f:
            json.dump(image_mapping, f, indent=2)
        print("Saved backup locally as image_mapping_backup.json")
    
    return image_mapping

async def main():
    print("Starting image mapping creation...")
    mapping = await create_image_mapping()
    print(f"Process completed. Total mappings created: {len(mapping)}")

if __name__ == "__main__":
    asyncio.run(main())
