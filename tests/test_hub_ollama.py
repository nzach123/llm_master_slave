import pytest
import tenacity
from unittest.mock import patch, MagicMock
from core.hub import Spine
from core.specs import DispatchStep, AgentResult

@pytest.fixture
def spine():
    with patch('core.hub.load_config') as mock_config:
        mock_config.return_value = {
            "GEMINI_API_KEY": "test",
            "OLLAMA_BASE_URL": "http://localhost:11434/v1",
            "CODER_MODEL": "qwen2.5-coder:7b",
            "REVIEWER_MODEL": "phi3.5:latest"
        }
        # Mock GeminiClient initialization to avoid API key check
        with patch('core.hub.GeminiClient'):
            return Spine()

@patch('core.hub.wait_for_resources')
@patch('core.spokes.CoderSpoke.handle_task')
def test_spine_dispatch_to_coder_success(mock_handle, mock_wait, spine):
    mock_wait.return_value = True
    mock_handle.return_value = AgentResult(status="ok", message="code", artifacts=[])
    
    step = DispatchStep(agent_name="coder", task_description="task", context={})
    result = spine.dispatch_to_agent(step)
    
    assert result.status == "ok"
    assert mock_handle.called
    assert mock_wait.called

@patch('core.hub.wait_for_resources')
def test_spine_dispatch_resource_fail(mock_wait, spine):
    # Simulate timeout returning False
    mock_wait.return_value = False
    
    step = DispatchStep(agent_name="coder", task_description="task", context={})
    
    # Tenacity might reraise the original error if configured or if it's a fatal one
    with pytest.raises(RuntimeError, match="System resources below threshold"):
        spine.dispatch_to_agent(step)

@patch('core.hub.wait_for_resources')
def test_spine_dispatch_unknown_agent(mock_wait, spine):
    mock_wait.return_value = True
    step = DispatchStep(agent_name="unknown", task_description="task", context={})
    
    # ValueError is not typically retried, but let's see how tenacity behaves
    with pytest.raises(ValueError, match="Unknown agent: unknown"):
        spine.dispatch_to_agent(step)
