import os
import logging
from pathlib import Path
from typing import List, Dict
from core.planner import GeminiClient
from tools.context import get_project_context

logger = logging.getLogger(__name__)

class CodebaseAnalyzer:
    def __init__(self, project_root: str = "."):
        self.project_root = Path(project_root).resolve()
        self.planner = GeminiClient(project_root=str(self.project_root))
        
    def _read_file_safe(self, file_path: Path) -> str:
        """Reads a file and returns its content or an error message."""
        if not file_path.exists():
            return f"(File not found: {file_path})"
        try:
            return file_path.read_text(encoding="utf-8")
        except Exception as e:
            return f"(Error reading {file_path}: {e})"

    def _get_core_files_content(self) -> str:
        """Aggregates content of core architectural files."""
        core_files = [
            "core/hub.py",
            "core/planner.py",
            "core/spokes.py",
            "main.py"
        ]
        
        content_parts = []
        for file_rel_path in core_files:
            file_path = self.project_root / file_rel_path
            content = self._read_file_safe(file_path)
            content_parts.append(f"### File: {file_rel_path}\n\n```python\n{content}\n```")
            
        return "\n\n".join(content_parts)

    def _get_conductor_docs(self) -> str:
        """Aggregates content of conductor documentation files."""
        doc_files = [
            "conductor/product.md",
            "conductor/tech-stack.md",
            "conductor/workflow.md"
        ]
        
        content_parts = []
        for file_rel_path in doc_files:
            file_path = self.project_root / file_rel_path
            content = self._read_file_safe(file_path)
            content_parts.append(f"### Doc: {file_rel_path}\n\n{content}")
            
        return "\n\n".join(content_parts)

    def analyze(self) -> str:
        """Performs the full codebase analysis using Gemini."""
        logger.info("Starting codebase analysis...")
        
        project_structure = get_project_context(str(self.project_root), max_depth=3)
        core_logic = self._get_core_files_content()
        documentation = self._get_conductor_docs()
        
        analysis_prompt = f"""
You are an expert Systems Architect and Lead Developer. 
Your task is to analyze the provided codebase and documentation to provide a clear explanation of how it works and suggest next steps for implementation.

## 1. ANALYSIS INPUTS

### Project Structure
{project_structure}

### Core Documentation
{documentation}

### Core Implementation Logic
{core_logic}

## 2. OUTPUT REQUIREMENTS

Analyze the above and provide a report in Markdown format with the following sections:

1.  **System Overview**: A high-level explanation of the architecture (Hub-and-Spoke, autonomous loop, tool usage).
2.  **Key Components**: Briefly explain the role of `core/hub.py`, `core/planner.py`, `core/spokes.py`, and any critical tools.
3.  **Current Status**: Based on the code and documentation, identify what is currently implemented and what seems to be in progress.
4.  **Implementation Next Steps**: Provide a prioritized list of concrete implementation tasks (e.g., adding new tools, improving error handling, increasing test coverage).
5.  **Technical Recommendations**: Suggest any architectural improvements or best practices that should be applied.

Keep the tone technical, concise, and actionable.
"""
        
        # Override the system instruction for this specific task
        self.planner.model = self.planner.model.__class__(
            model_name=self.planner.model_name,
            system_instruction="You are a Master Systems Architect providing codebase analysis reports."
        )
        
        response = self.planner.model.generate_content(analysis_prompt)
        return response.text

if __name__ == "__main__":
    # Test call
    logging.basicConfig(level=logging.INFO)
    analyzer = CodebaseAnalyzer()
    print(analyzer.analyze())
