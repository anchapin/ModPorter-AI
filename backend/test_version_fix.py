#!/usr/bin/env python3
"""Test version compatibility fix"""

import sys
from pathlib import Path
import httpx
import asyncio

# Add src to path
src_dir = Path(__file__).parent / "src"
sys.path.insert(0, str(src_dir))

from main import app

async def test_create_entry():
    """Test creating a compatibility entry"""
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        # Test create
        compatibility_data = {
            "source_version": "1.18.2",
            "target_version": "1.19.2",
            "compatibility_score": 0.85,
            "conversion_complexity": "medium",
        }
        
        response = await client.post("/api/v1/version-compatibility/entries/", json=compatibility_data)
        print(f"Create Status: {response.status_code}")
        
        if response.status_code == 201:
            data = response.json()
            print(f"Created entry ID: {data.get('id')}")
            print(f"Full response: {data}")
            
            # Test get
            entry_id = data.get('id')
            if entry_id:
                get_response = await client.get(f"/api/v1/version-compatibility/entries/{entry_id}")
                print(f"Get Status: {get_response.status_code}")
                print(f"Get Response: {get_response.json()}")
                
                # Test update
                update_data = {"compatibility_score": 0.9}
                update_response = await client.put(f"/api/v1/version-compatibility/entries/{entry_id}", json=update_data)
                print(f"Update Status: {update_response.status_code}")
                print(f"Update Response: {update_response.json()}")
                
                # Test delete
                delete_response = await client.delete(f"/api/v1/version-compatibility/entries/{entry_id}")
                print(f"Delete Status: {delete_response.status_code}")
                
            # Test batch import
            batch_data = {
                "entries": [
                    {
                        "source_version": "1.15.2",
                        "target_version": "1.16.5",
                        "compatibility_score": 0.65,
                        "conversion_complexity": "medium"
                    }
                ],
                "import_options": {
                    "validate_data": True,
                    "overwrite_existing": False,
                    "create_migration_guides": True
                }
            }
            
            batch_response = await client.post("/api/v1/version-compatibility/batch-import/", json=batch_data)
            print(f"Batch Import Status: {batch_response.status_code}")
            print(f"Batch Import Response: {batch_response.json()}")
        else:
            print(f"Error: {response.text}")

if __name__ == "__main__":
    asyncio.run(test_create_entry())
