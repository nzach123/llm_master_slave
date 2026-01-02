import pytest
from unittest.mock import MagicMock, patch
from core.hub import Spine
from core.specs import DispatchStep, AgentResult

@patch("core.hub.create_checkpoint")
@patch("tools.git_tools.get_current_branch")
@patch("core.hub.GeminiClient")
@patch("core.hub.run_pytest")
def test_autonomous_loop_includes_verification_steps(mock_run_pytest, mock_client_class, mock_get_branch, mock_checkpoint):
    """Test that manual verification steps are appended to the result message."""
    mock_get_branch.return_value = "main"
    mock_checkpoint.return_value = "task/abc"
    
    # Mock successful test run
    mock_test_result = MagicMock()
    mock_test_result.success = True
    mock_run_pytest.return_value = mock_test_result
    
    spine = Spine()
    mock_client = mock_client_class.return_value
    mock_client.generate_plan.return_value = DispatchStep(
        agent_name="coder",
        task_description="Implement add function",
        context={}
    )
    mock_client.generate_verification_steps.return_value = "**Manual Verification Steps:**\n1. Run it."
    
    with patch.object(spine, "dispatch_to_agent") as mock_dispatch:
        mock_dispatch.return_value = AgentResult(
            status="ok",
            message="Code implemented.",
            artifacts=[]
        )
        
        # Mock _parse_tool_calls to return nothing so we don't actually hit file system
        # Actually, we need success in execution_results to trigger tests and success
        with patch.object(spine, "_parse_tool_calls") as mock_parse:
            mock_parse.return_value = [] # But we need success
            
            # Since _parse_tool_calls is empty, execution_results["success"] will be empty.
            # I need to mock execution_results directly or make it succeed.
            with patch.object(spine, "_execute_tool_calls") as mock_execute:
                 mock_execute.return_value = {"success": ["Modified file"], "failed": []}
                 
                 result = spine.run_autonomous_loop("Add function", max_retries=1)
                 
                 assert result.status == "ok"
                 assert "Code implemented." in result.message
                 assert "**Manual Verification Steps:**" in result.message
                 mock_client.generate_verification_steps.assert_called_once()
