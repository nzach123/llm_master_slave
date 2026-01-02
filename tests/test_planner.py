import pytest
from unittest.mock import patch, MagicMock
from core.planner import GeminiClient
from core.specs import DispatchStep
import json

def test_gemini_client_initialization_success():
    """Test successful initialization when API key is present."""
    with patch("core.planner.load_config") as mock_load:
        with patch("google.genai.Client") as mock_client:
            mock_load.return_value = {"GEMINI_API_KEY": "test_key", "GEMINI_MODEL": "gemini-2.0-flash"}
            client = GeminiClient()
            assert client.api_key == "test_key"
            # Verify client was initialized with the key
            mock_client.assert_called_once_with(api_key="test_key")

def test_gemini_client_initialization_failure():
    """Test failure when API key is missing."""
    with patch("core.planner.load_config") as mock_load:
        mock_load.return_value = {"GEMINI_API_KEY": None}
        with pytest.raises(ValueError, match="GEMINI_API_KEY not found in configuration"):
            GeminiClient()

def test_generate_plan_success():
    """Test successful plan generation with valid JSON response."""
    with patch("core.planner.load_config") as mock_load:
        with patch("google.genai.Client") as mock_client_cls:
            mock_load.return_value = {"GEMINI_API_KEY": "test_key", "GEMINI_MODEL": "gemini-2.0-flash"}

            # Setup mock client instance
            mock_client_instance = MagicMock()
            mock_client_cls.return_value = mock_client_instance

            # Setup response
            mock_response = MagicMock()
            mock_response.text = json.dumps({
                "agent_name": "coder",
                "task_description": "Write a function",
                "context": {"file": "main.py"}
            })
            mock_client_instance.models.generate_content.return_value = mock_response

            client = GeminiClient()
            plan = client.generate_plan("Write a function in main.py")

            assert isinstance(plan, DispatchStep)
            assert plan.agent_name == "coder"
            mock_client_instance.models.generate_content.assert_called_once()
            args, kwargs = mock_client_instance.models.generate_content.call_args
            assert kwargs["model"] == "gemini-2.0-flash"
            assert kwargs["contents"] == "Write a function in main.py"
            # Just verify that system_instruction is present and not empty
            assert kwargs["config"].system_instruction

def test_generate_plan_invalid_json():
    """Test failure when API returns invalid JSON."""
    with patch("core.planner.load_config") as mock_load:
         with patch("google.genai.Client") as mock_client_cls:
            mock_load.return_value = {"GEMINI_API_KEY": "test_key"}

            mock_client_instance = MagicMock()
            mock_client_cls.return_value = mock_client_instance

            mock_response = MagicMock()
            mock_response.text = "invalid json"
            mock_client_instance.models.generate_content.return_value = mock_response

            client = GeminiClient()
            with pytest.raises(ValueError, match="Failed to parse JSON response"):
                client.generate_plan("intent")
