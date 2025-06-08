#!/usr/bin/env python3
"""
Comprehensive test script for the Product API /process endpoint.
Tests validation, error handling, and concurrent processing behavior.
"""

import requests
import json
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

BASE_URL = "http://localhost:8081"

def test_endpoint_validation():
    """Test endpoint validation and error handling."""
    print("🧪 Testing endpoint validation and error handling...")
    
    test_cases = [
        # Valid cases that should pass validation
        {
            "name": "Valid small range",
            "data": {"start_index": 0, "end_index": 2},
            "expected_status": 200,  # Will fail due to OpenAI key but passes validation
            "should_pass_validation": True
        },
        {
            "name": "Valid with session ID",
            "data": {"start_index": 5, "end_index": 7, "session_id": "test_session", "batch_size": 2},
            "expected_status": 200,
            "should_pass_validation": True
        },
        
        # Invalid cases that should fail validation
        {
            "name": "Missing start_index",
            "data": {"end_index": 5},
            "expected_status": 400,
            "should_pass_validation": False
        },
        {
            "name": "Missing end_index", 
            "data": {"start_index": 0},
            "expected_status": 400,
            "should_pass_validation": False
        },
        {
            "name": "Negative start_index",
            "data": {"start_index": -1, "end_index": 5},
            "expected_status": 400,
            "should_pass_validation": False
        },
        {
            "name": "Start > End",
            "data": {"start_index": 10, "end_index": 5},
            "expected_status": 400,
            "should_pass_validation": False
        },
        {
            "name": "Range too large",
            "data": {"start_index": 0, "end_index": 150},  # >100 URLs
            "expected_status": 400,
            "should_pass_validation": False
        },
        {
            "name": "Invalid batch_size (too small)",
            "data": {"start_index": 0, "end_index": 5, "batch_size": 0},
            "expected_status": 400,
            "should_pass_validation": False
        },
        {
            "name": "Invalid batch_size (too large)",
            "data": {"start_index": 0, "end_index": 5, "batch_size": 25},
            "expected_status": 400,
            "should_pass_validation": False
        },
        {
            "name": "Non-integer indices",
            "data": {"start_index": "abc", "end_index": "def"},
            "expected_status": 400,
            "should_pass_validation": False
        },
    ]
    
    results = []
    for test in test_cases:
        print(f"  Testing: {test['name']}")
        
        try:
            response = requests.post(f"{BASE_URL}/process", json=test["data"], timeout=10)
            result = response.json()
            
            # Check if status code matches expectation
            status_match = response.status_code == test["expected_status"]
            
            # For validation failures, check that we get an error message
            if not test["should_pass_validation"]:
                has_error = "error" in result
                validation_result = status_match and has_error
            else:
                # For valid requests, they should pass validation but fail due to OpenAI key
                validation_result = status_match and (
                    result.get("success") == False and 
                    "api_key" in result.get("message", "").lower()
                )
            
            results.append({
                "test": test["name"],
                "passed": validation_result,
                "status": response.status_code,
                "response": result
            })
            
            print(f"    ✅ PASS" if validation_result else f"    ❌ FAIL")
            if not validation_result:
                print(f"    Expected status: {test['expected_status']}, Got: {response.status_code}")
                print(f"    Response: {result}")
                
        except Exception as e:
            results.append({
                "test": test["name"],
                "passed": False,
                "error": str(e)
            })
            print(f"    ❌ ERROR: {str(e)}")
    
    return results

def test_concurrent_requests():
    """Test concurrent processing requests."""
    print("\n🔄 Testing concurrent processing requests...")
    
    def make_request(session_id):
        """Make a single processing request."""
        start_time = time.time()
        try:
            response = requests.post(
                f"{BASE_URL}/process",
                json={
                    "start_index": session_id * 2,  # Different ranges for each session
                    "end_index": session_id * 2 + 1,
                    "session_id": f"concurrent_test_{session_id}",
                    "batch_size": 1
                },
                timeout=30
            )
            duration = time.time() - start_time
            return {
                "session_id": session_id,
                "status_code": response.status_code,
                "response": response.json(),
                "duration": duration,
                "success": True
            }
        except Exception as e:
            duration = time.time() - start_time
            return {
                "session_id": session_id,
                "error": str(e),
                "duration": duration,
                "success": False
            }
    
    # Test with 3 concurrent requests
    num_concurrent = 3
    print(f"  Making {num_concurrent} concurrent requests...")
    
    with ThreadPoolExecutor(max_workers=num_concurrent) as executor:
        futures = [executor.submit(make_request, i) for i in range(num_concurrent)]
        results = []
        
        for future in as_completed(futures):
            result = future.result()
            results.append(result)
            
            if result["success"]:
                print(f"    Session {result['session_id']}: {result['status_code']} in {result['duration']:.2f}s")
            else:
                print(f"    Session {result['session_id']}: ERROR in {result['duration']:.2f}s - {result['error']}")
    
    return results

def test_status_during_processing():
    """Test status endpoint during processing."""
    print("\n📊 Testing status monitoring during processing...")
    
    # Start a processing request in background
    def background_request():
        try:
            response = requests.post(
                f"{BASE_URL}/process",
                json={"start_index": 0, "end_index": 3, "session_id": "status_test"},
                timeout=30
            )
            return response.json()
        except Exception as e:
            return {"error": str(e)}
    
    # Start background processing
    result_container = []
    thread = threading.Thread(target=lambda: result_container.append(background_request()))
    thread.start()
    
    # Monitor status while processing
    status_checks = []
    for i in range(5):  # Check status 5 times
        time.sleep(0.5)  # Wait 500ms between checks
        try:
            status_response = requests.get(f"{BASE_URL}/status", timeout=5)
            status_checks.append({
                "check": i + 1,
                "status": status_response.json(),
                "timestamp": time.time()
            })
            print(f"    Status check {i + 1}: {status_response.json()}")
        except Exception as e:
            print(f"    Status check {i + 1}: ERROR - {str(e)}")
    
    # Wait for background request to complete
    thread.join()
    
    # Final status check
    try:
        final_status = requests.get(f"{BASE_URL}/status", timeout=5).json()
        print(f"    Final status: {final_status}")
    except Exception as e:
        print(f"    Final status: ERROR - {str(e)}")
    
    return {
        "status_checks": status_checks,
        "processing_result": result_container[0] if result_container else None
    }

def test_api_info():
    """Test the info endpoint to verify URL availability."""
    print("\n📋 Testing API info endpoint...")
    
    try:
        response = requests.get(f"{BASE_URL}/info", timeout=10)
        info = response.json()
        
        print(f"    Total URLs available: {info.get('total_urls_available', 'Unknown')}")
        print(f"    Index range: {info.get('index_range', 'Unknown')}")
        print(f"    Sample URLs: {len(info.get('sample_urls', []))} shown")
        
        return {
            "success": True,
            "info": info
        }
    except Exception as e:
        print(f"    ❌ ERROR: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }

def main():
    """Run all tests."""
    print("🚀 Starting comprehensive Product API /process endpoint tests...\n")
    
    # Test API availability
    try:
        health_response = requests.get(f"{BASE_URL}/health", timeout=5)
        if health_response.status_code != 200:
            print("❌ API is not responding correctly!")
            return
        print("✅ API is running and healthy\n")
    except Exception as e:
        print(f"❌ Cannot connect to API: {str(e)}")
        return
    
    # Run all tests
    test_results = {}
    
    test_results["info"] = test_api_info()
    test_results["validation"] = test_endpoint_validation()
    test_results["concurrent"] = test_concurrent_requests()
    test_results["status_monitoring"] = test_status_during_processing()
    
    # Summary
    print("\n" + "="*60)
    print("📋 TEST SUMMARY")
    print("="*60)
    
    validation_passed = sum(1 for r in test_results["validation"] if r.get("passed", False))
    validation_total = len(test_results["validation"])
    print(f"Validation tests: {validation_passed}/{validation_total} passed")
    
    concurrent_successful = sum(1 for r in test_results["concurrent"] if r.get("success", False))
    concurrent_total = len(test_results["concurrent"])
    print(f"Concurrent requests: {concurrent_successful}/{concurrent_total} completed")
    
    info_success = test_results["info"]["success"]
    print(f"Info endpoint: {'✅ Working' if info_success else '❌ Failed'}")
    
    print(f"\nNote: All processing requests are expected to fail due to missing OpenAI API key.")
    print(f"This tests the API structure and validation logic.")
    
    return test_results

if __name__ == "__main__":
    results = main()
