import pytest
from unittest.mock import MagicMock, patch, AsyncMock
import json
from core.hub import Spine
from core.specs import ResearcherOutput, DispatchStep, ProjectOverview, StructureMap, HardConstraints, SoftConstraints, KnownUnknowns, PlannerGuardrails, EvidenceIndex, FeasibilityCheck
from core.judge import JudgeResult

@pytest.mark.asyncio
@patch("core.hub.get_project_context")
@patch("core.hub.os.path.exists") 
@patch("core.hub.load_config")
@patch("core.hub.setup_logging")
@patch("core.hub.GeminiClient")
async def test_negotiation_flow(mock_planner_cls, mock_logging, mock_config, mock_exists, mock_get_context):
    # Setup mocks
    mock_config.return_value = {"OLLAMA_BASE_URL": "http://mock", "CODER_MODEL": "mock", "REVIEWER_MODEL": "mock"}
    
    # Mock Planner instance
    mock_planner = MagicMock()
    mock_planner_cls.return_value = mock_planner
    mock_get_context.return_value = "├── file1.py\n└── file2.py"
    mock_exists.return_value = False 
    
    spine = Spine()
    spine.planner.generate_plan.return_value = DispatchStep(agent="coder", task="Do something")
    
    # Mock the dispatch_to_agent to return a valid ResearcherOutput followed by JudgeResult
    mock_output = ResearcherOutput(
        project_overview=ProjectOverview(
            primary_language="Python",
            frameworks=["Flask"],
            runtime_targets=["Windows"],
            name="TestProject"
        ),
        structure_map=StructureMap(entry_points=[], core_modules=[]),
        hard_constraints=HardConstraints(framework_versions={}, external_interfaces=[], cannot_change=[]),
        soft_constraints=SoftConstraints(coding_patterns=[], style_conventions=[], existing_abstractions=[], tech_debt_notes=[]),
        known_unknowns=KnownUnknowns(missing_context=[], ambiguous_areas=[]),
        planner_guardrails=PlannerGuardrails(do_not_assume=[], requires_validation=[]),
        evidence_index=EvidenceIndex(files_examined=[], configs_examined=[], commands_run=[])
    )
    
    with patch.object(spine, "dispatch_to_agent", new_callable=AsyncMock) as mock_dispatch:
        mock_dispatch.side_effect = [
            mock_output, # Researcher
            JudgeResult(score=0.9, reasoning="good", decision="APPROVE") # Judge
        ]
        
        # Execute
        plan = await spine._negotiate_plan("User intent")
        
        # Verify
        assert mock_dispatch.called
        # Check that one of the calls was for researcher
        researcher_call = [call for call in mock_dispatch.call_args_list if call.args[0].agent == "researcher"][0]
        assert "Project Structure" in researcher_call.args[0].context_files[0]
        
        # Check that one of the calls was for judge
        judge_call = [call for call in mock_dispatch.call_args_list if call.args[0].agent == "judge"][0]
        assert "Evaluate" in judge_call.args[0].task
