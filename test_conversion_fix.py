#!/usr/bin/env python3
"""
Quick test script to verify the SmartAssumptionEngine serialization fix
"""

import requests
import json
import time
import os

def test_conversion():
    """Test the conversion process to see if the serialization issue is fixed"""
    
    # Base URLs
    backend_url = "http://localhost:8080"
    
    # Check if backend is accessible
    try:
        health_response = requests.get(f"{backend_url}/api/v1/health", timeout=5)
        print(f"Backend health check: {health_response.status_code}")
    except Exception as e:
        print(f"Backend not accessible: {e}")
        return False
    
    # Test conversion with a JAR file (simulate upload and convert)
    jar_file = "temp_uploads/065a2a1c-9cba-47b1-9f6f-9e0c33195c74.jar"
    
    if not os.path.exists(jar_file):
        print(f"Test JAR file not found: {jar_file}")
        return False
    
    # Create a simple POST request to trigger conversion
    try:
        # First, we need to upload the file
        with open(jar_file, 'rb') as f:
            files = {'file': f}
            upload_response = requests.post(f"{backend_url}/api/v1/upload", files=files, timeout=10)
            
        if upload_response.status_code != 200:
            print(f"Upload failed: {upload_response.status_code} - {upload_response.text}")
            return False
            
        upload_data = upload_response.json()
        file_id = upload_data.get('file_id')
        print(f"Upload successful, file_id: {file_id}")
        
        # Now trigger conversion
        conversion_data = {
            "file_id": file_id,
            "options": {
                "smart_assumptions": True,
                "include_dependencies": True
            }
        }
        
        convert_response = requests.post(
            f"{backend_url}/api/v1/convert", 
            json=conversion_data, 
            timeout=10
        )
        
        if convert_response.status_code != 200:
            print(f"Conversion failed: {convert_response.status_code} - {convert_response.text}")
            return False
            
        conversion_result = convert_response.json()
        job_id = conversion_result.get('job_id')
        print(f"Conversion started, job_id: {job_id}")
        
        # Wait a few seconds to see if the SmartAssumptionEngine error occurs
        time.sleep(10)
        
        # Check the conversion status
        status_response = requests.get(f"{backend_url}/api/v1/convert/{job_id}/status", timeout=5)
        if status_response.status_code == 200:
            status_data = status_response.json()
            print(f"Conversion status: {status_data.get('status')}")
            print(f"Progress: {status_data.get('progress', 'N/A')}%")
            
            if status_data.get('status') == 'failed':
                print(f"Conversion failed with message: {status_data.get('message', 'Unknown error')}")
                return False
            else:
                print("Conversion appears to be working (no SmartAssumptionEngine serialization error)")
                return True
        else:
            print(f"Status check failed: {status_response.status_code}")
            return False
            
    except Exception as e:
        print(f"Test failed with exception: {e}")
        return False

if __name__ == "__main__":
    print("Testing conversion process after SmartAssumptionEngine fix...")
    success = test_conversion()
    print(f"Test result: {'PASSED' if success else 'FAILED'}")
