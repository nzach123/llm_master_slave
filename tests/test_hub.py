import pytest
from unittest.mock import MagicMock, patch
from core.hub import Spine
from core.specs import DispatchStep, AgentResult

@patch("core.hub.create_checkpoint")
@patch("core.hub.GeminiClient")
def test_spine_run_mock_loop(mock_client_class, mock_checkpoint):
    """Test the mock loop runs and validates results."""
    spine = Spine()
    
    # Mocking dispatch_to_agent to avoid real network/retry latency in unit test
    with patch.object(spine, "dispatch_to_agent") as mock_dispatch:
        mock_dispatch.return_value = AgentResult(
            status="ok", 
            message="Mock success", 
            artifacts=[]
        )
        
        spine.run_mock_loop()
        
        # Verify checkpoint was called
        mock_checkpoint.assert_called_once_with("mock_task_001")
        # Verify dispatch was called
        mock_dispatch.assert_called_once()

@patch("core.hub.GeminiClient")
@patch("core.hub.create_checkpoint")
def test_spine_run_autonomous_loop(mock_checkpoint, mock_client_class):
    """Test the autonomous loop uses Planner and dispatches tasks."""
    spine = Spine()
    mock_client = mock_client_class.return_value
    mock_client.generate_plan.return_value = DispatchStep(
        agent_name="MockAgent",
        task_description="Generated Task",
        context={}
    )
    
    with patch.object(spine, "dispatch_to_agent") as mock_dispatch:
        mock_dispatch.return_value = AgentResult(
            status="ok", 
            message="Autonomous success", 
            artifacts=[]
        )
        
        spine.run_autonomous_loop("User Goal")
        
        # Verify checkpoint
        mock_checkpoint.assert_called()
        # Verify planner usage
        mock_client.generate_plan.assert_called_once_with("User Goal")
        # Verify dispatch
        mock_dispatch.assert_called_once()

@patch("core.hub.GeminiClient")
def test_spine_retry_logic(mock_client_class):
    """Test that dispatch_to_agent retries on failure using tenacity."""
    spine = Spine()
    
    mock_agent = MagicMock()
    # Fail once, then succeed
    mock_agent.side_effect = [Exception("Fail"), AgentResult(status="ok", message="Success", artifacts=[])]
    
    result = spine.dispatch_to_agent(mock_agent)
    
    assert result.status == "ok"
    assert mock_agent.call_count == 2
