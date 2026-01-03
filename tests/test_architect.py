import pytest
from unittest.mock import MagicMock, patch
from core.architect import Architect
from core.specs import ProjectBundle

@pytest.fixture
def mock_genai_client():
    with patch("core.architect.genai.Client") as mock:
        yield mock

def test_architect_initialization(mock_genai_client):
    """Test that Architect initializes correctly."""
    with patch("core.architect.load_config", return_value={"GEMINI_API_KEY": "fake_key"}):
        arch = Architect()
        assert arch.api_key == "fake_key"
        mock_genai_client.assert_called_once_with(api_key="fake_key")

def test_generate_project_bundle(mock_genai_client):
    """Test successful project bundle generation."""
    with patch("core.architect.load_config", return_value={"GEMINI_API_KEY": "fake_key"}):
        arch = Architect()

        # Mock file read
        with patch("builtins.open", new_callable=MagicMock) as mock_open:
            mock_open.return_value.__enter__.return_value.read.return_value = "- [ ] Project 1"

            # Mock Gemini response
            mock_response = MagicMock()
            mock_response.text = '''
            {
                "project_name": "Project Alpha",
                "high_level_intent": "Build alpha",
                "acceptance_criteria": ["It works"],
                "constraints": {"env": ["linux"]},
                "risk_notes": "None"
            }
            '''
            arch.client.models.generate_content.return_value = mock_response

            bundle = arch.generate_project_bundle()

            assert isinstance(bundle, ProjectBundle)
            assert bundle.project_name == "Project Alpha"
            assert bundle.acceptance_criteria == ["It works"]
