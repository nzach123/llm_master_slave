import os
import logging
from dotenv import load_dotenv

def load_config():
    """Load environment variables from .env file."""
    load_dotenv()
    return {
        "GEMINI_API_KEY": os.getenv("GEMINI_API_KEY"),
        "GEMINI_MODEL": os.getenv("GEMINI_MODEL", "gemini-2.0-flash"),
        "OLLAMA_BASE_URL": os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1"),
        "CODER_MODEL": os.getenv("CODER_MODEL", "qwen2.5-coder:7b"),
        "REVIEWER_MODEL": os.getenv("REVIEWER_MODEL", "phi3.5:latest"),
    }

def setup_logging(log_file="activity.log"):
    """Configure standard logging."""
    logger = logging.getLogger()
    # Remove existing handlers if any (useful for testing)
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
        
    logger.setLevel(logging.INFO)
    
    file_handler = logging.FileHandler(log_file)
    stream_handler = logging.StreamHandler()
    
    formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
    file_handler.setFormatter(formatter)
    stream_handler.setFormatter(formatter)
    
    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)

