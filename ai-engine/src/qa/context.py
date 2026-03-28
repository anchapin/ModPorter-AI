from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime
from pathlib import Path


class QAContext(BaseModel):
    job_id: str
    job_dir: Path
    source_java_path: Path
    output_bedrock_path: Path
    metadata: Dict[str, Any] = {}
    validation_results: Dict[str, Any] = {}
    created_at: datetime = Field(default_factory=datetime.now)
    current_agent: Optional[str] = None
