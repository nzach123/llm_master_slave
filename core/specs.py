from pydantic import BaseModel
from typing import Dict, Any, List

class DispatchStep(BaseModel):
    agent_name: str
    task_description: str
    context: Dict[str, Any]

class AgentResult(BaseModel):
    status: str
    message: str
    artifacts: List[str]
