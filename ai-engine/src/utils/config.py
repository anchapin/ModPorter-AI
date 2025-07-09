"""
Configuration management for AI Engine
"""

import os
from typing import Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class Config:
    """Configuration management"""
    
    # OpenAI Configuration
    OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY")
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4")
    OPENAI_RPM_LIMIT: int = int(os.getenv("OPENAI_RPM_LIMIT", "50"))
    OPENAI_TPM_LIMIT: int = int(os.getenv("OPENAI_TPM_LIMIT", "40000"))
    OPENAI_MAX_RETRIES: int = int(os.getenv("OPENAI_MAX_RETRIES", "3"))

    # Vector DB Configuration
    VECTOR_DB_URL: str = os.getenv("VECTOR_DB_URL", "http://localhost:19530")
    VECTOR_DB_API_KEY: Optional[str] = os.getenv("VECTOR_DB_API_KEY", "your_vector_db_api_key")
    
    # AI Engine Configuration
    MOCK_AI_RESPONSES: bool = os.getenv("MOCK_AI_RESPONSES", "false").lower() == "true"
    
    # Redis Configuration
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379")
    
    # Logging Configuration
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
    
    # Performance Configuration
    MAX_CONVERSION_TIME: int = int(os.getenv("MAX_CONVERSION_TIME", "600"))
    
    @classmethod
    def is_openai_available(cls) -> bool:
        """Check if OpenAI API is available"""
        return cls.OPENAI_API_KEY is not None and cls.OPENAI_API_KEY != ""
    
    @classmethod
    def get_rate_limit_config(cls) -> dict:
        """Get rate limiting configuration"""
        return {
            "requests_per_minute": cls.OPENAI_RPM_LIMIT,
            "tokens_per_minute": cls.OPENAI_TPM_LIMIT,
            "max_retries": cls.OPENAI_MAX_RETRIES
        }