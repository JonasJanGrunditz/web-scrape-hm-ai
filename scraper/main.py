import asyncio
import re
from crawl4ai import AsyncWebCrawler
from crawl4ai.async_configs import BrowserConfig, CrawlerRunConfig
from gcp.gcp_bucket import upload_urls_to_gcs

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

async def main():

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
    for index in range(1, 3):
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
        else:
            print(f"Crawl failed: {result.error_message}")
    upload_urls_to_gcs(all_urls)

if __name__ == "__main__":
    asyncio.run(main())






