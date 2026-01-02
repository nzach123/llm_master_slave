import httpx
import logging
import json
from abc import ABC, abstractmethod
from core.specs import DispatchStep, AgentResult

logger = logging.getLogger(__name__)

class BaseSpoke(ABC):
    def __init__(self, base_url: str, model: str):
        self.base_url = base_url
        self.model = model

    @abstractmethod
    def get_system_prompt(self) -> str:
        pass

    def build_prompt(self, step: DispatchStep) -> str:
        """Constructs the prompt with context injection."""
        context_str = json.dumps(step.context, indent=2)
        return (
            f"Context:\n{context_str}\n\n"
            f"Task: {step.task_description}"
        )

    def handle_task(self, step: DispatchStep) -> AgentResult:
        """Sends a synchronous request to Ollama's OpenAI-compatible endpoint."""
        system_prompt = self.get_system_prompt()
        user_prompt = self.build_prompt(step)

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": 0.1
        }

        logger.info(f"Sending task to Ollama model: {self.model}")
        
        with httpx.Client(timeout=300.0) as client:
            response = client.post(
                f"{self.base_url}/chat/completions",
                json=payload
            )
            response.raise_for_status()
            data = response.json()
            
            content = data["choices"][0]["message"]["content"]
            return AgentResult(
                status="ok",
                message=content,
                artifacts=[]
            )

class CoderSpoke(BaseSpoke):
    def get_system_prompt(self) -> str:
        return (
            "You are an expert Python developer. "
            "Your task is to implement features or fix bugs based on the provided context. "
            "Provide clean, documented, and idiomatic Python code.\n\n"
            
            "## CRITICAL: OUTPUT FORMAT\n"
            "You MUST output file operations using XML tags. Do NOT use markdown code fences.\n\n"
            
            "To create or overwrite a file:\n"
            "<write_file path=\"relative/path/to/file.py\">\n"
            "# Complete file content here\n"
            "def example():\n"
            "    pass\n"
            "</write_file>\n\n"
            
            "To patch an existing file (search/replace):\n"
            "<apply_patch path=\"relative/path/to/file.py\">\n"
            "<old>\n"
            "exact text to find and replace\n"
            "</old>\n"
            "<new>\n"
            "replacement text\n"
            "</new>\n"
            "</apply_patch>\n\n"
            
            "You may include explanation text outside the XML tags, but ALL file operations MUST use these tags.\n"
            "Multiple operations are allowed. Execute them in logical order.\n"
        )

class ReviewerSpoke(BaseSpoke):
    def get_system_prompt(self) -> str:
        return (
            "You are a senior code reviewer. "
            "Analyze the provided code changes for quality, bugs, and security issues. "
            "Respond strictly with either 'Approve' or 'Reject', followed by your detailed reasoning."
        )
