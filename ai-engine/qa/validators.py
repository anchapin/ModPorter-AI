from typing import Any, Dict, List

from pydantic import BaseModel


class AgentOutput(BaseModel):
    agent_name: str
    success: bool
    result: Dict[str, Any]
    errors: List[str] = []
    execution_time_ms: int


def validate_agent_output(data: Dict[str, Any]) -> AgentOutput:
    return AgentOutput(**data)
