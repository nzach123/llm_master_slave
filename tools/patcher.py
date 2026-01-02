"""Patcher module for safe file I/O and atomic patching."""

import os
import logging
import tempfile
from pathlib import Path

# Configure logging
logger = logging.getLogger(__name__)

# Project root for path whitelisting (can be overridden via environment variable)
PROJECT_ROOT = Path(os.getenv("PATCHER_PROJECT_ROOT", os.getcwd())).resolve()


class PathSecurityError(Exception):
    """Raised when a file operation attempts to write outside the project directory."""
    pass


def validate_path(path: str) -> Path:
    """
    Validates that a path is within the project directory.
    """
    project_root = Path(os.getenv("PATCHER_PROJECT_ROOT", os.getcwd())).resolve()
    target_path = Path(path).resolve()
    
    # Check if the resolved path is within project_root
    try:
        target_path.relative_to(project_root)
    except ValueError:
        error_msg = (
            f"Security violation: Attempted to access path outside project directory. "
            f"Path: {target_path}, Project Root: {project_root}"
        )
        logger.error(error_msg)
        raise PathSecurityError(error_msg)
    
    return target_path

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
        logger.error("File not found: %s", path)
        raise
    except Exception as e:
        logger.error("Error reading file %s: %s", path, e)
        raise

def write_file(path: str, content: str) -> None:
    """
    Writes content to a file atomically.
    Creates parent directories if they do not exist.
    
    Security: Only allows writes within the project directory.

    Args:
        path: The path to the file to write.
        content: The content to write.
        
    Raises:
        PathSecurityError: If path is outside project directory
    """
    # Validate path is within project directory
    target_path = validate_path(path)
    try:
        # Create parent directories
        target_path.parent.mkdir(parents=True, exist_ok=True)

        # Write to a temporary file in the same directory to ensure atomic move
        # Delete=False is required on Windows to close before rename
        with tempfile.NamedTemporaryFile(
            "w",
            dir=target_path.parent,
            delete=False,
            encoding="utf-8"
        ) as tmp_file:
            tmp_file.write(content)
            tmp_path = tmp_file.name

        # Atomic replacement
        os.replace(tmp_path, target_path)
        logger.info("Successfully wrote to %s", path)

    except Exception as e:
        logger.error("Error writing to file %s: %s", path, e)
        # Clean up temp file if it exists and wasn't moved
        if 'tmp_path' in locals() and os.path.exists(tmp_path):
            os.remove(tmp_path)
        raise

def apply_patch(path: str, search_block: str, replace_block: str) -> bool:
    """
    Applies a patch to a file by replacing the first occurrence of search_block.
    Idempotent: returns True if replace_block is already present and search_block is missing.
    Returns False if search_block is not found.
    
    Security: Only allows patches within the project directory.

    Args:
        path: Path to the file.
        search_block: The exact string to find.
        replace_block: The string to replace it with.

    Returns:
        bool: True if patched or already patched, False otherwise.
        
    Raises:
        PathSecurityError: If path is outside project directory
    """
    # Validate path security before reading
    validate_path(path)
    content = read_file(path)

    # Idempotency check
    if replace_block in content and search_block not in content:
        logger.info("Patch already applied to %s", path)
        return True

    if search_block not in content:
        logger.warning("Search block not found in %s", path)
        return False

    # Perform replacement (first occurrence only)
    new_content = content.replace(search_block, replace_block, 1)

    # Write file atomically
    write_file(path, new_content)
    logger.info("Successfully applied patch to %s", path)
    return True
