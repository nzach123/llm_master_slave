import logging
import uuid
import os
import re
import xml.etree.ElementTree as ET
from typing import List
from tenacity import retry, stop_after_attempt, wait_fixed
from core.config import load_config, setup_logging
from core.specs import DispatchStep, AgentResult, ToolCall
from core.planner import GeminiClient
from core.spokes import CoderSpoke, ReviewerSpoke
from core.parsing import TagParser
from tools.git_tools import create_checkpoint
from tools.resource_monitor import check_resources_threshold, wait_for_resources
from tools import patcher
from tools.executor import run_pytest, parse_pytest_output
from tools.queue import TaskQueue

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
        
        # Initialize TagParser
        self.parser = TagParser()

        # Initialize TaskQueue
        self.queue = TaskQueue()

        try:
            self.planner = GeminiClient()
        except ValueError as e:
            self.logger.warning(f"Planner initialization failed (API Key missing?): {e}")
            self.planner = None

    @retry(stop=stop_after_attempt(2), wait=wait_fixed(1), reraise=True)
    def dispatch_to_agent(self, step: DispatchStep) -> AgentResult:
        """Dispatches a step to a specific Spoke with resource checks."""
        self.logger.info(f"Dispatching task to agent: {step.agent_name}")
        
        # Pre-flight resource check (Wait-State Policy)
        skip_check = os.getenv("SKIP_RESOURCE_CHECK", "false").lower() == "true"
        if not skip_check:
            # Wait up to 10 minutes (600s) for resources
            if not wait_for_resources(min_gb=2.0, timeout_seconds=600):
                 error_msg = "System resources below threshold (2GB) after timeout. Terminating for stability."
                 self.logger.critical(error_msg)
                 raise RuntimeError(error_msg)

        if step.agent_name.lower() == "coder":
            return self.coder.handle_task(step)
        elif step.agent_name.lower() == "reviewer":
            return self.reviewer.handle_task(step)
        else:
            raise ValueError(f"Unknown agent: {step.agent_name}")
    
    def _parse_tool_calls(self, text: str) -> List[ToolCall]:
        """
        Parse XML tool calls from LLM output.
        Uses TagParser for robust extraction of raw code blocks.
        """
        self.logger.info("Parsing tool calls from LLM output...")
        return self.parser.parse_tool_calls(text)
    
    def _execute_tool_calls(self, tool_calls: List[ToolCall]) -> dict:
        """
        Execute parsed tool calls using the patcher module.
        
        Args:
            tool_calls: List of ToolCall objects to execute
            
        Returns:
            Dict with execution results
        """
        results = {"success": [], "failed": []}
        
        for tool_call in tool_calls:
            try:
                if tool_call.action == "write_file":
                    patcher.write_file(tool_call.path, tool_call.content)
                    results["success"].append(f"Wrote {tool_call.path}")
                    self.logger.info(f"Successfully wrote file: {tool_call.path}")
                    
                elif tool_call.action == "apply_patch":
                    success = patcher.apply_patch(
                        tool_call.path,
                        tool_call.old_content,
                        tool_call.content
                    )
                    if success:
                        results["success"].append(f"Patched {tool_call.path}")
                        self.logger.info(f"Successfully patched file: {tool_call.path}")
                    else:
                        results["failed"].append(
                            f"Patch failed for {tool_call.path}: search block not found"
                        )
                        
            except patcher.PathSecurityError as e:
                error_msg = f"Security violation: {tool_call.path} - {str(e)}"
                results["failed"].append(error_msg)
                self.logger.error(error_msg)
            except Exception as e:
                error_msg = f"Error executing {tool_call.action} on {tool_call.path}: {str(e)}"
                results["failed"].append(error_msg)
                self.logger.error(error_msg)
        
        return results

    def run_autonomous_loop(self, user_intent: str, max_retries: int = 3, existing_task_id: str = None) -> AgentResult:
        """
        Executes an autonomous loop with retry capability: Plan -> Execute -> Verify -> Retry if needed.
        
        Args:
            user_intent: The high-level goal from the user.
            max_retries: Maximum number of retry attempts (default: 3)
            existing_task_id: ID of an existing task if resuming/processing from queue
            
        Returns:
            The final result of the agent execution.
        """
        if not self.planner:
            raise RuntimeError("Planner not initialized. Cannot run autonomous loop.")

        task_id = existing_task_id or f"task_{uuid.uuid4().hex[:8]}"
        self.logger.info(f"Starting/Resuming autonomous loop for task: {task_id}")
        self.logger.info(f"User Intent: {user_intent}")

        original_branch = "main"
        task_branch = None
        try:
            from tools.git_tools import get_current_branch, rollback
            original_branch = get_current_branch()
            task_branch = create_checkpoint(task_id)

            # Update task state with branch info
            self.queue.update_task_state(task_id, git_branch=task_branch)

        except Exception as e:
            self.logger.warning(f"Git checkpoint skipped or failed: {e}")

        error_context = None
        attempt = 0
        
        while attempt < max_retries:
            attempt += 1
            self.logger.info(f"Attempt {attempt}/{max_retries}")
            
            # Update task progress
            self.queue.update_task_state(task_id, step_index=attempt)

            try:
                # 1. Generate Plan (with error context if retrying)
                self.logger.info("Generating plan...")
                step = self.planner.generate_plan(user_intent, error_context)
                self.logger.info(f"Plan generated: Agent={step.agent_name}, Task={step.task_description}")

                # 2. Dispatch to agent
                result = self.dispatch_to_agent(step)
                
                # 3. Parse and execute tool calls
                tool_calls = self._parse_tool_calls(result.message)
                execution_results = {"success": [], "failed": []}
                
                if tool_calls:
                    self.logger.info(f"Found {len(tool_calls)} tool calls to execute")
                    execution_results = self._execute_tool_calls(tool_calls)
                    self.logger.info(f"Tool execution results: {execution_results}")
                
                # 4. Run tests if tool execution succeeded
                test_failures = None
                if execution_results["success"] and not execution_results["failed"]:
                    self.logger.info("Running tests to verify changes...")
                    try:
                        test_result = run_pytest(timeout=180)
                        if not test_result.success:
                            # Parse test output for relevant failures
                            parsed = parse_pytest_output(test_result.stdout)
                            test_failures = (
                                f"Tests failed (exit code {test_result.exit_code}):\n" +
                                "\n".join(parsed["failed_tests"][:5])  # Limit to first 5 failures
                            )
                            self.logger.warning(f"Test failures detected: {test_failures}")
                    except Exception as e:
                        self.logger.warning(f"Test execution failed: {e}")
                        # Don't fail the loop if test execution itself fails
                
                # 5. Check for failures (tool execution or tests)
                if execution_results["failed"] or test_failures:
                    # Build comprehensive error context
                    error_parts = []
                    
                    if execution_results["failed"]:
                        error_parts.append("Tool execution failures:\n" + "\n".join(execution_results["failed"]))
                    
                    if test_failures:
                        error_parts.append(test_failures)
                    
                    error_context = "\n\n".join(error_parts)
                    self.logger.warning(f"Attempt {attempt} failed: {error_context}")
                    
                    if attempt < max_retries:
                        self.logger.info("Retrying with error context...")
                        continue
                    else:
                        self.logger.error("Max retries reached. Terminating and rolling back.")
                        try:
                            from tools.git_tools import rollback
                            # Close TinyDB to release file lock before git operations
                            if hasattr(self.queue, 'close'):
                                self.queue.close()
                            rollback(original_branch, task_branch)
                        except Exception as re:
                            self.logger.error(f"Rollback failed: {re}")
                            
                        return AgentResult(
                            status="error",
                            message=f"Failed after {max_retries} attempts: {error_context}",
                            artifacts=[]
                        )
                else:
                    # Success!
                    self.logger.info(f"Task completed successfully on attempt {attempt}")
                    
                    # Generate manual verification steps
                    try:
                        verification_steps = self.planner.generate_verification_steps(user_intent, step.task_description)
                        result.message = f"{result.message}\n\n{verification_steps}"
                        self.logger.info("Manual verification steps generated.")
                    except Exception as ve:
                        self.logger.warning(f"Could not generate verification steps: {ve}")
                        
                    return result
                    
            except Exception as e:
                error_context = f"Exception during execution: {str(e)}"
                self.logger.error(f"Attempt {attempt} failed with exception: {e}")
                
                if attempt < max_retries:
                    self.logger.info("Retrying after exception...")
                    continue
                else:
                    self.logger.error("Max retries reached after exception. Rolling back.")
                    try:
                        from tools.git_tools import rollback
                        # Close TinyDB to release file lock before git operations
                        if hasattr(self.queue, 'close'):
                            self.queue.close()
                        rollback(original_branch, task_branch)
                    except Exception as re:
                        self.logger.error(f"Rollback failed: {re}")
                    raise
        
        # Should not reach here, but safety fallback
        return AgentResult(
            status="error",
            message="Loop terminated unexpectedly",
            artifacts=[]
        )

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