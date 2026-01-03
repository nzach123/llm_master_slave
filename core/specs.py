from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional, Literal

class DispatchStep(BaseModel):
    agent: str = Field(..., alias="agent_name") # Support both for backward compat if needed, or strict per spec
    task: str = Field(..., alias="task_description")
    context_files: List[str] = Field(default_factory=list, alias="context")

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

class ClassificationJustification(BaseModel):
    """Justification for a classification decision (for traceability)."""
    item: str
    classification: str
    reason: str
    confidence: Optional[float] = None


class SpokeResponse(BaseModel):
    """The strict JSON output expected from a Coder/Spoke."""
    thoughts: str
    tool_calls: List[ToolCall]
    justifications: Optional[List[ClassificationJustification]] = None

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

class ProjectOverview(BaseModel):
    name: Optional[str] = None
    primary_language: str
    frameworks: List[str]
    runtime_targets: List[str]
    build_system: Optional[str] = None

class EntryPoint(BaseModel):
    path: str
    type: Literal["file", "script", "service"]
    notes: str

class CoreModule(BaseModel):
    path: str
    responsibility: str
    dependencies: List[str]

class StructureMap(BaseModel):
    entry_points: List[EntryPoint]
    core_modules: List[CoreModule]

class ExternalInterface(BaseModel):
    type: Literal["API", "CLI", "file", "network"]
    description: str
    location: str

class HardConstraints(BaseModel):
    language_version: Optional[str] = None
    framework_versions: Dict[str, str]
    external_interfaces: List[ExternalInterface]
    cannot_change: List[str]

class SoftConstraints(BaseModel):
    coding_patterns: List[str]
    style_conventions: List[str]
    existing_abstractions: List[str]
    tech_debt_notes: List[str]

class MissingContext(BaseModel):
    description: str
    blocking: bool

class AmbiguousArea(BaseModel):
    path: str
    why_unclear: str

class KnownUnknowns(BaseModel):
    missing_context: List[MissingContext]
    ambiguous_areas: List[AmbiguousArea]

class PlannerGuardrails(BaseModel):
    do_not_assume: List[str]
    requires_validation: List[Dict[str, str]] # {"decision": "...", "needs": "..."}

class EvidenceIndex(BaseModel):
    files_examined: List[str]
    configs_examined: List[str]
    commands_run: List[str]

class ResearcherOutput(BaseModel):
    """Strict schema for Researcher Spoke output."""
    project_overview: ProjectOverview
    structure_map: StructureMap
    hard_constraints: HardConstraints
    soft_constraints: SoftConstraints
    known_unknowns: KnownUnknowns
    planner_guardrails: PlannerGuardrails
    evidence_index: EvidenceIndex

class KnowledgeSummary(BaseModel):
    # DEPRECATED: Kept for backward compatibility if needed, but ResearcherOutput is preferred
    relevant_files: List[str]
    technical_constraints: List[str]
    missing_information: List[str]
    feasibility_score: float

class FeasibilityCheck(BaseModel):
    summary: ResearcherOutput
    message: str
