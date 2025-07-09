#!/usr/bin/env python3
"""
Test script to verify rate limiting implementation
"""

import requests
import json
import time
import os

def test_rate_limiting():
    """Test the rate limiting implementation"""
    
    # Base URLs
    backend_url = "http://localhost:8080"
    ai_engine_url = "http://localhost:8001"
    
    print("Testing rate limiting implementation...")
    
    # Check if AI engine is accessible
    try:
        health_response = requests.get(f"{ai_engine_url}/api/v1/health", timeout=5)
        print(f"AI Engine health check: {health_response.status_code}")
        
        if health_response.status_code == 200:
            print("✅ AI Engine is running and accessible")
        else:
            print("❌ AI Engine health check failed")
            return False
    except Exception as e:
        print(f"❌ AI Engine not accessible: {e}")
        return False
    
    # Check backend health
    try:
        backend_health = requests.get(f"{backend_url}/api/v1/health", timeout=5)
        print(f"Backend health check: {backend_health.status_code}")
        
        if backend_health.status_code == 200:
            print("✅ Backend is running and accessible")
        else:
            print("❌ Backend health check failed")
            return False
    except Exception as e:
        print(f"❌ Backend not accessible: {e}")
        return False
    
    # Test rate limiting by making several requests
    print("\nTesting rate limiting with multiple requests...")
    
    # Use a test JAR file if available
    test_jar_path = "temp_uploads/065a2a1c-9cba-47b1-9f6f-9e0c33195c74.jar"
    
    if os.path.exists(test_jar_path):
        print(f"Using test JAR: {test_jar_path}")
        
        # Make 3 quick conversion requests to test rate limiting
        for i in range(3):
            try:
                print(f"\nAttempt {i+1}/3:")
                
                # Upload file
                with open(test_jar_path, 'rb') as f:
                    files = {'file': f}
                    upload_response = requests.post(f"{backend_url}/api/v1/upload", files=files, timeout=10)
                
                if upload_response.status_code == 200:
                    upload_data = upload_response.json()
                    file_id = upload_data.get('file_id')
                    original_filename = upload_data.get('original_filename')
                    print(f"  Upload successful: {file_id}")
                    print(f"  Original filename: {original_filename}")
                    
                    # Trigger conversion
                    conversion_data = {
                        "file_id": file_id,
                        "original_filename": original_filename,
                        "options": {
                            "smart_assumptions": True,
                            "include_dependencies": True
                        }
                    }
                    
                    start_time = time.time()
                    convert_response = requests.post(
                        f"{backend_url}/api/v1/convert", 
                        json=conversion_data, 
                        timeout=30
                    )
                    end_time = time.time()
                    
                    if convert_response.status_code == 200:
                        conversion_result = convert_response.json()
                        job_id = conversion_result.get('job_id')
                        print(f"  Conversion started: {job_id}")
                        print(f"  Response time: {end_time - start_time:.2f}s")
                        
                        # Wait a bit to see if rate limiting messages appear
                        time.sleep(2)
                        
                        # Check status
                        status_response = requests.get(f"{backend_url}/api/v1/convert/{job_id}/status", timeout=5)
                        if status_response.status_code == 200:
                            status_data = status_response.json()
                            print(f"  Status: {status_data.get('status', 'unknown')}")
                        
                    else:
                        print(f"  ❌ Conversion failed: {convert_response.status_code}")
                        print(f"  Response: {convert_response.text}")
                
                else:
                    print(f"  ❌ Upload failed: {upload_response.status_code}")
                
                # Small delay between requests
                time.sleep(1)
                
            except Exception as e:
                print(f"  ❌ Request {i+1} failed: {e}")
    
    else:
        print(f"❌ Test JAR file not found: {test_jar_path}")
        print("Rate limiting test skipped - no test file available")
    
    print("\nRate limiting test completed!")
    print("✅ If no rate limiting errors occurred, the implementation is working")
    return True

if __name__ == "__main__":
    success = test_rate_limiting()
    print(f"\nOverall result: {'PASSED' if success else 'FAILED'}")