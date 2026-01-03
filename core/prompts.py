"""
System prompts for the Hub (Gemini) Planner.
"""
import json
from core.specs import DispatchStep
from tools.context import get_project_context

SYSTEM_PROMPT = """
You are the Hub (Planner) for an LLM master-slave agent system.
Your goal is to parse user intent and decompose it into a structured, executable plan.

GUIDELINES:
1. **Comprehensiveness**: Your initial plan must be detailed enough to be actionable. Anticipate complexity. Vague plans will be rejected by the Judge.
2. **Strict JSON**: You MUST output only valid JSON matching the provided schema.
3. **No Markdown**: Do not wrap the JSON in markdown code blocks unless explicitly told otherwise.
4. **Valid Agents**: The 'agent_name' field MUST be one of: "coder" or "reviewer".
5. **File Paths**: When using `write_file`, ALWAYS provide a full filename with an extension (e.g., `folder/file.py`).
6. **Implementation Details**: When planning code, specify:
    - Target files
    - Key functions/classes to implement
    - Dependencies to check
    - Testing strategy

EXAMPLE OUTPUT:
{
  "agent_name": "coder",
  "task_description": "Create core/utils.py. Implement `calculate_metrics(data)` using numpy. Ensure it handles empty input arrays. Add unit tests in tests/test_utils.py.",
  "context": {}
}

SCHEMA:
The response must match the following JSON schema:
"""

def get_system_prompt(project_root: str = ".", include_context: bool = True) -> str:
    """
    Generate the system prompt dynamically including the Pydantic schema and project context.
    
    Args:
        project_root: Root directory of the project for context gathering
        include_context: Whether to inject project structure context
    
    Returns:
        The full system prompt string.
    """
    schema = DispatchStep.model_json_schema()
    prompt = f"{SYSTEM_PROMPT}\n{json.dumps(schema, indent=2)}"
    
    if include_context:
        try:
            # Generate project context (selective, token-efficient)
            project_context = get_project_context(project_root, max_depth=2)
            prompt += f"\n\n## Current Project Structure\n\n{project_context}\n"
        except Exception as e:
            # Gracefully degrade if context generation fails
            prompt += f"\n\n## Project Context\n(Context unavailable: {str(e)})\n"
    
    return prompt