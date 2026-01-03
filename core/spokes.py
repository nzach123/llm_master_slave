import httpx
import logging
import json
from abc import ABC, abstractmethod
from typing import Type, TypeVar
from pydantic import BaseModel
from core.specs import DispatchStep, AgentResult, SpokeResponse, ReviewResult, KnowledgeSummary, ResearcherOutput
from core.roles import CODER_SYSTEM_PROMPT, REVIEWER_SYSTEM_PROMPT, RESEARCHER_SYSTEM_PROMPT, TROUBLESHOOTER_SYSTEM_PROMPT

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)

class BaseSpoke(ABC):
    def __init__(self, base_url: str, model: str):
        # Sanitize base_url: strip trailing slashes and /v1 suffix
        self.base_url = base_url.rstrip("/")
        if self.base_url.endswith("/v1"):
            self.base_url = self.base_url[:-3].rstrip("/")
        self.model = model

    @abstractmethod
    def get_system_prompt(self) -> str:
        pass

    @property
    @abstractmethod
    def response_model(self) -> Type[T]:
        """Returns the Pydantic model class expected for this spoke's response."""
        pass

    def build_prompt(self, step: DispatchStep) -> str:
        """Constructs the prompt with context injection."""
        return (
            f"Context Files: {step.context_files}\n"
            f"Task: {step.task}"
        )

    async def handle_task(self, step: DispatchStep) -> T:
        """Sends an asynchronous request to Ollama with JSON enforcement."""
        system_prompt = self.get_system_prompt()
        user_prompt = self.build_prompt(step)

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": 0.1,
            "format": "json",
            "stream": False
        }

        logger.info(f"Sending task to Ollama model: {self.model}")
        
        async with httpx.AsyncClient(timeout=300.0) as client:
            # Using native Ollama /api/chat endpoint which supports 'format': 'json'
            response = await client.post(
                f"{self.base_url}/api/chat",
                json=payload
            )

            response.raise_for_status()
            data = response.json()
            
            content = data["message"]["content"]

            # Parse and Validate using the specific model for this spoke
            try:
                return self.response_model.model_validate_json(content)
            except Exception as e:
                logger.error(f"Failed to parse JSON response for {self.__class__.__name__}: {content}")
                raise e

class CoderSpoke(BaseSpoke):
    def get_system_prompt(self) -> str:
        return CODER_SYSTEM_PROMPT

    @property
    def response_model(self) -> Type[SpokeResponse]:
        return SpokeResponse

class ReviewerSpoke(BaseSpoke):
    def get_system_prompt(self) -> str:
        return REVIEWER_SYSTEM_PROMPT

    @property
    def response_model(self) -> Type[ReviewResult]:
        return ReviewResult

class ResearcherSpoke(BaseSpoke):
    def get_system_prompt(self) -> str:
        return RESEARCHER_SYSTEM_PROMPT

    @property
    def response_model(self) -> Type[ResearcherOutput]:
        return ResearcherOutput

class TroubleshooterSpoke(BaseSpoke):
    def get_system_prompt(self) -> str:
        return TROUBLESHOOTER_SYSTEM_PROMPT

    @property
    def response_model(self) -> Type[SpokeResponse]:
        # Troubleshooter output is similar to Coder (thoughts + tool_calls)
        return SpokeResponse
