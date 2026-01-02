import pytest
from core.planner import GeminiClient

def test_gemini_client_initialization():
    # This should fail because GeminiClient is not yet defined in core/planner.py
    client = GeminiClient()
    assert client is not None
