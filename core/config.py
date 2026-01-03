import os
import logging
import getpass
from dotenv import load_dotenv

def load_config():
    """Load environment variables from .env file."""
    load_dotenv()

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("GEMINI_API_KEY not found in environment or .env file.")
        api_key = getpass.getpass("Please enter your Gemini API Key: ")
        os.environ["GEMINI_API_KEY"] = api_key # Set it for the current process

    return {
        "GEMINI_API_KEY": api_key,
        "GEMINI_MODEL": os.getenv("GEMINI_MODEL", "gemini-2.0-flash"),
        "OLLAMA_BASE_URL": os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
        "CODER_MODEL": os.getenv("CODER_MODEL", "qwen2.5-coder:7b"),
        "REVIEWER_MODEL": os.getenv("REVIEWER_MODEL", "phi3.5:latest"),
        "JUDGE_MODEL": os.getenv("JUDGE_MODEL", "phi3.5:latest"),
    }

def setup_logging(log_file="activity.log"):
    """Configure standard logging."""
    # Try to enable ANSI support for Windows
    try:
        from tools.cli_utils import enable_ansi_support
        enable_ansi_support()
    except ImportError:
        pass

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
