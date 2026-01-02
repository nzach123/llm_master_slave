from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional, Literal

class DispatchStep(BaseModel):
    agent_name: str
    task_description: str
    context: Dict[str, Any]

class AgentResult(BaseModel):
    status: str
    message: str
    artifacts: List[str]

class ToolCall(BaseModel):
    """Represents a parsed tool call from LLM output."""
    action: Literal["write_file", "apply_patch"]
    path: str
    content: str
    old_content: Optional[str] = None  # Required for apply_patch

class KnowledgeSummary(BaseModel):
    relevant_files: List[str]
    technical_constraints: List[str]
    missing_information: List[str]
    feasibility_score: float

class FeasibilityCheck(BaseModel):
    summary: KnowledgeSummary
    message: str
