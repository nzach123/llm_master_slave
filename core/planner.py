import json
import google.generativeai as genai
from tenacity import retry, stop_after_attempt, wait_exponential
from core.config import load_config
from core.specs import DispatchStep
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
            
        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel(
            model_name="gemini-2.0-flash",
            system_instruction=get_system_prompt(project_root)
        )


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
        
        response = self.model.generate_content(prompt)
        
        try:
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
