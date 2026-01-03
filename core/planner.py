import json
import warnings
from google import genai
from google.genai import types
from tenacity import retry, stop_after_attempt, wait_exponential
from core.config import load_config
from core.specs import DispatchStep, FeasibilityCheck
from core.prompts import get_system_prompt

class GeminiClient:
    def __init__(self, project_root: str = "."):
        """
        Initialize the Gemini Planner client.
        
        Args:
            project_root: Root directory of the project for context gathering
        """
        config = load_config()
        self.api_key = config.get("GEMINI_API_KEY")
        self.project_root = project_root
        
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY not found in configuration")
            
        self.model_name = config.get("GEMINI_MODEL", "gemini-1.5-flash")
        
        # Initialize the client with the API key from environment or config
        # Note: If GEMINI_API_KEY is in env, genai.Client() picks it up automatically,
        # but passing it explicitly is safer if load_config() is the source of truth.
        self.client = genai.Client(api_key=self.api_key)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True
    )
    def generate_plan(self, user_intent: str, error_context: str = None) -> DispatchStep:
        """
        Generate a structured plan based on user intent.
        
        Args:
            user_intent: The high-level goal provided by the user.
            error_context: Optional error context from previous attempt
            
        Returns:
            A validated DispatchStep object.
            
        Raises:
            ValueError: If the model response cannot be parsed or validated.
        """
        # Inject error context if retrying
        prompt = user_intent
        if error_context:
            prompt = f"{user_intent}\n\n**Previous Attempt Failed:**\n{error_context}\n\nPlease revise the plan."
        
        # In the new SDK, system instructions are passed via the config object
        system_instruction = get_system_prompt(self.project_root)
        
        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction
                )
            )

            # Attempt to extract JSON if it's wrapped in markdown code blocks
            text = response.text
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0].strip()
            elif "```" in text:
                text = text.split("```")[1].split("```")[0].strip()
            
            data = json.loads(text)
            return DispatchStep(**data)

        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse JSON response: {str(e)}")
        except Exception as e:
            raise ValueError(f"Failed to validate plan: {str(e)}")

    def refine_plan(self, original_plan: DispatchStep, feedback: FeasibilityCheck) -> DispatchStep:
        """
        Refines a plan based on feedback from the Researcher/Spoke.
        """
        prompt = f"""
        Original Task: {original_plan.task}
        Original Context: {original_plan.context_files}

        Researcher Feedback:
        - Hard Constraints: {feedback.summary.hard_constraints}
        - Soft Constraints: {feedback.summary.soft_constraints}
        - Missing Info: {feedback.summary.known_unknowns}
        - Message: {feedback.message}

        Please refine the plan to address these constraints and missing information.
        Update the 'task_description' and 'context' fields accordingly.
        """

        system_instruction = get_system_prompt(self.project_root)

        try:
             response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction
                )
            )

             # Attempt to extract JSON if it's wrapped in markdown code blocks
             text = response.text
             if "```json" in text:
                text = text.split("```json")[1].split("```")[0].strip()
             elif "```" in text:
                text = text.split("```")[1].split("```")[0].strip()

             data = json.loads(text)
             return DispatchStep(**data)

        except json.JSONDecodeError as e:
            # Fallback: Return original plan if parsing fails (for now)
            # In production, we'd want to retry or raise
            warnings.warn(f"Failed to parse refined plan JSON: {e}")
            return original_plan
        except Exception as e:
             raise ValueError(f"Failed to refine plan: {str(e)}")

    def generate_verification_steps(self, user_intent: str, task_description: str) -> str:
        """
        Generate actionable manual verification steps following the workflow.md format.
        """
        prompt = f"""
Based on the completed task, generate a step-by-step manual verification plan for the user.

USER INTENT: {user_intent}
TASK COMPLETED: {task_description}

FORMAT REQUIREMENTS:
- Use the structure from workflow.md.
- For backend changes, include curl commands or script execution.
- For frontend changes, include browser navigation and expected visual outcomes.
- Start with 'The automated tests have passed. For manual verification, please follow these steps:'
- Use a bold heading '**Manual Verification Steps:**'

Keep it concise and actionable.
"""
        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction="You are a Quality Assurance Engineer generating manual verification protocols."
                )
            )
            return response.text
        except Exception as e:
            # Fallback or log if verification step generation fails
            return f"Error generating verification steps: {str(e)}"
