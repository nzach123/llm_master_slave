import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from core.hub import Spine
from core.specs import DispatchStep, AgentResult, SpokeResponse, ResearcherOutput, ProjectOverview, StructureMap, HardConstraints, SoftConstraints, KnownUnknowns, PlannerGuardrails, EvidenceIndex

@pytest.mark.asyncio
@patch("core.hub.create_checkpoint")
@patch("tools.git_tools.get_current_branch")
@patch("tools.git_tools.rollback")
@patch("core.hub.GeminiClient")
async def test_autonomous_loop_rollback_on_max_retries(mock_client_class, mock_rollback, mock_get_branch, mock_checkpoint):
    """Test that rollback is called when max retries are reached."""
    mock_get_branch.return_value = "main"
    mock_checkpoint.return_value = "task/abc"
    
    # Mock Spine dependencies to avoid real init
    with patch('core.hub.load_config', return_value={}), \
         patch('core.hub.setup_logging'):
        
        spine = Spine()
        mock_client = mock_client_class.return_value
        mock_client.generate_plan.return_value = DispatchStep(
            agent="coder",
            task="task",
            context_files=[]
        )
        
        # Mock researcher output for negotiation
        mock_researcher_output = ResearcherOutput(
            project_overview=ProjectOverview(name="test", primary_language="py", frameworks=[], runtime_targets=[], build_system=""),
            structure_map=StructureMap(entry_points=[], core_modules=[]),
            hard_constraints=HardConstraints(language_version="", framework_versions={}, external_interfaces=[], cannot_change=[]),
            soft_constraints=SoftConstraints(coding_patterns=[], style_conventions=[], existing_abstractions=[], tech_debt_notes=[]),
            known_unknowns=KnownUnknowns(missing_context=[], ambiguous_areas=[]),
            planner_guardrails=PlannerGuardrails(do_not_assume=[], requires_validation=[]),
            evidence_index=EvidenceIndex(files_examined=[], configs_examined=[], commands_run=[])
        )

        # Mock dispatch to always return a failure (e.g., tool execution failed)
        with patch.object(spine, "dispatch_to_agent", new_callable=AsyncMock) as mock_dispatch:
            # First call is negotiation (researcher), subsequent calls are coder
            mock_dispatch.side_effect = [
                mock_researcher_output, #Turn 1 Researcher
                MagicMock(score=0.9, reasoning="good", decision="APPROVE"), #Turn 1 Judge
                SpokeResponse(thoughts="fail", tool_calls=[]), # Attempt 1 Coder
                SpokeResponse(thoughts="fail", tool_calls=[]), # Attempt 2 Coder
            ]
            
            # Mock tool execution to always fail
            with patch.object(spine, "_execute_tool_calls") as mock_execute:
                mock_execute.return_value = {"success": [], "failed": ["Disk full"]}
                
                # Mock parse_tool_calls to return something so execute is called
                with patch.object(spine, "_parse_tool_calls") as mock_parse:
                    from core.specs import ToolCall
                    mock_parse.return_value = [ToolCall(action="write_file", path="test.py", content="content")]
                    
                    # Mock input to not block
                    with patch("asyncio.to_thread", side_effect=lambda f, *args, **kwargs: None if f == input else f(*args, **kwargs)):
                        result = await spine.run_autonomous_loop("Fail Me", max_retries=2)
                    
                        assert result.status == "error"
                        mock_rollback.assert_called_once_with("main", "task/abc")

@pytest.mark.asyncio
@patch("core.hub.create_checkpoint")
@patch("tools.git_tools.get_current_branch")
@patch("tools.git_tools.rollback")
@patch("core.hub.GeminiClient")
async def test_autonomous_loop_rollback_on_exception(mock_client_class, mock_rollback, mock_get_branch, mock_checkpoint):
    """Test that rollback is called when a fatal exception occurs after retries."""
    mock_get_branch.return_value = "main"
    mock_checkpoint.return_value = "task/abc"
    
    with patch('core.hub.load_config', return_value={}), \
         patch('core.hub.setup_logging'):
        spine = Spine()
        mock_client = mock_client_class.return_value
        
        # Mock negotiate_plan to raise exception or just generate_plan
        with patch.object(spine, "_negotiate_plan", side_effect=Exception("System Crash")):
            with pytest.raises(Exception) as excinfo:
                await spine.run_autonomous_loop("Crash Me", max_retries=1)
                
            assert "System Crash" in str(excinfo.value)
            mock_rollback.assert_called_once_with("main", "task/abc")
