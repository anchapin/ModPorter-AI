#!/usr/bin/env python3
"""Test if version compatibility health endpoint works"""

import sys
from pathlib import Path
import httpx

# Add src to path
src_dir = Path(__file__).parent / "src"
sys.path.insert(0, str(src_dir))

from main import app

async def test_health():
    """Test health endpoint"""
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/v1/version-compatibility/health/")
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
        
        # Test entries endpoint
        entries_response = await client.get("/api/v1/version-compatibility/entries/")
        print(f"Entries Status: {entries_response.status_code}")
        print(f"Entries Response: {entries_response.json()}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_health())
