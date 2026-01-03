import pytest
import httpx
import json
from unittest.mock import patch, MagicMock
from core.spokes import CoderSpoke, ReviewerSpoke, ResearcherSpoke
from core.specs import DispatchStep, SpokeResponse, ReviewResult, ResearcherOutput

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
    """Test ResearcherSpoke returns ResearcherOutput."""
    researcher = ResearcherSpoke("http://mock", "model")
    assert researcher.response_model == ResearcherOutput

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
    # Create a valid ResearcherOutput JSON structure
    valid_output = {
        "project_overview": {
            "name": "Test Project",
            "primary_language": "Python",
            "frameworks": ["Django"],
            "runtime_targets": ["Linux"],
            "build_system": "Poetry"
        },
        "structure_map": {
            "entry_points": [],
            "core_modules": []
        },
        "hard_constraints": {
            "language_version": "3.12",
            "framework_versions": {},
            "external_interfaces": [],
            "cannot_change": []
        },
        "soft_constraints": {
            "coding_patterns": [],
            "style_conventions": [],
            "existing_abstractions": [],
            "tech_debt_notes": []
        },
        "known_unknowns": {
            "missing_context": [],
            "ambiguous_areas": []
        },
        "planner_guardrails": {
            "do_not_assume": [],
            "requires_validation": []
        },
        "evidence_index": {
            "files_examined": [],
            "configs_examined": [],
            "commands_run": []
        }
    }

    mock_post.return_value = MagicMock(
        status_code=200,
        json=lambda: {
            "message": {"content": json.dumps(valid_output)}
        }
    )
    
    researcher = ResearcherSpoke("http://mock", "model")
    step = DispatchStep(agent="researcher", task="research", context_files=[])
    result = researcher.handle_task(step)
    
    assert isinstance(result, ResearcherOutput)
    assert result.project_overview.name == "Test Project"
