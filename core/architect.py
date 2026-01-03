import json
import logging
from google import genai
from google.genai import types
from tenacity import retry, stop_after_attempt, wait_exponential
from core.config import load_config
from core.specs import ProjectBundle

class Architect:
    def __init__(self, project_root: str = "."):
        config = load_config()
        self.api_key = config.get("GEMINI_API_KEY")
        self.project_root = project_root

        if not self.api_key:
            raise ValueError("GEMINI_API_KEY not found in configuration")

        self.model_name = config.get("GEMINI_MODEL", "gemini-2.0-flash") # Use 2.0 Flash as per memory
        self.client = genai.Client(api_key=self.api_key)
        self.logger = logging.getLogger(__name__)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def generate_project_bundle(self, roadmap_path: str = "conductor/roadmap.md") -> ProjectBundle:
        """
        Reads the roadmap, identifies the next milestone, and generates a ProjectBundle.
        """
        with open(roadmap_path, "r", encoding="utf-8") as f:
            roadmap_content = f.read()

        prompt = f"""
        You are the System Architect. Your goal is to define the next immediate project based on the roadmap.

        Roadmap Content:
        {roadmap_content}

        INSTRUCTIONS:
        1. Identify the first unchecked milestone in the Roadmap.
        2. Create a comprehensive 'Project Bundle' for this milestone.
        3. 'acceptance_criteria' must be a list of natural language statements describing what success looks like (e.g., "The user can login via CLI").
        4. 'constraints' should list technical boundaries.

        Output strictly valid JSON matching the ProjectBundle schema.
        """

        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction="You are a Senior Software Architect. Output strictly JSON."
                )
            )

            text = response.text
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0].strip()
            elif "```" in text:
                text = text.split("```")[1].split("```")[0].strip()

            data = json.loads(text)
            return ProjectBundle(**data)

        except Exception as e:
            self.logger.error(f"Architect failed to generate bundle: {e}")
            raise
