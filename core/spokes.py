import httpx
import logging
import json
from abc import ABC, abstractmethod
from core.specs import DispatchStep, AgentResult
from core.roles import CODER_SYSTEM_PROMPT, REVIEWER_SYSTEM_PROMPT, RESEARCHER_SYSTEM_PROMPT

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
        return CODER_SYSTEM_PROMPT

class ReviewerSpoke(BaseSpoke):
    def get_system_prompt(self) -> str:
        return REVIEWER_SYSTEM_PROMPT

class ResearcherSpoke(BaseSpoke):
    def get_system_prompt(self) -> str:
        return RESEARCHER_SYSTEM_PROMPT
