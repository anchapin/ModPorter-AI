"""
Configuration settings for the AI Engine.
"""

import os
from typing import Optional


class Config:
    """
    Configuration class for AI Engine settings.
    All settings can be overridden via environment variables.
    """
    
    # Database Configuration
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql://postgres:password@localhost:5432/modporter_ai")
    
    # OpenAI Configuration
    OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY")
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4")
    OPENAI_MAX_TOKENS: int = int(os.getenv("OPENAI_MAX_TOKENS", "2000"))
    OPENAI_TEMPERATURE: float = float(os.getenv("OPENAI_TEMPERATURE", "0.7"))
    
    # Vector DB Configuration
    VECTOR_DB_URL: str = os.getenv("VECTOR_DB_URL", "http://localhost:19530")
    VECTOR_DB_API_KEY: Optional[str] = os.getenv("VECTOR_DB_API_KEY", "your_vector_db_api_key")
    
    # AI Engine Configuration
    MOCK_AI_RESPONSES: bool = os.getenv("MOCK_AI_RESPONSES", "false").lower() == "true"
    BACKEND_API_URL: str = os.getenv("BACKEND_API_URL", "http://localhost:8000/api/v1") # Default for local backend
    
    # RAG Configuration
    RAG_EMBEDDING_MODEL: str = os.getenv("RAG_EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
    RAG_SIMILARITY_THRESHOLD: float = float(os.getenv("RAG_SIMILARITY_THRESHOLD", "0.7"))
    RAG_MAX_RESULTS: int = int(os.getenv("RAG_MAX_RESULTS", "10"))

    # Search Tool Fallback Configuration
    # Enable/disable fallback mechanism when primary search returns insufficient results
    SEARCH_FALLBACK_ENABLED: bool = os.getenv("SEARCH_FALLBACK_ENABLED", "true").lower() == "true"
    
    # Specifies which fallback tool to use (e.g., 'web_search_tool', 'api_search_tool')
    # The tool name should match the filename without extension in tools/
    FALLBACK_SEARCH_TOOL: str = os.getenv("FALLBACK_SEARCH_TOOL", "web_search_tool")
    
    # Redis Configuration
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379")
    
    # Logging Configuration
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
    
    # Performance Configuration
    MAX_WORKERS: int = int(os.getenv("MAX_WORKERS", "4"))
    TASK_TIMEOUT: int = int(os.getenv("TASK_TIMEOUT", "300"))  # 5 minutes
    
    # File Processing Configuration
    MAX_FILE_SIZE: int = int(os.getenv("MAX_FILE_SIZE", "100").replace("MB", ""))  # MB
    TEMP_DIR: str = os.getenv("TEMP_DIR", "/tmp/modporter")
    
    # Java Analysis Configuration
    JAVA_ANALYSIS_TIMEOUT: int = int(os.getenv("JAVA_ANALYSIS_TIMEOUT", "60"))  # seconds
    
    # Asset Processing Configuration
    MAX_TEXTURE_SIZE: int = int(os.getenv("MAX_TEXTURE_SIZE", "1024"))  # pixels
    SUPPORTED_FORMATS: list = ["png", "jpg", "jpeg", "ogg", "wav"]

    # Bedrock Scraper Configuration
    BEDROCK_SCRAPER_ENABLED: bool = os.getenv("BEDROCK_SCRAPER_ENABLED", "true").lower() == "true"
    BEDROCK_SCRAPER_RATE_LIMIT: float = float(os.getenv("BEDROCK_SCRAPER_RATE_LIMIT", "1.0")) # requests per second
    BEDROCK_DOCS_CACHE_TTL: int = int(os.getenv("BEDROCK_DOCS_CACHE_TTL", "86400")) # 24 hours
    
    # GPU Configuration
    GPU_TYPE: str = os.getenv("GPU_TYPE", "cpu").lower()  # nvidia, amd, cpu
    GPU_ENABLED: bool = os.getenv("GPU_ENABLED", "false").lower() == "true"
    MODEL_CACHE_SIZE: str = os.getenv("MODEL_CACHE_SIZE", "2GB")
    MAX_TOKENS_PER_REQUEST: int = int(os.getenv("MAX_TOKENS_PER_REQUEST", "4000"))