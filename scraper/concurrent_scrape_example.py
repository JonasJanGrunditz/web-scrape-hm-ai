#!/usr/bin/env python3
"""
Example script demonstrating how to make multiple concurrent scraping requests
to the H&M scraper API. All results will be saved to the same GCS location.
"""

import asyncio
import aiohttp
import json
import time

async def make_scrape_request(session, base_url, start_page, end_page, session_id):
    """Make a single scraping request to the API."""
    url = f"{base_url}/scrape"
    payload = {
        "start_page": start_page,
        "end_page": end_page,
        "session_id": session_id
    }
    
    print(f"🚀 Starting request for pages {start_page}-{end_page} (session: {session_id})")
    start_time = time.time()
    
    try:
        async with session.post(url, json=payload) as response:
            result = await response.json()
            duration = time.time() - start_time
            
            if response.status == 200:
                print(f"✅ Session {session_id} completed in {duration:.1f}s: {result}")
            else:
                print(f"❌ Session {session_id} failed in {duration:.1f}s: {result}")
            
            return result
    except Exception as e:
        duration = time.time() - start_time
        print(f"💥 Session {session_id} errored in {duration:.1f}s: {str(e)}")
        return {"error": str(e)}

async def check_status(session, base_url):
    """Check the status of the scraping service."""
    try:
        async with session.get(f"{base_url}/status") as response:
            if response.status == 200:
                status = await response.json()
                print(f"📊 Service status: {status}")
            else:
                print(f"❌ Status check failed: {response.status}")
    except Exception as e:
        print(f"💥 Status check error: {str(e)}")

async def run_concurrent_scraping():
    """Run multiple scraping requests concurrently."""
    # Configuration
    base_url = "http://localhost:8080"  # Change to your deployed URL if needed
    
    # Define the page ranges to scrape concurrently
    scraping_tasks = [
        {"start_page": 1, "end_page": 5, "session_id": "batch_1"},
        {"start_page": 6, "end_page": 10, "session_id": "batch_2"},
        {"start_page": 11, "end_page": 15, "session_id": "batch_3"},
        {"start_page": 16, "end_page": 20, "session_id": "batch_4"},
    ]
    
    async with aiohttp.ClientSession() as session:
        print("🔍 Checking service status before starting...")
        await check_status(session, base_url)
        
        print(f"\n🎯 Starting {len(scraping_tasks)} concurrent scraping tasks...")
        start_time = time.time()
        
        # Create all scraping tasks
        tasks = [
            make_scrape_request(
                session, 
                base_url, 
                task["start_page"], 
                task["end_page"], 
                task["session_id"]
            ) 
            for task in scraping_tasks
        ]
        
        # Run all tasks concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        total_duration = time.time() - start_time
        print(f"\n🏁 All tasks completed in {total_duration:.1f}s")
        
        # Check final status
        print("\n🔍 Checking final service status...")
        await check_status(session, base_url)
        
        # Summary
        successful_tasks = sum(1 for r in results if isinstance(r, dict) and r.get("success"))
        total_urls = sum(r.get("urls_found", 0) for r in results if isinstance(r, dict))
        
        print(f"\n📈 Summary:")
        print(f"   ✅ Successful tasks: {successful_tasks}/{len(scraping_tasks)}")
        print(f"   🔗 Total URLs found: {total_urls}")
        print(f"   ⏱️  Total time: {total_duration:.1f}s")

if __name__ == "__main__":
    print("🕷️  H&M Concurrent Scraper Example")
    print("=====================================")
    print("This script will make multiple concurrent requests to scrape different page ranges.")
    print("All URLs will be saved to the same GCS location automatically.\n")
    
    try:
        asyncio.run(run_concurrent_scraping())
    except KeyboardInterrupt:
        print("\n⚠️  Scraping interrupted by user")
    except Exception as e:
        print(f"\n💥 Unexpected error: {str(e)}")
