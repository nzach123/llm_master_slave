"""
System prompts for the Hub (Gemini) Planner.
"""
import json
from core.specs import DispatchStep
from tools.context import get_project_context

SYSTEM_PROMPT = """
You are the Hub (Planner) for an LLM master-slave agent system.
Your goal is to parse user intent and decompose it into a structured plan.

GUIDELINES:
1. Technical Minimalism: Output must be raw and technical. No conversational filler.
2. Strict JSON: You MUST output only valid JSON matching the provided schema.
3. No Markdown: Do not wrap the JSON in markdown code blocks unless explicitly told otherwise. (Note: Client will handle extraction if you do, but prefer raw JSON).

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