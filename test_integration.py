#!/usr/bin/env python3
"""
Test script to verify dashboard backend integration
"""
import asyncio
import aiohttp
import json
import time

async def test_upload_and_conversion():
    """Test the complete upload -> conversion -> download workflow"""
    
    # Create a test file
    test_file_content = b"test jar content for conversion"
    
    async with aiohttp.ClientSession() as session:
        # Test 1: Health check
        print("🏥 Testing health endpoint...")
        async with session.get('http://localhost:8000/api/v1/health') as response:
            if response.status == 200:
                health_data = await response.json()
                print(f"✅ Health check passed: {health_data['status']}")
            else:
                print(f"❌ Health check failed: {response.status}")
                return False

        # Test 2: File upload
        print("\n📁 Testing file upload...")
        data = aiohttp.FormData()
        data.add_field('file', test_file_content, filename='test_mod.jar', content_type='application/java-archive')
        
        async with session.post('http://localhost:8000/api/v1/upload', data=data) as response:
            if response.status == 200:
                upload_result = await response.json()
                print(f"✅ File upload successful: {upload_result['file_id']}")
                file_id = upload_result['file_id']
                original_filename = upload_result['original_filename']
            else:
                print(f"❌ File upload failed: {response.status}")
                error_text = await response.text()
                print(f"Error: {error_text}")
                return False

        # Test 3: Start conversion
        print("\n🔄 Testing conversion start...")
        conversion_request = {
            "file_id": file_id,
            "original_filename": original_filename,
            "target_version": "1.20.0",
            "options": {
                "smartAssumptions": True,
                "includeDependencies": True
            }
        }
        
        async with session.post('http://localhost:8000/api/v1/convert', json=conversion_request) as response:
            if response.status == 200:
                conversion_result = await response.json()
                print(f"✅ Conversion started: {conversion_result['job_id']}")
                job_id = conversion_result['job_id']
            else:
                print(f"❌ Conversion start failed: {response.status}")
                error_text = await response.text()
                print(f"Error: {error_text}")
                return False

        # Test 4: Poll conversion status
        print("\n📊 Testing conversion status polling...")
        for i in range(15):  # Poll for up to 30 seconds
            await asyncio.sleep(2)
            
            async with session.get(f'http://localhost:8000/api/v1/convert/{job_id}/status') as response:
                if response.status == 200:
                    status_result = await response.json()
                    status = status_result['status']
                    progress = status_result['progress']
                    message = status_result['message']
                    
                    print(f"📈 Status: {status} ({progress}%) - {message}")
                    
                    if status == 'completed':
                        print("✅ Conversion completed successfully!")
                        result_url = status_result.get('result_url')
                        if result_url:
                            print(f"📥 Download URL: {result_url}")
                        break
                    elif status == 'failed':
                        print(f"❌ Conversion failed: {status_result.get('error', 'Unknown error')}")
                        return False
                else:
                    print(f"❌ Status check failed: {response.status}")
                    return False
        else:
            print("⏰ Conversion timed out")
            return False

        # Test 5: Download result
        print("\n📥 Testing file download...")
        async with session.get(f'http://localhost:8000/api/v1/convert/{job_id}/download') as response:
            if response.status == 200:
                download_content = await response.read()
                print(f"✅ File download successful: {len(download_content)} bytes")
                
                # Check content-disposition header
                content_disposition = response.headers.get('Content-Disposition', '')
                if 'filename=' in content_disposition:
                    filename = content_disposition.split('filename=')[1].strip('"')
                    print(f"📄 Downloaded filename: {filename}")
            else:
                print(f"❌ File download failed: {response.status}")
                error_text = await response.text()
                print(f"Error: {error_text}")
                return False

    print("\n🎉 All integration tests passed!")
    return True

async def main():
    print("🚀 Starting ModPorter AI Dashboard Integration Tests\n")
    print("=" * 60)
    
    try:
        success = await test_upload_and_conversion()
        if success:
            print("\n" + "=" * 60)
            print("✅ DASHBOARD INTEGRATION READY FOR FRONTEND TESTING")
            print("=" * 60)
        else:
            print("\n" + "=" * 60)
            print("❌ INTEGRATION TESTS FAILED")
            print("=" * 60)
    except Exception as e:
        print(f"\n❌ Test failed with exception: {str(e)}")
        print("=" * 60)

if __name__ == "__main__":
    asyncio.run(main())