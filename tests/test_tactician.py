import pytest
from unittest.mock import MagicMock, patch
from core.tactician import Tactician
from core.specs import DispatchStep, FeasibilityCheck, ResearcherOutput

@pytest.fixture
def mock_genai_client():
    with patch("core.tactician.genai.Client") as mock:
        yield mock

def test_tactician_initialization(mock_genai_client):
    """Test that Tactician initializes correctly with API key."""
    with patch("core.tactician.load_config", return_value={"GEMINI_API_KEY": "fake_key"}):
        planner = Tactician()
        assert planner.api_key == "fake_key"
        mock_genai_client.assert_called_once_with(api_key="fake_key")

def test_generate_plan_success(mock_genai_client):
    """Test successful plan generation."""
    with patch("core.tactician.load_config", return_value={"GEMINI_API_KEY": "fake_key"}):
        planner = Tactician()

        # Mock the response
        mock_response = MagicMock()
        mock_response.text = '{"agent_name": "coder", "task_description": "Fix bug", "context": []}'
        planner.client.models.generate_content.return_value = mock_response

        step = planner.generate_plan("Fix the bug in main.py")

        assert isinstance(step, DispatchStep)
        assert step.agent == "coder"
        assert step.task == "Fix bug"

def test_generate_plan_json_cleanup(mock_genai_client):
    """Test that markdown code blocks are stripped from JSON."""
    with patch("core.tactician.load_config", return_value={"GEMINI_API_KEY": "fake_key"}):
        planner = Tactician()

        mock_response = MagicMock()
        mock_response.text = '```json\n{"agent_name": "coder", "task_description": "test", "context": []}\n```'
        planner.client.models.generate_content.return_value = mock_response

        step = planner.generate_plan("test")
        assert step.task == "test"

def test_refine_plan(mock_genai_client):
    """Test plan refinement based on feedback."""
    with patch("core.tactician.load_config", return_value={"GEMINI_API_KEY": "fake_key"}):
        planner = Tactician()

        original_step = DispatchStep(agent_name="coder", task_description="Do X", context=[])

        # Create a mock FeasibilityCheck with a proper ResearcherOutput summary
        mock_summary = MagicMock(spec=ResearcherOutput)
        mock_summary.relevant_files = ["a.py"]
        mock_summary.technical_constraints = ["no libraries"]
        mock_summary.missing_information = []

        feedback = FeasibilityCheck(
            summary=mock_summary,
            message="Needs update"
        )

        mock_response = MagicMock()
        mock_response.text = '{"agent_name": "coder", "task_description": "Do X with constraint", "context": []}'
        planner.client.models.generate_content.return_value = mock_response

        new_step = planner.refine_plan(original_step, feedback)
        assert new_step.task == "Do X with constraint"
