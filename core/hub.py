import logging
import uuid
from tenacity import retry, stop_after_attempt, wait_fixed
from core.config import load_config, setup_logging
from core.specs import DispatchStep, AgentResult
from core.planner import GeminiClient
from tools.git_tools import create_checkpoint

class Spine:
    def __init__(self):
        self.config = load_config()
        setup_logging()
        self.logger = logging.getLogger(__name__)
        self.logger.info("Spine initialized.")
        try:
            self.planner = GeminiClient()
        except ValueError as e:
            self.logger.warning(f"Planner initialization failed (API Key missing?): {e}")
            self.planner = None

    @retry(stop=stop_after_attempt(2), wait=wait_fixed(1))
    def dispatch_to_agent(self, agent_func) -> AgentResult:
        """Dispatches a step to an agent with retry logic."""
        self.logger.info("Dispatching task to agent...")
        return agent_func()

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

        # 2. Dispatch (Mock for now, as we don't have real agents yet)
        def agent_action():
            self.logger.info(f"Agent {step.agent_name} executing: {step.task_description}")
            # In a real scenario, we'd route to the specific agent here based on step.agent_name
            return AgentResult(status="ok", message=f"Executed: {step.task_description}", artifacts=[])

        result = self.dispatch_to_agent(agent_action)
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
            agent_name="MockAgent",
            task_description="Create a hello world file",
            context={}
        )

        def mock_agent_action():
            self.logger.info(f"Agent executing: {step.task_description}")
            return AgentResult(status="ok", message="Hello World created", artifacts=["hello.txt"])

        result = self.dispatch_to_agent(mock_agent_action)
        self.logger.info(f"Task completed with status: {result.status}")
        return result