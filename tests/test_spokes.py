import pytest
import httpx
from unittest.mock import patch, MagicMock
from core.spokes import CoderSpoke, ReviewerSpoke, BaseSpoke
from core.specs import DispatchStep, AgentResult

@pytest.fixture
def mock_config():
    return {
        "OLLAMA_BASE_URL": "http://localhost:11434/v1",
        "CODER_MODEL": "qwen2.5-coder:7b",
        "REVIEWER_MODEL": "phi3.5:latest"
    }

def test_coder_spoke_generate_prompt():
    coder = CoderSpoke("http://localhost:11434/v1", "qwen2.5-coder:7b")
    step = DispatchStep(
        agent_name="coder",
        task_description="Write a python script",
        context={"files": {"main.py": "print('hello')"}}
    )
    prompt = coder.build_prompt(step)
    assert "Write a python script" in prompt
    assert "main.py" in prompt
    assert "print('hello')" in prompt

@patch("httpx.Client.post")
def test_coder_spoke_handle_task_success(mock_post):
    mock_post.return_value = MagicMock(
        status_code=200,
        json=lambda: {
            "choices": [{"message": {"content": "```python\nprint('hello')\n```"}}]
        }
    )
    
    coder = CoderSpoke("http://localhost:11434/v1", "qwen2.5-coder:7b")
    step = DispatchStep(
        agent_name="coder",
        task_description="Write python",
        context={}
    )
    
    result = coder.handle_task(step)
    assert result.status == "ok"
    assert "print('hello')" in result.message
    assert mock_post.called

@patch("httpx.Client.post")
def test_spoke_ollama_connection_error(mock_post):
    mock_post.side_effect = httpx.ConnectError("Ollama down")
    
    coder = CoderSpoke("http://localhost:11434/v1", "qwen2.5-coder:7b")
    step = DispatchStep(agent_name="coder", task_description="task", context={})
    
    with pytest.raises(httpx.ConnectError):
        coder.handle_task(step)
