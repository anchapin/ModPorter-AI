from pydantic import BaseModel

class CacheStats(BaseModel):
    hits: int = 0
    misses: int = 0
    current_items: int = 0
    total_size_bytes: int = 0 # Represents size in bytes
