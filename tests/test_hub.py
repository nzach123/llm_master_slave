import pytest
from unittest.mock import MagicMock, patch
from core.hub import Spine
from core.specs import AgentResult

@patch("core.hub.create_checkpoint")
def test_spine_run_mock_loop(mock_checkpoint):
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

def test_spine_retry_logic():
    """Test that dispatch_to_agent retries on failure using tenacity."""
    spine = Spine()
    
    mock_agent = MagicMock()
    # Fail once, then succeed
    mock_agent.side_effect = [Exception("Fail"), AgentResult(status="ok", message="Success", artifacts=[])]
    
    result = spine.dispatch_to_agent(mock_agent)
    
    assert result.status == "ok"
    assert mock_agent.call_count == 2
