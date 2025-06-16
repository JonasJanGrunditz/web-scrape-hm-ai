import asyncio
import aiohttp
import json
import time

async def send_request(session, start_index, end_index):
    """Send a single request"""
    url = "https://hm-product-processor-api-utpsz4u73q-ew.a.run.app/process"
    payload = {"start_index": start_index, "end_index": end_index}
    
    async with session.post(url, json=payload) as response:
        result = await response.json()
        print(f"Request {start_index}-{end_index}: Status {response.status}")
        return result

async def send_multiple_requests(ranges):
    """Send multiple requests simultaneously"""
    timeout = aiohttp.ClientTimeout(total=600, connect=600, sock_read=600)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        
        tasks = []
        for start, end in ranges:
            task = send_request(session, start, end)
            tasks.append(task)
        
        # Execute all requests simultaneously
        results = await asyncio.gather(*tasks)
        return results


ranges = []
start_index = 1800
end_index = 5000
num_requests_per_batch = 10
for start in range(start_index,end_index, num_requests_per_batch):
    end = start + num_requests_per_batch -1
    ranges.append((start, end))

print(ranges)





# Run the async function
if __name__ == "__main__":
    ranges_batch = []
    for n, i in enumerate(ranges):
        if n % 20 == 0 and n > 0:
            print(f"Sending batch {ranges_batch} requests")
            results = asyncio.run(send_multiple_requests(ranges_batch))
            print(f"Completed {len(results)} requests")
            ranges_batch = []
       
        ranges_batch.append(i)

