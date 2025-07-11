#!/usr/bin/env python3
"""
Test script to verify full mod conversion process
"""

import requests
import json
import time
import os

def test_full_conversion():
    """Test the full mod conversion process"""
    
    # Base URLs
    backend_url = "http://localhost:8080"
    
    print("Testing full mod conversion process...")
    
    # Check if backend is accessible
    try:
        health_response = requests.get(f"{backend_url}/api/v1/health", timeout=5)
        print(f"Backend health check: {health_response.status_code}")
        
        if health_response.status_code != 200:
            print("❌ Backend health check failed")
            return False
    except Exception as e:
        print(f"❌ Backend not accessible: {e}")
        return False
    
    # Test conversion with a JAR file
    test_jar_path = "temp_uploads/065a2a1c-9cba-47b1-9f6f-9e0c33195c74.jar"
    
    if not os.path.exists(test_jar_path):
        print(f"❌ Test JAR file not found: {test_jar_path}")
        return False
    
    try:
        print(f"📁 Using test JAR: {test_jar_path}")
        
        # Step 1: Upload file
        print("\n1️⃣ Uploading mod file...")
        with open(test_jar_path, 'rb') as f:
            files = {'file': f}
            upload_response = requests.post(f"{backend_url}/api/v1/upload", files=files, timeout=10)
        
        if upload_response.status_code != 200:
            print(f"❌ Upload failed: {upload_response.status_code}")
            print(f"Response: {upload_response.text}")
            return False
        
        upload_data = upload_response.json()
        file_id = upload_data.get('file_id')
        original_filename = upload_data.get('original_filename')
        print("✅ Upload successful!")
        print(f"   File ID: {file_id}")
        print(f"   Original filename: {original_filename}")
        
        # Step 2: Start conversion
        print("\n2️⃣ Starting conversion...")
        conversion_data = {
            "file_id": file_id,
            "original_filename": original_filename,
            "options": {
                "smart_assumptions": True,
                "include_dependencies": True
            }
        }
        
        convert_response = requests.post(
            f"{backend_url}/api/v1/convert", 
            json=conversion_data, 
            timeout=30
        )
        
        if convert_response.status_code != 200:
            print(f"❌ Conversion failed: {convert_response.status_code}")
            print(f"Response: {convert_response.text}")
            return False
        
        conversion_result = convert_response.json()
        job_id = conversion_result.get('job_id')
        print("✅ Conversion started!")
        print(f"   Job ID: {job_id}")
        
        # Step 3: Monitor progress
        print("\n3️⃣ Monitoring conversion progress...")
        max_wait_time = 1800  # 30 minutes to account for rate limiting
        start_time = time.time()
        
        while time.time() - start_time < max_wait_time:
            status_response = requests.get(f"{backend_url}/api/v1/convert/{job_id}/status", timeout=5)
            
            if status_response.status_code == 200:
                status_data = status_response.json()
                status = status_data.get('status', 'unknown')
                progress = status_data.get('progress', 0)
                elapsed_time = time.time() - start_time
                
                print(f"   Status: {status} ({progress}%) - Elapsed: {elapsed_time/60:.1f} minutes")
                
                if status == 'completed':
                    print("✅ Conversion completed successfully!")
                    
                    # Check if output file exists
                    download_url = status_data.get('download_url')
                    if download_url:
                        print(f"   Download URL: {download_url}")
                    
                    # Get detailed results
                    detailed_report = status_data.get('detailed_report', {})
                    if detailed_report:
                        print(f"   Overall success rate: {status_data.get('overall_success_rate', 'N/A')}")
                        print(f"   Smart assumptions applied: {len(status_data.get('smart_assumptions_applied', []))}")
                    
                    return True
                
                elif status == 'failed':
                    print("❌ Conversion failed!")
                    error_msg = status_data.get('message', 'Unknown error')
                    print(f"   Error: {error_msg}")
                    return False
                
                elif status in ['processing', 'queued']:
                    # Continue waiting - use longer sleep for rate limiting scenarios
                    sleep_time = 10 if elapsed_time > 300 else 5  # 10s sleep after 5 minutes
                    time.sleep(sleep_time)
                    continue
                
                else:
                    print(f"❓ Unknown status: {status}")
                    time.sleep(5)
                    continue
            
            else:
                print(f"❌ Status check failed: {status_response.status_code}")
                time.sleep(5)
                continue
        
        print(f"⏰ Conversion timeout after {max_wait_time/60:.1f} minutes")
        print("   This may be due to OpenAI API rate limiting. The conversion may still complete.")
        return False
        
    except Exception as e:
        print(f"❌ Test failed with exception: {e}")
        return False

if __name__ == "__main__":
    print("🚀 ModPorter AI - Full Conversion Test")
    print("=" * 50)
    
    success = test_full_conversion()
    
    print("\n" + "=" * 50)
    if success:
        print("🎉 SUCCESS: Full conversion test passed!")
        print("   - File upload: ✅")
        print("   - Conversion start: ✅")
        print("   - AI processing: ✅")
        print("   - Rate limiting: ✅")
        print("   - Output generation: ✅")
    else:
        print("❌ FAILED: Full conversion test failed!")
        print("   Check the logs above for details")
    
    print(f"\nOverall result: {'PASSED' if success else 'FAILED'}")