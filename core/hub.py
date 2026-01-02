import logging
import uuid
import os
from tenacity import retry, stop_after_attempt, wait_fixed
from core.config import load_config, setup_logging
from core.specs import DispatchStep, AgentResult
from core.planner import GeminiClient
from core.spokes import CoderSpoke, ReviewerSpoke
from tools.git_tools import create_checkpoint
from tools.resource_monitor import check_resources_threshold

class Spine:
    def __init__(self):
        self.config = load_config()
        setup_logging()
        self.logger = logging.getLogger(__name__)
        self.logger.info("Spine initialized.")
        
        # Initialize Spokes
        base_url = self.config.get("OLLAMA_BASE_URL")
        self.coder = CoderSpoke(base_url, self.config.get("CODER_MODEL"))
        self.reviewer = ReviewerSpoke(base_url, self.config.get("REVIEWER_MODEL"))
        
        try:
            self.planner = GeminiClient()
        except ValueError as e:
            self.logger.warning(f"Planner initialization failed (API Key missing?): {e}")
            self.planner = None

    @retry(stop=stop_after_attempt(2), wait=wait_fixed(1), reraise=True)
    def dispatch_to_agent(self, step: DispatchStep) -> AgentResult:
        """Dispatches a step to a specific Spoke with resource checks."""
        self.logger.info(f"Dispatching task to agent: {step.agent_name}")
        
        # Pre-flight resource check (Hard Fail policy)
        skip_check = os.getenv("SKIP_RESOURCE_CHECK", "false").lower() == "true"
        if not skip_check and not check_resources_threshold(min_gb=2.0):
            error_msg = "System resources below threshold (2GB). Terminating for stability."
            self.logger.critical(error_msg)
            raise RuntimeError(error_msg)

        if step.agent_name.lower() == "coder":
            return self.coder.handle_task(step)
        elif step.agent_name.lower() == "reviewer":
            return self.reviewer.handle_task(step)
        else:
            raise ValueError(f"Unknown agent: {step.agent_name}")

    def run_autonomous_loop(self, user_intent: str) -> AgentResult:
        """
        Executes an autonomous loop: Plan -> Checkpoint -> Dispatch.
        
        Args:
            user_intent: The high-level goal from the user.
            
        Returns:
            The result of the agent execution.
        """
        if not self.planner:
            raise RuntimeError("Planner not initialized. Cannot run autonomous loop.")

        task_id = f"task_{uuid.uuid4().hex[:8]}"
        self.logger.info(f"Starting autonomous loop for task: {task_id}")
        self.logger.info(f"User Intent: {user_intent}")

        try:
            create_checkpoint(task_id)
        except Exception as e:
            self.logger.warning(f"Git checkpoint skipped or failed: {e}")

        # 1. Generate Plan
        self.logger.info("Generating plan...")
        step = self.planner.generate_plan(user_intent)
        self.logger.info(f"Plan generated: Agent={step.agent_name}, Task={step.task_description}")

        result = self.dispatch_to_agent(step)
        self.logger.info(f"Task completed with status: {result.status}")
        return result

    def run_mock_loop(self):
        """A simple mock loop for verification."""
        task_id = "mock_task_001"
        self.logger.info(f"Starting mock loop for task: {task_id}")
        
        try:
            create_checkpoint(task_id)
        except Exception as e:
            self.logger.warning(f"Git checkpoint skipped or failed: {e}")

        # Mock DispatchStep
        step = DispatchStep(
            agent_name="coder",
            task_description="Create a hello world file",
            context={}
        )

        result = self.dispatch_to_agent(step)
        self.logger.info(f"Task completed with status: {result.status}")
        return result