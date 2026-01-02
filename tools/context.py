"""
Context gathering utilities for the Hub-and-Spoke system.

Generates token-efficient representations of the project state to inject
into the Planner's context.
"""

import os
from pathlib import Path
from typing import List, Set


# Directories and patterns to ignore
IGNORE_DIRS: Set[str] = {
    '.git', '.venv', '__pycache__', 'node_modules', 
    '.pytest_cache', 'venv', 'env', '.coverage',
    '.mypy_cache', '.tox', 'dist', 'build', '*.egg-info'
}

IGNORE_EXTENSIONS: Set[str] = {
    '.pyc', '.pyo', '.pyd', '.so', '.dll', '.dylib',
    '.log', '.sqlite', '.db'
}


def should_ignore(path: Path) -> bool:
    """Check if a path should be ignored based on filters."""
    # Check if any parent directory is in ignore list
    for part in path.parts:
        if part in IGNORE_DIRS or part.startswith('.'):
            return True
    
    # Check file extension
    if path.suffix in IGNORE_EXTENSIONS:
        return True
    
    return False


def get_file_size_str(size_bytes: int) -> str:
    """Convert bytes to human-readable format."""
    for unit in ['B', 'KB', 'MB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f}{unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f}GB"


def generate_tree(
    root_dir: str, 
    max_depth: int = 3,
    selective_dirs: List[str] = None
) -> str:
    """
    Generate a token-efficient tree view of the repository.
    
    Args:
        root_dir: Root directory to scan
        max_depth: Maximum depth to traverse (default: 3)
        selective_dirs: If provided, only include these directories
        
    Returns:
        Formatted tree structure as string
    """
    root_path = Path(root_dir).resolve()
    lines = [f"Project Root: {root_path.name}/\n"]
    
    def _walk_tree(current_path: Path, prefix: str = "", depth: int = 0):
        if depth > max_depth:
            return
        
        # If selective filtering is enabled, check if we should include this path
        if selective_dirs:
            relative = current_path.relative_to(root_path)
            if depth > 0 and not any(str(relative).startswith(d) for d in selective_dirs):
                return
        
        try:
            items = sorted(current_path.iterdir(), key=lambda x: (not x.is_dir(), x.name))
        except PermissionError:
            return
        
        # Separate directories and files
        dirs = [item for item in items if item.is_dir() and not should_ignore(item)]
        files = [item for item in items if item.is_file() and not should_ignore(item)]
        
        # Process directories first
        for i, dir_path in enumerate(dirs):
            is_last_dir = (i == len(dirs) - 1) and len(files) == 0
            connector = "└── " if is_last_dir else "├── "
            lines.append(f"{prefix}{connector}{dir_path.name}/")
            
            extension = "    " if is_last_dir else "│   "
            _walk_tree(dir_path, prefix + extension, depth + 1)
        
        # Process files
        for i, file_path in enumerate(files):
            is_last = i == len(files) - 1
            connector = "└── " if is_last else "├── "
            
            try:
                size = file_path.stat().st_size
                size_str = get_file_size_str(size)
                lines.append(f"{prefix}{connector}{file_path.name} ({size_str})")
            except (OSError, PermissionError):
                lines.append(f"{prefix}{connector}{file_path.name}")
    
    _walk_tree(root_path)
    return "\n".join(lines)


def get_project_context(
    root_dir: str = ".",
    max_depth: int = 3,
    relevant_keywords: List[str] = None
) -> str:
    """
    Get a comprehensive but token-efficient project context.
    
    Args:
        root_dir: Project root directory
        max_depth: Maximum tree depth
        relevant_keywords: If provided, filter directories by these keywords
        
    Returns:
        Formatted context string
    """
    root_path = Path(root_dir).resolve()
    
    # Generate selective directory list if keywords provided
    selective_dirs = None
    if relevant_keywords:
        selective_dirs = []
        for root, dirs, _ in os.walk(root_path):
            dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
            for dir_name in dirs:
                if any(keyword.lower() in dir_name.lower() for keyword in relevant_keywords):
                    rel_path = Path(root).relative_to(root_path) / dir_name
                    selective_dirs.append(str(rel_path))
    
    tree = generate_tree(str(root_path), max_depth, selective_dirs)
    
    context = f"""# Project Structure

{tree}

## Context Notes
- Tree depth limited to {max_depth} levels for token efficiency
- System directories (.git, .venv, __pycache__) are filtered out
"""
    
    if selective_dirs:
        context += f"- Selective filtering applied for: {', '.join(relevant_keywords)}\n"
    
    return context


if __name__ == "__main__":
    # Test the context generator
    print(get_project_context(max_depth=2))
