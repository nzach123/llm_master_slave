import logging
from tenacity import retry, stop_after_attempt, wait_fixed
from core.config import load_config, setup_logging
from core.specs import DispatchStep, AgentResult
from tools.git_tools import create_checkpoint

class Spine:
    def __init__(self):
        self.config = load_config()
        setup_logging()
        self.logger = logging.getLogger(__name__)
        self.logger.info("Spine initialized.")

    @retry(stop=stop_after_attempt(2), wait=wait_fixed(1))
    def dispatch_to_agent(self, agent_func) -> AgentResult:
        """Dispatches a step to an agent with retry logic."""
        self.logger.info("Dispatching task to agent...")
        return agent_func()

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
