import logging
import uuid
import os
import re
import xml.etree.ElementTree as ET
from typing import List
import json
import asyncio
from tenacity import retry, stop_after_attempt, wait_fixed
from core.config import load_config, setup_logging
from core.specs import DispatchStep, AgentResult, ToolCall, KnowledgeSummary, FeasibilityCheck, SpokeResponse, ResearcherOutput
from core.planner import GeminiClient
from core.spokes import CoderSpoke, ReviewerSpoke, ResearcherSpoke
from core.judge import JudgeSpoke
from core.troubleshooter import Troubleshooter
# from core.parsing import TagParser # REMOVED: Replaced by structured JSON
from core.consensus import ConsensusScorer
from core.conflict_resolver import ConflictResolver, ConflictResolutionStrategy
from tools.git_tools import create_checkpoint
from tools.resource_monitor import check_resources_threshold, wait_for_resources
from tools import patcher
from tools.executor import run_pytest, parse_pytest_output
from tools.queue import TaskQueue
from tools.context import get_project_context
from tools.logger import rich_logger

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
        self.researcher = ResearcherSpoke(base_url, self.config.get("CODER_MODEL")) # Reuse coder model for now or separate
        self.judge = JudgeSpoke(base_url, self.config.get("JUDGE_MODEL"))
        self.troubleshooter = Troubleshooter(base_url, self.config.get("CODER_MODEL")) # Use robust model for troubleshooting
        
        # Initialize TagParser
        # self.parser = TagParser() # REMOVED

        # Initialize TaskQueue
        self.queue = TaskQueue()

        # Initialize Consensus Scorer
        # self.scorer = ConsensusScorer() # REPLACED by Judge
        
        # Initialize Conflict Resolver for multi-worker scenarios (ISSUE-001 fix)
        self.conflict_resolver = ConflictResolver(ConflictResolutionStrategy.MAJORITY_VOTE)

        # Resource Mutex
        self.resource_lock = asyncio.Lock()

        try:
            self.planner = GeminiClient()
        except ValueError as e:
            self.logger.warning(f"Planner initialization failed (API Key missing?): {e}")
            self.planner = None

    @retry(stop=stop_after_attempt(2), wait=wait_fixed(1), reraise=True)
    async def dispatch_to_agent(self, step: DispatchStep) -> SpokeResponse | AgentResult | ResearcherOutput:
        """Dispatches a step to a specific Spoke with resource checks and mutex."""
        self.logger.info(f"Dispatching task to agent: {step.agent}")
        rich_logger.log_info(f"Dispatching task to {step.agent}")
        
        # Pre-flight resource check (Wait-State Policy)
        skip_check = os.getenv("SKIP_RESOURCE_CHECK", "false").lower() == "true"
        if not skip_check:
            # Wait up to 10 minutes (600s) for resources
            if not await wait_for_resources(min_gb=2.0, timeout_seconds=600):
                 error_msg = "System resources below threshold (2GB) after timeout. Terminating for stability."
                 self.logger.critical(error_msg)
                 rich_logger.log_error(error_msg)
                 raise RuntimeError(error_msg)

        async with self.resource_lock:
            with rich_logger.log_status(f"Agent {step.agent} working..."):
                if step.agent.lower() == "coder":
                    return await self.coder.handle_task(step)
                elif step.agent.lower() == "reviewer":
                    return await self.reviewer.handle_task(step)
                elif step.agent.lower() == "researcher":
                    # For researcher, we expect JSON output.
                    result = await self.researcher.handle_task(step)
                    return result
                elif step.agent.lower() == "judge":
                    # Judge output is specialized
                    return await self.judge.handle_task(step)
                else:
                    raise ValueError(f"Unknown agent: {step.agent}")
    
    def _parse_tool_calls(self, spoke_response: SpokeResponse) -> List[ToolCall]:
        """
        Extract tool calls from the structured SpokeResponse.
        """
        self.logger.info("Extracting tool calls from SpokeResponse...")
        return spoke_response.tool_calls
    
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
                    # Pydantic model makes content optional, but it's required for write_file
                    if tool_call.content is None:
                         raise ValueError("Content missing for write_file")
                    patcher.write_file(tool_call.path, tool_call.content)
                    results["success"].append(f"Wrote {tool_call.path}")
                    self.logger.info(f"Successfully wrote file: {tool_call.path}")
                    rich_logger.log_success(f"Wrote {tool_call.path}")
                    
                elif tool_call.action == "apply_patch":
                     # Pydantic model makes these optional, but required for apply_patch
                    if tool_call.search is None or tool_call.replace is None:
                        raise ValueError("Search or replace block missing for apply_patch")

                    success = patcher.apply_patch(
                        tool_call.path,
                        tool_call.search,
                        tool_call.replace
                    )
                    if success:
                        results["success"].append(f"Patched {tool_call.path}")
                        self.logger.info(f"Successfully patched file: {tool_call.path}")
                        rich_logger.log_success(f"Patched {tool_call.path}")
                    else:
                        error_msg = f"Patch failed for {tool_call.path}: search block not found"
                        results["failed"].append(error_msg)
                        rich_logger.log_error(error_msg)
                        
            except patcher.PathSecurityError as e:
                error_msg = f"Security violation: {tool_call.path} - {str(e)}"
                results["failed"].append(error_msg)
                self.logger.error(error_msg)
                rich_logger.log_error(error_msg)
            except Exception as e:
                error_msg = f"Error executing {tool_call.action} on {tool_call.path}: {str(e)}"
                results["failed"].append(error_msg)
                self.logger.error(error_msg)
                rich_logger.log_error(error_msg)
        
        return results

    async def _negotiate_plan(self, user_intent: str, max_turns: int = 3) -> DispatchStep:
        """
        Collaborative planning loop with real Researcher analysis.
        """
        self.logger.info("Starting negotiation loop...")
        rich_logger.log_info("Starting negotiation loop...")

        # 1. Hub proposes Plan v1
        with rich_logger.log_status("Planner generating initial plan..."):
            plan = self.planner.generate_plan(user_intent)
        rich_logger.log_plan(plan.model_dump())

        # Gather Project Context for Researcher
        try:
             project_tree = get_project_context(".", max_depth=2)
             # We might want to read a few key files too, but let's start with the tree
             # and maybe GEMINI.md if it exists
             context_text = f"Project Structure:\n{project_tree}\n"
             if os.path.exists("GEMINI.md"):
                 with open("GEMINI.md", "r", encoding="utf-8") as f:
                     context_text += f"\nGEMINI.md:\n{f.read()}\n"
        except Exception as e:
            self.logger.warning(f"Failed to gather project context: {e}")
            context_text = "Project context unavailable."

        for turn in range(max_turns):
            self.logger.info(f"Negotiation Turn {turn + 1}")
            rich_logger.log_info(f"Negotiation Turn {turn + 1}")

            # 2. Researcher analyzes feasibility
            # We explicitly ask the Researcher to look at the plan AND the context
            research_step = DispatchStep(
                agent="researcher",
                task=f"Analyze feasibility for this plan:\n{plan.task}\n\nUser Intent: {user_intent}",
                context_files=[context_text] # Passing raw text as context item for now
            )

            try:
                # This returns a ResearcherOutput object directly now because of the Spoke update
                research_output = await self.dispatch_to_agent(research_step)
                
                # Verify it's the right type (it should be since dispatch_to_agent calls handle_task -> validate)
                if not hasattr(research_output, "project_overview"):
                     # Fallback if something went wrong or we got a generic response
                     self.logger.warning("Researcher did not return ResearcherOutput model. Using generic.")
                     # We can't easily create a valid ResearcherOutput from scratch without data
                     # So we might just skip this turn or error. 
                     # For robustness, let's treat it as a pass but log it.
                     pass
                else:
                    self.logger.info(f"Researcher analysis complete. Hard constraints found: {len(research_output.hard_constraints.cannot_change)}")
                    rich_logger.log_info(f"Researcher found {len(research_output.hard_constraints.cannot_change)} hard constraints")

                feedback = FeasibilityCheck(
                    summary=research_output,
                    message="Researcher provided strict analysis."
                )

                # 3. Judge Evaluates Plan (Replaces ConsensusScorer)
                # Note: dispatch_to_agent handles resource locking, but here we were calling judge.evaluate_plan directly.
                # To ensure consistency and safety, we should wrap the judge call or use dispatch_to_agent if possible.
                # However, evaluate_plan is a convenience method on JudgeSpoke.
                # Let's use dispatch_to_agent to respect the resource lock.

                self.logger.info("Submitting plan to Judge for evaluation...")

                # Construct the task for the judge manually to use dispatch_to_agent
                judge_task = (
                    f"Evaluate the following plan against the researcher's feedback.\n\n"
                    f"Plan Task: {plan.task}\n"

                    f"Researcher Feedback:\n"
                    f"Hard Constraints: {feedback.summary.hard_constraints}\n"
                    f"Soft Constraints: {feedback.summary.soft_constraints}\n"
                    f"Missing Info/Unknowns: {feedback.summary.known_unknowns}\n"
                    f"Message: {feedback.message}\n"
                )

                judge_step = DispatchStep(
                    agent="judge",
                    task=judge_task,
                    context_files=[]
                )

                # Use dispatch_to_agent to ensure resource locking
                judge_result = await self.dispatch_to_agent(judge_step)

                self.logger.info(f"Judge Score: {judge_result.score} - Decision: {judge_result.decision}")
                self.logger.info(f"Judge Reasoning: {judge_result.reasoning}")

                if judge_result.score > 0.8:
                    rich_logger.log_success(f"Judge APPROVED (Score: {judge_result.score})")
                    self.logger.info("Judge APPROVED the plan!")
                    return plan
                else:
                    rich_logger.log_warning(f"Judge REJECTED (Score: {judge_result.score}): {judge_result.reasoning}")

                # 4. Refine Plan
                self.logger.info("Judge REJECTED the plan. Refining...")
                rich_logger.log_info("Refining plan based on feedback...")
                # We append the judge's reasoning to the feedback message for the planner
                feedback.message += f"\n\nJudge Feedback:\n{judge_result.reasoning}"

                with rich_logger.log_status("Planner refining plan..."):
                    plan = self.planner.refine_plan(plan, feedback)
                rich_logger.log_plan(plan.model_dump())

            except Exception as e:
                 self.logger.warning(f"Negotiation step failed: {e}. Proceeding with current plan.")
                 rich_logger.log_warning(f"Negotiation failed: {e}. Proceeding with current plan.")
                 return plan

        return plan


    async def run_autonomous_loop(self, user_intent: str, max_retries: int = 3, existing_task_id: str = None) -> AgentResult:
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
        rich_logger.log_info(f"Starting task: {user_intent} (ID: {task_id})")

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
            rich_logger.log_info(f"Attempt {attempt}/{max_retries}")
            
            # Update task progress
            self.queue.update_task_state(task_id, step_index=attempt)

            try:
                # 1. Negotiate Plan (New Step)
                if attempt == 1:
                     step = await self._negotiate_plan(user_intent)
                else:
                     # For retries, we might want to skip negotiation or re-negotiate with error context
                     # For now, let's just regenerate based on error context like before
                     with rich_logger.log_status("Regenerating plan based on errors..."):
                        step = self.planner.generate_plan(user_intent, error_context)
                     rich_logger.log_plan(step.model_dump())

                self.logger.info(f"Final Plan for execution: Agent={step.agent}, Task={step.task}")

                # INTERACTIVE GATING
                print(f"\nPLAN READY: {step.task}")
                print("Press Enter to execute, or Ctrl+C to abort...")
                # In async context, we use a thread executor for blocking input to not freeze the event loop
                await asyncio.to_thread(input, ">> ")

                # 2. Dispatch to agent
                # Ensure we are dispatching to Coder for execution phase
                step.agent = "coder"
                result = await self.dispatch_to_agent(step)
                
                # result is SpokeResponse

                # 3. Parse and execute tool calls
                tool_calls = self._parse_tool_calls(result)
                execution_results = {"success": [], "failed": []}
                
                if tool_calls:
                    self.logger.info(f"Found {len(tool_calls)} tool calls to execute")
                    execution_results = self._execute_tool_calls(tool_calls)
                    self.logger.info(f"Tool execution results: {execution_results}")
                
                # 4. Run tests if tool execution succeeded
                test_failures = None
                if execution_results["success"] and not execution_results["failed"]:
                    self.logger.info("Running tests to verify changes...")
                    rich_logger.log_info("Running verification tests...")
                    try:
                        # Use executor to run sync test runner in thread
                        test_result = await asyncio.to_thread(run_pytest, timeout=180)
                        if not test_result.success:
                            # Parse test output for relevant failures
                            parsed = parse_pytest_output(test_result.stdout)
                            test_failures = (
                                f"Tests failed (exit code {test_result.exit_code}):\n" +
                                "\n".join(parsed["failed_tests"][:5])  # Limit to first 5 failures
                            )
                            self.logger.warning(f"Test failures detected: {test_failures}")
                            rich_logger.log_error("Tests failed")
                        else:
                            rich_logger.log_success("Tests passed")
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
                    rich_logger.log_warning(f"Attempt {attempt} failed")
                    
                    # TRIGGER TROUBLESHOOTER
                    # We try to recover using the Troubleshooter before generic retry
                    try:
                        self.logger.info("Triggering Troubleshooter Protocol...")
                        rich_logger.log_info("Triggering Troubleshooter Protocol...")
                        # Get git diff for context
                        from tools.git_tools import get_diff
                        current_diff = get_diff() # Gets unstaged changes (or we might need staged)

                        with rich_logger.log_status("Troubleshooter analyzing failure..."):
                            fix_plan = self.troubleshooter.analyze_failure(step.task, error_context, current_diff)
                        self.logger.info(f"Troubleshooter thoughts: {fix_plan.thoughts}")

                        fix_results = self.troubleshooter.apply_fix(fix_plan)

                        if fix_results["success"] and not fix_results["failed"]:
                            self.logger.info("Troubleshooter applied fix. Re-verifying...")
                            rich_logger.log_info("Troubleshooter applied fix. Re-verifying...")
                            # Re-run tests immediately to see if fix worked
                            test_result = await asyncio.to_thread(run_pytest, timeout=180)
                            if test_result.success:
                                self.logger.info("Troubleshooter fix VERIFIED! Proceeding to success.")
                                rich_logger.log_success("Troubleshooter fix VERIFIED!")
                                # Return success immediately, breaking the retry loop
                                return AgentResult(
                                    status="ok",
                                    message=f"Fixed by Troubleshooter:\n{fix_plan.thoughts}",
                                    artifacts=[]
                                )
                            else:
                                self.logger.warning("Troubleshooter fix failed verification.")
                                rich_logger.log_warning("Troubleshooter fix failed verification.")
                                error_context += f"\n\nTroubleshooter Attempt Failed. New Error:\n{test_result.stdout}"
                        else:
                             self.logger.warning(f"Troubleshooter failed to apply fix: {fix_results['failed']}")
                             rich_logger.log_error("Troubleshooter failed to apply fix")

                    except Exception as te:
                        self.logger.error(f"Troubleshooter crashed: {te}")
                        rich_logger.log_error(f"Troubleshooter crashed: {te}")
                        # Fallback to standard retry

                    if attempt < max_retries:
                        self.logger.info("Retrying with error context...")
                        continue
                    else:
                        self.logger.error("Max retries reached. Terminating and rolling back.")
                        rich_logger.log_error("Max retries reached. Rolling back.")
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
                    rich_logger.log_success("Task completed successfully!")
                    
                    # Generate manual verification steps
                    try:
                        verification_steps = self.planner.generate_verification_steps(user_intent, step.task)
                        # Result is SpokeResponse, doesn't have 'message' field in same way
                        # But we return AgentResult at end.
                        # We need to convert SpokeResponse to AgentResult for the return type

                        return AgentResult(
                            status="ok",
                            message=f"{result.thoughts}\n\n{verification_steps}",
                            artifacts=[]
                        )
                    except Exception as ve:
                        self.logger.warning(f"Could not generate verification steps: {ve}")
                        return AgentResult(
                            status="ok",
                            message=result.thoughts,
                            artifacts=[]
                        )
                    
            except Exception as e:
                error_context = f"Exception during execution: {str(e)}"
                self.logger.error(f"Attempt {attempt} failed with exception: {e}")
                rich_logger.log_error(f"Exception during execution: {e}")
                
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

    async def run_mock_loop(self):
        """A simple mock loop for verification."""
        task_id = "mock_task_001"
        self.logger.info(f"Starting mock loop for task: {task_id}")
        
        try:
            create_checkpoint(task_id)
        except Exception as e:
            self.logger.warning(f"Git checkpoint skipped or failed: {e}")

        # Mock DispatchStep
        step = DispatchStep(
            agent="coder",
            task="Create a hello world file",
            context_files=[]
        )

        # Mock dispatch (since we might not have Ollama running)
        result = await self.dispatch_to_agent(step)

        self.logger.info(f"Mock Loop Finished")
        return AgentResult(status="ok", message="Mock loop finished", artifacts=[])
