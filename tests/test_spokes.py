import pytest
import httpx
from unittest.mock import patch, MagicMock
from core.spokes import CoderSpoke, ReviewerSpoke, ResearcherSpoke
from core.specs import DispatchStep, SpokeResponse, ReviewResult, KnowledgeSummary

@pytest.fixture
def mock_config():
    return {
        "OLLAMA_BASE_URL": "http://localhost:11434/api",
        "CODER_MODEL": "qwen2.5-coder:7b",
        "REVIEWER_MODEL": "phi3.5:latest"
    }

def test_coder_spoke_response():
    """Test CoderSpoke returns SpokeResponse."""
    coder = CoderSpoke("http://mock", "model")
    assert coder.response_model == SpokeResponse

def test_reviewer_spoke_response():
    """Test ReviewerSpoke returns ReviewResult."""
    reviewer = ReviewerSpoke("http://mock", "model")
    assert reviewer.response_model == ReviewResult

def test_researcher_spoke_response():
    """Test ResearcherSpoke returns KnowledgeSummary."""
    researcher = ResearcherSpoke("http://mock", "model")
    assert researcher.response_model == KnowledgeSummary

@patch("httpx.Client.post")
def test_coder_handle_task(mock_post):
    """Test Coder execution flow."""
    mock_post.return_value = MagicMock(
        status_code=200,
        json=lambda: {
            "message": {"content": '{"thoughts": "ok", "tool_calls": []}'}
        }
    )
    
    coder = CoderSpoke("http://mock", "model")
    step = DispatchStep(agent="coder", task="task", context_files=[])
    result = coder.handle_task(step)

    assert isinstance(result, SpokeResponse)
    assert result.thoughts == "ok"

@patch("httpx.Client.post")
def test_reviewer_handle_task(mock_post):
    """Test Reviewer execution flow."""
    mock_post.return_value = MagicMock(
        status_code=200,
        json=lambda: {
            "message": {"content": '{"approved": true, "comments": ["good"]}'}
        }
    )
    
    reviewer = ReviewerSpoke("http://mock", "model")
    step = DispatchStep(agent="reviewer", task="review", context_files=[])
    result = reviewer.handle_task(step)

    assert isinstance(result, ReviewResult)
    assert result.approved is True
    assert result.comments == ["good"]

@patch("httpx.Client.post")
def test_researcher_handle_task(mock_post):
    """Test Researcher execution flow."""
    mock_post.return_value = MagicMock(
        status_code=200,
        json=lambda: {
            "message": {"content": '{"relevant_files": ["a.py"], "technical_constraints": [], "missing_information": [], "feasibility_score": 0.9}'}
        }
    )
    
    researcher = ResearcherSpoke("http://mock", "model")
    step = DispatchStep(agent="researcher", task="research", context_files=[])
    result = researcher.handle_task(step)
    
    assert isinstance(result, KnowledgeSummary)
    assert result.relevant_files == ["a.py"]
