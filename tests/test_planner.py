import pytest
from unittest.mock import patch
from core.planner import GeminiClient

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
