import time
import asyncio
import os
from dotenv import load_dotenv
from crawl4ai import AsyncWebCrawler
from crawl4ai.async_configs import BrowserConfig, CrawlerRunConfig
import re
from groq import Groq
from llm.openai import extract_sections_from_markdown_openai
from gcp.gcp_bucket import download_urls_from_gcs, upload_urls_to_gcs
from llm.openai import extract_sections_from_markdown_openai
from openai import OpenAI

# Load environment variables
load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))



import html

def between_size_and_material(text: str) -> str | None:
    """
    returns everything that sits between the headings
    "Välj storlek"  …  "Ytterligare materialinformation"
    """

    # 1) normalise the text for pattern matching --------------------------
    txt_normalized = html.unescape(text)          # turns &nbsp; → '\xa0' etc.
    txt_normalized = txt_normalized.replace('\xa0', ' ')     # non-breaking space → space
    txt_normalized = txt_normalized.lower()                  # ignore case completely

    # 2) regex: be generous with white-space inside the headings ------------
    pattern = (
        r"välj\s+storlek"               # start
        r"\s*(.*?)\s*"                  # everything in between
        r"(?:ytterligare\s+materialinformation"  # end option 1
        r"|förklaring\s+av\s+materialen"         # end option 2
        r"|skötselråd)"                           # end option 3  ← NEW
    )

    # 3) Find the match in normalized text to get positions
    m = re.search(pattern, txt_normalized, flags=re.DOTALL)
    
    if m:
        # Get the original text preserving formatting
        original_text = html.unescape(text).replace('\xa0', ' ')
        
        # Find the same pattern in original text (case-insensitive)
        original_pattern = (
            r"välj\s+storlek"
            r"\s*(.*?)\s*"
            r"(?:ytterligare\s+materialinformation"
            r"|förklaring\s+av\s+materialen"
            r"|skötselråd)"
        )
        
        original_match = re.search(original_pattern, original_text, flags=re.DOTALL | re.IGNORECASE)
        
        if original_match:
            text = "välj storlek " + original_match.group(1).strip()
        else:
            text = "välj storlek " + m.group(1).strip()
    else:
        text = None
    
    
    return text


async def crawl_url(url, browser_config, run_config, client, max_retries=3):
    """Crawl a single URL with retry logic for better reliability."""
    for attempt in range(max_retries):
        try:
            async with AsyncWebCrawler(config=browser_config) as crawler:
                result = await crawler.arun(url=url, config=run_config)
                
                if result.success:
                    print(f"Successfully crawled {url} on attempt {attempt + 1}")
                    extracted_content = between_size_and_material(result.markdown)
                    if extracted_content is None:
                        print(f"Warning: No content extracted from {url} - pattern not found")
                       # print(result.markdown)
                    else:
                     
                        extracted_content_cleaned = extract_sections_from_markdown_openai(extracted_content, client)
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

async def process_batch(urls, browser_config, run_config, client, batch_num):
    """Process a single batch of URLs."""
    print(f"Processing batch {batch_num} with {len(urls)} URLs...")
    
    tasks = [
        crawl_url(url, browser_config, run_config, client)
        for url in urls
    ]
    
    batch_results = await asyncio.gather(*tasks)
    
    print(f"Completed batch {batch_num}")
    
    return batch_results

async def main():
    start_time = time.perf_counter()
    
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    garment_urls = download_urls_from_gcs()[:500]
    browser_config = BrowserConfig()  # Default browser configuration
    run_config = CrawlerRunConfig()     # Default crawl run configuration

    print(f"Total URLs to process: {len(garment_urls)}")
    
    # Process URLs in batches of 5
    batch_size = 5
    all_content = []
    
    for batch_num, batch_urls in enumerate(create_batches(garment_urls, batch_size), 1):
        batch_results = await process_batch(batch_urls, browser_config, run_config, client, batch_num)
        all_content.extend(batch_results)
        
        # Optional: Add a small delay between batches to be gentle on the server
        if batch_num < len(garment_urls) // batch_size + (1 if len(garment_urls) % batch_size else 0):
            print("Waiting 2 seconds before next batch...")
            await asyncio.sleep(2)

    # Filter out None results and track failures
    valid_content = [content for content in all_content if content is not None]
    failed_count = len(all_content) - len(valid_content)
    
    print(f"Successfully processed {len(valid_content)} out of {len(garment_urls)} URLs")
    print(f"Failed to extract content from {failed_count} URLs")

    upload_urls_to_gcs(
        valid_content,
        bucket_name="web-scrape-ai",
        destination_blob_name="garments-info/products-info.txt",
        project_id="voii-459718"
    )

    elapsed = time.perf_counter() - start_time
    print(f"Execution time: {elapsed:.2f} seconds")

if __name__ == "__main__":
    asyncio.run(main())

