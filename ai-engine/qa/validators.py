from pydantic import BaseModel, ValidationError
from typing import Dict, Any, List


class AgentOutput(BaseModel):
    agent_name: str
    success: bool
    result: Dict[str, Any]
    errors: List[str] = []
    execution_time_ms: int


def validate_agent_output(data: Dict[str, Any]) -> AgentOutput:
    return AgentOutput(**data)
