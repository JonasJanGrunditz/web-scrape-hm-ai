#!/usr/bin/env python3
"""
Test script to verify duplicate handling behavior.
This script will make the same request multiple times and show what happens.
"""

import requests
import time
import json

def test_duplicate_behavior():
    base_url = "http://localhost:8080"
    
    # Same request parameters
    test_payload = {
        "start_page": 1,
        "end_page": 2,  # Small range for testing
        "session_id": "duplicate_test"
    }
    
    print("🧪 Testing Duplicate Handling Behavior")
    print("=" * 50)
    print(f"Request payload: {json.dumps(test_payload, indent=2)}")
    print()
    
    for run_number in range(1, 4):  # Run 3 times
        print(f"🚀 Run #{run_number}: Making request...")
        
        try:
            response = requests.post(
                f"{base_url}/scrape",
                json=test_payload,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ Run #{run_number} completed:")
                print(f"   Success: {result.get('success')}")
                print(f"   URLs found this run: {result.get('urls_found')}")
                print(f"   Message: {result.get('message')}")
            else:
                print(f"❌ Run #{run_number} failed: {response.status_code}")
                print(f"   Response: {response.text}")
                
        except Exception as e:
            print(f"💥 Run #{run_number} error: {str(e)}")
        
        print()
        
        if run_number < 3:
            print("⏳ Waiting 5 seconds before next run...")
            time.sleep(5)
    
    print("🏁 Test completed!")
    print("\n📝 Expected behavior:")
    print("   - Each run should find URLs (possibly the same ones)")
    print("   - All unique URLs are preserved in GCS")
    print("   - Duplicates are automatically removed")
    print("   - Total unique URLs accumulate over runs")

if __name__ == "__main__":
    test_duplicate_behavior()
