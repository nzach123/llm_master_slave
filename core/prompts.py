"""
System prompts for the Hub (Gemini) Planner.
"""
import json
from core.specs import DispatchStep

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

def get_system_prompt() -> str:
    """
    Generate the system prompt dynamically including the Pydantic schema.
    
    Returns:
        The full system prompt string.
    """
    schema = DispatchStep.model_json_schema()
    return f"{SYSTEM_PROMPT}\n{json.dumps(schema, indent=2)}"