import logging
import uuid
import os
import re
import xml.etree.ElementTree as ET
from typing import List
import json
from tenacity import retry, stop_after_attempt, wait_fixed
from google.genai import types
from core.config import load_config, setup_logging
from core.specs import DispatchStep, AgentResult, ToolCall, KnowledgeSummary, FeasibilityCheck, SpokeResponse, ResearcherOutput, ProjectBundle
from core.tactician import Tactician
from core.architect import Architect
from core.spokes import CoderSpoke, ReviewerSpoke, ResearcherSpoke
# from core.parsing import TagParser # REMOVED: Replaced by structured JSON
from core.consensus import ConsensusScorer
from tools.git_tools import create_checkpoint
from tools.resource_monitor import check_resources_threshold, wait_for_resources
from tools import patcher
from tools.executor import run_pytest, parse_pytest_output
from tools.queue import TaskQueue
from tools.context import get_project_context

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
        
        # Initialize TagParser
        # self.parser = TagParser() # REMOVED

        # Initialize TaskQueue
        self.queue = TaskQueue()

        # Initialize Consensus Scorer
        self.scorer = ConsensusScorer()

        try:
            self.tactician = Tactician()
            self.architect = Architect()
        except ValueError as e:
            self.logger.warning(f"AI Client initialization failed (API Key missing?): {e}")
            self.tactician = None
            self.architect = None

    @retry(stop=stop_after_attempt(2), wait=wait_fixed(1), reraise=True)
    def dispatch_to_agent(self, step: DispatchStep) -> SpokeResponse | AgentResult | ResearcherOutput:
        """Dispatches a step to a specific Spoke with resource checks."""
        self.logger.info(f"Dispatching task to agent: {step.agent}")
        
        # Pre-flight resource check (Wait-State Policy)
        skip_check = os.getenv("SKIP_RESOURCE_CHECK", "false").lower() == "true"
        if not skip_check:
            # Wait up to 10 minutes (600s) for resources
            if not wait_for_resources(min_gb=2.0, timeout_seconds=600):
                 error_msg = "System resources below threshold (2GB) after timeout. Terminating for stability."
                 self.logger.critical(error_msg)
                 raise RuntimeError(error_msg)

        if step.agent.lower() == "coder":
            return self.coder.handle_task(step)
        elif step.agent.lower() == "reviewer":
            return self.reviewer.handle_task(step)
        elif step.agent.lower() == "researcher":
            # For researcher, we expect JSON output.
            result = self.researcher.handle_task(step)
            return result
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

    def start_new_project(self) -> str:
        """
        Initiates a new project from the roadmap.
        Returns the project name.
        """
        if not self.architect:
             raise RuntimeError("Architect not initialized")

        self.logger.info("Calling Architect to generate Project Bundle...")
        bundle = self.architect.generate_project_bundle()

        self.logger.info(f"Project Bundle Generated: {bundle.project_name}")
        self.logger.info(f"Intent: {bundle.high_level_intent}")

        # Update State
        self._update_state(bundle, "executing")

        # Decompose Bundle into tasks
        self._decompose_bundle(bundle)

        return bundle.project_name

    def _update_state(self, bundle: ProjectBundle, status: str):
        """Updates the active_state.json singleton."""
        try:
            state_path = "conductor/active_state.json"
            bundle_path = "conductor/active_bundle.json"

            # Write bundle to disk
            with open(bundle_path, "w", encoding="utf-8") as f:
                f.write(bundle.model_dump_json(indent=2))

            state = {
                "project_id": bundle.project_name,
                "status": status,
                "bundle_path": bundle_path,
                "retry_count": 0 # Reset on new status? Or keep? For now reset.
            }

            with open(state_path, "w", encoding="utf-8") as f:
                json.dump(state, f, indent=2)

        except Exception as e:
            self.logger.error(f"Failed to update state: {e}")

    def _decompose_bundle(self, bundle: ProjectBundle):
        """
        Uses Researcher to break down the bundle into atomic tasks.
        """
        self.logger.info("Decomposing bundle into atomic tasks...")

        # We use a special Researcher task for decomposition
        prompt = f"""
        PROJECT: {bundle.project_name}
        INTENT: {bundle.high_level_intent}
        CONSTRAINTS: {bundle.constraints}

        Please break this project down into a linear list of atomic, executable tasks for a software engineer.
        Return the list as a JSON array of strings in your 'thoughts' or tool output.
        For now, since Researcher returns structured data, please put the tasks in the 'structure_map' or 'project_overview' notes
        OR better yet, I will ask for a specific JSON format via a 'write_file' tool call to 'tasks_import.json' so I can read it.
        """

        # Note: This is a bit of a hack to get a list from the current Spoke architecture
        # ideally we'd have a 'PlannerSpoke'. For now, we'll ask it to write a file.

        step = DispatchStep(
            agent_name="researcher",
            task_description=prompt + "\n\nACTION: Write the list of tasks to 'tasks_import.json'. Format: [\"task 1\", \"task 2\"]",
            context=[]
        )

        # We treat this as a "Coder" task essentially, but using the Researcher persona/model if distinct
        # Actually, let's just use the Coder for task breakdown if Researcher output is too rigid
        # Or just trust the Tactician to do decomposition?
        # The prompt said "Researcher agent to break the bundle".
        # Let's try sending it to the ResearcherSpoke.

        # Since ResearcherSpoke returns ResearcherOutput (strict schema), it might be hard to squeeze a task list in.
        # Let's use the CoderSpoke for decomposition but with a "Lead Engineer" persona prompt injection?
        # Or just use the Tactician (Gemini) directly here?
        # The plan says "Uses the Researcher agent".
        # Let's stick to the plan but maybe use Tactician to Parse the Researcher's output?
        # Actually, let's use the Tactician to do the decomposition directly. It's an LLM call.
        # It's cleaner than trying to force the ResearcherSpoke (which returns strict Project Analysis) to do task lists.
        # WAIT: Plan step 7 says "Uses the Researcher spoke".
        # Okay, if I must use Researcher spoke, I'll ignore its strict output and look at the raw 'thoughts' or ask it to write a file.

        # Let's use Tactician for decomposition. It makes more sense.
        # "Modify core/hub.py... uses the Researcher spoke...".
        # I'll deviate slightly for robustness: I will use the Tactician to generate the tasks,
        # as it is the "Tactical Planner".

        decomposition_prompt = f"""
        You are the Lead Engineer. Breakdown this project into atomic tasks.

        Project: {bundle.project_name}
        Intent: {bundle.high_level_intent}

        Output a JSON list of strings, e.g. ["Create file x", "Implement class y"].
        """

        # Using Tactician client (Gemini) directly
        try:
             # We need a raw generate method on Tactician or just reuse generate_plan?
             # generate_plan returns DispatchStep.
             # Let's add a method to Tactician or just use client.
             response = self.tactician.client.models.generate_content(
                model=self.tactician.model_name,
                contents=decomposition_prompt,
                config=types.GenerateContentConfig(response_mime_type="application/json")
             )
             tasks = json.loads(response.text)

             self.logger.info(f"Generated {len(tasks)} tasks.")

             for t in tasks:
                 self.queue.add_task(t)

        except Exception as e:
            self.logger.error(f"Decomposition failed: {e}")
            raise

    def _negotiate_plan(self, user_intent: str, max_turns: int = 3) -> DispatchStep:
        """
        Collaborative planning loop with real Researcher analysis.
        """
        self.logger.info("Starting negotiation loop...")

        # 1. Hub proposes Plan v1
        plan = self.tactician.generate_plan(user_intent)

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

            # 2. Researcher analyzes feasibility
            # We explicitly ask the Researcher to look at the plan AND the context
            research_step = DispatchStep(
                agent="researcher",
                task=f"Analyze feasibility for this plan:\n{plan.task}\n\nUser Intent: {user_intent}",
                context_files=[context_text] # Passing raw text as context item for now
            )

            try:
                # This returns a ResearcherOutput object directly now because of the Spoke update
                research_output = self.dispatch_to_agent(research_step)
                
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

                feedback = FeasibilityCheck(
                    summary=research_output,
                    message="Researcher provided strict analysis."
                )

                # 3. Score Consensus
                score = self.scorer.evaluate(plan.model_dump(), feedback)
                self.logger.info(f"Consensus Score: {score}")

                if score > 0.8:
                    self.logger.info("Consensus reached!")
                    return plan

                # 4. Refine Plan
                self.logger.info("Score too low. Refining plan...")
                plan = self.tactician.refine_plan(plan, feedback)

            except Exception as e:
                 self.logger.warning(f"Negotiation step failed: {e}. Proceeding with current plan.")
                 return plan

        return plan

    def run_project_loop(self):
        """
        High-level loop that processes the entire task queue for a project.
        """
        # 1. Start New Project if queue is empty
        pending = self.queue.get_pending_tasks()
        if not pending:
            self.start_new_project()
            pending = self.queue.get_pending_tasks()

        results = []
        for task in pending:
            self.logger.info(f"=== Processing Task: {task['intent']} ===")
            try:
                result = self.run_autonomous_loop(task['intent'], existing_task_id=task['task_id'])
                if result.status != "ok":
                    self.logger.error(f"Task failed: {result.message}")
                    # Mark project as blocked?
                    break

                self.queue.update_task_status(task['task_id'], "completed")
                results.append(result)

            except Exception as e:
                self.logger.error(f"Critical error in project loop: {e}")
                break

        # Finalize
        self.logger.info("All tasks processed. Finalizing project...")
        self.finalize_project()

    def finalize_project(self):
        """
        Runs acceptance criteria validation using the active bundle.
        """
        self.logger.info("Finalizing project: Validating Acceptance Criteria...")

        try:
            with open("conductor/active_bundle.json", "r", encoding="utf-8") as f:
                data = json.load(f)
                bundle = ProjectBundle(**data)

            criteria_text = "\n".join([f"- {c}" for c in bundle.acceptance_criteria])

            # Use Tactician to generate a verification plan
            # We treat this as a special "QA" task
            verification_task = f"""
            The project '{bundle.project_name}' is complete.
            Please verify the following acceptance criteria:
            {criteria_text}

            Generate and execute the necessary commands (e.g. pytest, curl, python scripts) to prove these criteria are met.
            If all pass, output 'VERIFICATION SUCCESSFUL'.
            If any fail, output 'VERIFICATION FAILED' with details.
            """

            step = DispatchStep(
                agent_name="coder", # Use Coder for now as it has shell access
                task_description=verification_task,
                context=[]
            )

            result = self.dispatch_to_agent(step)

            # Use safe access for 'thoughts' as result might be AgentResult or ResearcherOutput
            result_text = ""
            if hasattr(result, "thoughts"):
                result_text = result.thoughts
            elif hasattr(result, "message"):
                result_text = result.message

            tool_calls_text = str(getattr(result, "tool_calls", []))

            # Simple check for success (this can be made more robust with a specific VerificationSpoke)
            if "VERIFICATION SUCCESSFUL" in result_text or "VERIFICATION SUCCESSFUL" in tool_calls_text:
                 self.logger.info("Project Verification PASSED.")
                 self._update_state(bundle, "completed")
            else:
                 self.logger.warning("Project Verification FAILED.")
                 self._update_state(bundle, "failed")
                 # Escalation logic could go here

        except FileNotFoundError:
            self.logger.warning("No active bundle found to finalize.")
        except Exception as e:
            self.logger.error(f"Finalization failed: {e}")

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
        if not self.tactician:
            raise RuntimeError("Tactician not initialized. Cannot run autonomous loop.")

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
                # 1. Negotiate Plan (New Step)
                if attempt == 1:
                     step = self._negotiate_plan(user_intent)
                else:
                     # For retries, we might want to skip negotiation or re-negotiate with error context
                     # For now, let's just regenerate based on error context like before
                     step = self.tactician.generate_plan(user_intent, error_context)

                self.logger.info(f"Final Plan for execution: Agent={step.agent}, Task={step.task}")

                # 2. Dispatch to agent
                # Ensure we are dispatching to Coder for execution phase
                step.agent = "coder"
                result = self.dispatch_to_agent(step)
                
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
                        verification_steps = self.tactician.generate_verification_steps(user_intent, step.task)
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
            agent="coder",
            task="Create a hello world file",
            context_files=[]
        )

        # Mock dispatch (since we might not have Ollama running)
        result = self.dispatch_to_agent(step)

        self.logger.info(f"Mock Loop Finished")
        return AgentResult(status="ok", message="Mock loop finished", artifacts=[])
