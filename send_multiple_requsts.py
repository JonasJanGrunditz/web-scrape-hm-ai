import asyncio
import aiohttp
import json

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
    async with aiohttp.ClientSession() as session:
        tasks = []
        
        
        for start, end in ranges:
            task = send_request(session, start, end)
            tasks.append(task)
        
        # Execute all requests simultaneously
        results = await asyncio.gather(*tasks)
        return results


ranges = []
start_index = 0
end_index = 200
num_requests_per_batch = 10
for start in range(start_index,end_index, num_requests_per_batch):
    end = start + num_requests_per_batch -1
    ranges.append((start, end))

print(ranges)


# Run the async function
if __name__ == "__main__":
    results = asyncio.run(send_multiple_requests(ranges))
    print(f"Completed {len(results)} requests")
