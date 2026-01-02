import json
import google.generativeai as genai
from core.config import load_config
from core.specs import DispatchStep

class GeminiClient:
    def __init__(self):
        config = load_config()
        self.api_key = config.get("GEMINI_API_KEY")
        
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY not found in configuration")
            
        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel("gemini-2.0-flash")

    def generate_plan(self, user_intent: str) -> DispatchStep:
        """
        Generate a structured plan based on user intent.
        
        Args:
            user_intent: The high-level goal provided by the user.
            
        Returns:
            A validated DispatchStep object.
            
        Raises:
            ValueError: If the model response cannot be parsed or validated.
        """
        prompt = f"Generate a JSON response for the following intent: {user_intent}"
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