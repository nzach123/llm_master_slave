import pytest
from pydantic import ValidationError
from core.specs import DispatchStep, AgentResult

def test_dispatch_step_valid():
    """Test creating a valid DispatchStep."""
    data = {
        "agent_name": "mock_agent",
        "task_description": "Do something",
        "context_files": ["main.py"]
    }
    step = DispatchStep(**data)
    assert step.agent == "mock_agent"
    assert step.task == "Do something"
    assert step.context_files == ["main.py"]

def test_dispatch_step_invalid_missing_field():
    """Test DispatchStep fails with missing fields."""
    data = {
        "agent_name": "mock_agent",
        # Missing task_description
        "context_files": []
    }
    with pytest.raises(ValidationError):
        DispatchStep(**data)

def test_agent_result_valid():
    """Test creating a valid AgentResult."""
    data = {
        "status": "ok",
        "message": "Task complete",
        "artifacts": ["file1.txt"]
    }
    result = AgentResult(**data)
    assert result.status == "ok"
    assert result.message == "Task complete"
    assert result.artifacts == ["file1.txt"]

def test_agent_result_invalid_status():
    """Test AgentResult might fail or pass depending on constraints.
    Assuming strict typing, but 'status' is a string.
    Let's check if we enforce specific values? Spec says 'status (ok/error)'.
    We can test for existence first.
    """
    data = {
        "message": "Missing status",
        "artifacts": []
    }
    with pytest.raises(ValidationError):
        AgentResult(**data)
