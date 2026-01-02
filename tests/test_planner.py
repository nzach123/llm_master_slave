import pytest
from unittest.mock import patch
from core.planner import GeminiClient
from core.specs import DispatchStep
import json

def test_gemini_client_initialization_success():
    """Test successful initialization when API key is present."""
    with patch("core.planner.load_config") as mock_load:
        with patch("google.generativeai.configure") as mock_configure:
            mock_load.return_value = {"GEMINI_API_KEY": "test_key"}
            client = GeminiClient()
            assert client.api_key == "test_key"
            mock_configure.assert_called_once_with(api_key="test_key")

def test_gemini_client_initialization_failure():
    """Test failure when API key is missing."""
    with patch("core.planner.load_config") as mock_load:
        mock_load.return_value = {"GEMINI_API_KEY": None}
        with pytest.raises(ValueError, match="GEMINI_API_KEY not found in configuration"):
            GeminiClient()

def test_generate_plan_success():
    """Test successful plan generation with valid JSON response."""
    with patch("core.planner.load_config") as mock_load:
        with patch("google.generativeai.configure"):
            mock_load.return_value = {"GEMINI_API_KEY": "test_key"}
            client = GeminiClient()
            
            mock_response = patch("google.generativeai.GenerativeModel.generate_content")
            with mock_response as mock_gen:
                mock_gen.return_value.text = json.dumps({
                    "agent_name": "coder",
                    "task_description": "Write a function",
                    "context": {"file": "main.py"}
                })
                
                plan = client.generate_plan("Write a function in main.py")
                assert isinstance(plan, DispatchStep)
                assert plan.agent_name == "coder"
                assert plan.task_description == "Write a function"

def test_generate_plan_invalid_json():
    """Test failure when API returns invalid JSON."""
    with patch("core.planner.load_config") as mock_load:
        with patch("google.generativeai.configure"):
            mock_load.return_value = {"GEMINI_API_KEY": "test_key"}
            client = GeminiClient()
            
            mock_response = patch("google.generativeai.GenerativeModel.generate_content")
            with mock_response as mock_gen:
                mock_gen.return_value.text = "invalid json"
                
                with pytest.raises(ValueError, match="Failed to parse JSON response"):
                    client.generate_plan("intent")
