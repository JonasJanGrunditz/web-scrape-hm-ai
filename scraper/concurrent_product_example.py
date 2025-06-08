#!/usr/bin/env python3
"""
Example script demonstrating how to make multiple concurrent product processing requests
to the H&M Product Processor API. All results will be saved to the same GCS location.
"""

import asyncio
import aiohttp
import json
import time

async def make_process_request(session, base_url, start_index, end_index, session_id, batch_size=5):
    """Make a single processing request to the API."""
    url = f"{base_url}/process"
    payload = {
        "start_index": start_index,
        "end_index": end_index,
        "session_id": session_id,
        "batch_size": batch_size
    }
    
    print(f"🚀 Starting request for indices {start_index}-{end_index} (session: {session_id})")
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
    """Check the status of the processing service."""
    try:
        async with session.get(f"{base_url}/status") as response:
            if response.status == 200:
                status = await response.json()
                print(f"📊 Service status: {status}")
            else:
                print(f"❌ Status check failed: {response.status}")
    except Exception as e:
        print(f"💥 Status check error: {str(e)}")

async def get_info(session, base_url):
    """Get information about available URLs to process."""
    try:
        async with session.get(f"{base_url}/info") as response:
            if response.status == 200:
                info = await response.json()
                print(f"📋 Available URLs info: {info}")
                return info
            else:
                print(f"❌ Info check failed: {response.status}")
                return None
    except Exception as e:
        print(f"💥 Info check error: {str(e)}")
        return None

async def run_concurrent_processing():
    """Run multiple processing requests concurrently."""
    # Configuration
    base_url = "http://localhost:8081"  # Change to your deployed URL if needed
    
    async with aiohttp.ClientSession() as session:
        print("🔍 Checking service status and getting URL info...")
        await check_status(session, base_url)
        info = await get_info(session, base_url)
        
        if not info or info.get("total_urls_available", 0) == 0:
            print("❌ No URLs available to process. Make sure the scraper has run first.")
            return
        
        total_urls = info["total_urls_available"]
        print(f"📈 Found {total_urls} URLs available for processing")
        
        # Define the index ranges to process concurrently
        # Adjust these based on your needs and available URLs
        batch_size = 10  # URLs per request
        processing_tasks = []
        
        # Create tasks for concurrent processing
        for i in range(0, min(total_urls, 40), batch_size):  # Process first 40 URLs max
            end_idx = min(i + batch_size - 1, total_urls - 1)
            processing_tasks.append({
                "start_index": i,
                "end_index": end_idx,
                "session_id": f"batch_{i//batch_size + 1}",
                "batch_size": 3  # Internal batch size for processing
            })
        
        print(f"\n🎯 Starting {len(processing_tasks)} concurrent processing tasks...")
        start_time = time.time()
        
        # Create all processing tasks
        tasks = [
            make_process_request(
                session, 
                base_url, 
                task["start_index"], 
                task["end_index"], 
                task["session_id"],
                task["batch_size"]
            ) 
            for task in processing_tasks
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
        total_processed = sum(r.get("products_processed", 0) for r in results if isinstance(r, dict))
        total_failed = sum(r.get("products_failed", 0) for r in results if isinstance(r, dict))
        
        print(f"\n📈 Summary:")
        print(f"   ✅ Successful tasks: {successful_tasks}/{len(processing_tasks)}")
        print(f"   🔗 Total products processed: {total_processed}")
        print(f"   ❌ Total products failed: {total_failed}")
        print(f"   ⏱️  Total time: {total_duration:.1f}s")

if __name__ == "__main__":
    print("🕷️  H&M Concurrent Product Processor Example")
    print("=============================================")
    print("This script will make multiple concurrent requests to process different URL ranges.")
    print("All processed product data will be saved to the same GCS location automatically.\n")
    
    try:
        asyncio.run(run_concurrent_processing())
    except KeyboardInterrupt:
        print("\n⚠️  Processing interrupted by user")
    except Exception as e:
        print(f"\n💥 Unexpected error: {str(e)}")
