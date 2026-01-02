import os
import logging
from core.config import setup_logging, load_config

def test_load_config(tmp_path):
    """Test loading environment variables."""
    env_file = tmp_path / ".env"
    env_file.write_text("GEMINI_API_KEY=test_key")
    
    # Manually set env var to simulate dotenv loading
    os.environ["GEMINI_API_KEY"] = "test_key"
    config = load_config()
    assert config["GEMINI_API_KEY"] == "test_key"

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
