from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional, Literal

class DispatchStep(BaseModel):
    agent: str = Field(..., alias="agent_name") # Support both for backward compat if needed, or strict per spec
    task: str = Field(..., alias="task_description")
    context_files: List[str]

    class Config:
        populate_by_name = True

class ToolCall(BaseModel):
    """Represents a structured tool call from the Spoke."""
    action: Literal["write_file", "apply_patch", "run_command", "read_file"]
    path: str
    content: Optional[str] = None # content for write_file
    search: Optional[str] = None # search block for apply_patch
    replace: Optional[str] = None # replace block for apply_patch
    command: Optional[str] = None # command for run_command

class SpokeResponse(BaseModel):
    """The strict JSON output expected from a Coder/Spoke."""
    thoughts: str
    tool_calls: List[ToolCall]

class ReviewResult(BaseModel):
    """Output from the Reviewer agent."""
    approved: bool
    comments: List[str]

class JudgeDecision(BaseModel):
    """Output from the Judge agent."""
    safe: bool
    reason: str

# Legacy / Other models
class AgentResult(BaseModel):
    status: str
    message: str
    artifacts: List[str]

class KnowledgeSummary(BaseModel):
    relevant_files: List[str]
    technical_constraints: List[str]
    missing_information: List[str]
    feasibility_score: float

class FeasibilityCheck(BaseModel):
    summary: KnowledgeSummary
    message: str
