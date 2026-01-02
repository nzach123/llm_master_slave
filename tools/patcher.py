import os
import logging
import tempfile
from pathlib import Path

# Configure logging
logger = logging.getLogger(__name__)

def read_file(path: str) -> str:
    """
    Reads a file safely as UTF-8.

    Args:
        path: The path to the file to read.

    Returns:
        The content of the file as a string.

    Raises:
        FileNotFoundError: If the file does not exist.
        UnicodeDecodeError: If the file is not valid UTF-8.
    """
    try:
        return Path(path).read_text(encoding="utf-8")
    except FileNotFoundError:
        logger.error(f"File not found: {path}")
        raise
    except Exception as e:
        logger.error(f"Error reading file {path}: {e}")
        raise

def write_file(path: str, content: str) -> None:
    """
    Writes content to a file atomically.
    Creates parent directories if they do not exist.

    Args:
        path: The path to the file to write.
        content: The content to write.
    """
    target_path = Path(path)
    try:
        # Create parent directories
        target_path.parent.mkdir(parents=True, exist_ok=True)

        # Write to a temporary file in the same directory to ensure atomic move
        # Delete=False is required on Windows to close before rename
        with tempfile.NamedTemporaryFile("w", dir=target_path.parent, delete=False, encoding="utf-8") as tmp_file:
            tmp_file.write(content)
            tmp_path = tmp_file.name

        # Atomic replacement
        os.replace(tmp_path, target_path)
        logger.info(f"Successfully wrote to {path}")

    except Exception as e:
        logger.error(f"Error writing to file {path}: {e}")
        # Clean up temp file if it exists and wasn't moved
        if 'tmp_path' in locals() and os.path.exists(tmp_path):
            os.remove(tmp_path)
        raise
