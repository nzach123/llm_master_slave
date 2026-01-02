import google.generativeai as genai
from core.config import load_config

class GeminiClient:
    def __init__(self):
        config = load_config()
        self.api_key = config.get("GEMINI_API_KEY")
        
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY not found in configuration")
            
        genai.configure(api_key=self.api_key)
