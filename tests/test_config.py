import os
import logging
from core.config import setup_logging, load_config

def test_load_config(tmp_path):
    """Test loading environment variables."""
    # Mock environment variables
    os.environ["GEMINI_API_KEY"] = "test_key"
    os.environ["OLLAMA_BASE_URL"] = "http://test-ollama:11434/v1"
    os.environ["CODER_MODEL"] = "test-coder"
    os.environ["REVIEWER_MODEL"] = "test-reviewer"
    
    config = load_config()
    assert config["GEMINI_API_KEY"] == "test_key"
    assert config["OLLAMA_BASE_URL"] == "http://test-ollama:11434/v1"
    assert config["CODER_MODEL"] == "test-coder"
    assert config["REVIEWER_MODEL"] == "test-reviewer"

def test_load_config_defaults(tmp_path):
    """Test loading configuration with default values."""
    # Clear environment variables
    if "OLLAMA_BASE_URL" in os.environ: del os.environ["OLLAMA_BASE_URL"]
    if "CODER_MODEL" in os.environ: del os.environ["CODER_MODEL"]
    if "REVIEWER_MODEL" in os.environ: del os.environ["REVIEWER_MODEL"]
    
    config = load_config()
    assert config["OLLAMA_BASE_URL"] == "http://localhost:11434"
    assert config["CODER_MODEL"] == "qwen2.5-coder:7b"
    assert config["REVIEWER_MODEL"] == "phi3.5:latest"

def test_setup_logging(tmp_path):
    """Test logging setup creates a file."""
    log_file = tmp_path / "activity.log"
    setup_logging(str(log_file))
    
    logger = logging.getLogger()
    logger.info("Test log message")
    
    # Force flush handlers
    for handler in logger.handlers:
        handler.flush()
        
    assert log_file.exists()
    assert "Test log message" in log_file.read_text()
