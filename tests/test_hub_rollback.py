import pytest
from unittest.mock import MagicMock, patch
from core.hub import Spine
from core.specs import DispatchStep, AgentResult, SpokeResponse

@patch("core.hub.create_checkpoint")
@patch("tools.git_tools.get_current_branch")
@patch("tools.git_tools.rollback")
@patch("core.hub.GeminiClient")
def test_autonomous_loop_rollback_on_max_retries(mock_client_class, mock_rollback, mock_get_branch, mock_checkpoint):
    """Test that rollback is called when max retries are reached."""
    mock_get_branch.return_value = "main"
    mock_checkpoint.return_value = "task/abc"
    
    spine = Spine()
    mock_client = mock_client_class.return_value
    mock_client.generate_plan.return_value = DispatchStep(
        agent_name="coder",
        task_description="task",
        context_files=[]
    )
    
    # Mock dispatch to always return a failure (e.g., tool execution failed)
    with patch.object(spine, "dispatch_to_agent") as mock_dispatch:
        mock_dispatch.return_value = SpokeResponse(
            thoughts="some tool call which we will mock to fail in execute",
            tool_calls=[]
        )
        
        # Mock tool execution to always fail
        with patch.object(spine, "_execute_tool_calls") as mock_execute:
            mock_execute.return_value = {"success": [], "failed": ["Disk full"]}
            
            # Mock parse_tool_calls to return something so execute is called
            with patch.object(spine, "_parse_tool_calls") as mock_parse:
                from core.specs import ToolCall
                mock_parse.return_value = [ToolCall(action="write_file", path="test.py", content="content")]
                
                result = spine.run_autonomous_loop("Fail Me", max_retries=2)
                
                assert result.status == "error"
                # Negotiation dispatches to researcher before each coder dispatch
                assert mock_dispatch.call_count >= 2
                # Verify rollback was called with correct arguments
                mock_rollback.assert_called_once_with("main", "task/abc")

@patch("core.hub.create_checkpoint")
@patch("tools.git_tools.get_current_branch")
@patch("tools.git_tools.rollback")
@patch("core.hub.GeminiClient")
def test_autonomous_loop_rollback_on_exception(mock_client_class, mock_rollback, mock_get_branch, mock_checkpoint):
    """Test that rollback is called when a fatal exception occurs after retries."""
    mock_get_branch.return_value = "main"
    mock_checkpoint.return_value = "task/abc"
    
    spine = Spine()
    mock_client = mock_client_class.return_value
    
    # Mock generate_plan to raise exception
    mock_client.generate_plan.side_effect = Exception("System Crash")
    
    with pytest.raises(Exception) as excinfo:
        spine.run_autonomous_loop("Crash Me", max_retries=1)
        
    assert "System Crash" in str(excinfo.value)
    mock_rollback.assert_called_once_with("main", "task/abc")
