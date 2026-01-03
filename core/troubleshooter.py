import logging
from core.spokes import TroubleshooterSpoke
from core.specs import DispatchStep, SpokeResponse, ToolCall
from tools import patcher

class Troubleshooter:
    def __init__(self, base_url: str, model: str):
        self.logger = logging.getLogger(__name__)
        # Ensure we pass the base_url and model correctly to the spoke
        # The Spoke implementation expects base_url and model.
        # We need to make sure we don't pass None if config is missing
        self.spoke = TroubleshooterSpoke(base_url or "http://localhost:11434/api", model or "qwen2.5-coder:7b")

    def analyze_failure(self, task: str, error_context: str, diff: str = None) -> SpokeResponse:
        """
        Analyzes a failure using the TroubleshooterSpoke.
        """
        self.logger.info("Engaging Troubleshooter...")

        # Construct the context for the troubleshooter
        context_text = f"""
ERROR CONTEXT:
{error_context}

RECENT DIFF (Potential Cause):
{diff if diff else "No diff available."}
"""

        step = DispatchStep(
            agent_name="troubleshooter",
            task_description=f"Fix the failure in task: {task}",
            context=[context_text]
        )

        try:
            # We bypass the generic dispatch mechanism to call the spoke directly
            # or we could add it to Spine.dispatch_to_agent.
            # Calling directly here for cleaner separation.
            response = self.spoke.handle_task(step)
            return response
        except Exception as e:
            self.logger.error(f"Troubleshooter failed to analyze: {e}")
            raise

    def apply_fix(self, response: SpokeResponse) -> dict:
        """
        Executes the fix proposed by the Troubleshooter.
        """
        self.logger.info("Applying Troubleshooter Fix...")
        results = {"success": [], "failed": []}

        for tool_call in response.tool_calls:
            try:
                if tool_call.action == "write_file":
                    if tool_call.content is None:
                         raise ValueError("Content missing for write_file")
                    patcher.write_file(tool_call.path, tool_call.content)
                    results["success"].append(f"Wrote {tool_call.path}")

                elif tool_call.action == "apply_patch":
                    if tool_call.search is None or tool_call.replace is None:
                        raise ValueError("Search or replace block missing for apply_patch")

                    success = patcher.apply_patch(
                        tool_call.path,
                        tool_call.search,
                        tool_call.replace
                    )
                    if success:
                        results["success"].append(f"Patched {tool_call.path}")
                    else:
                        results["failed"].append(
                            f"Patch failed for {tool_call.path}"
                        )
                # Add other actions if needed

            except Exception as e:
                error_msg = f"Error executing {tool_call.action} on {tool_call.path}: {str(e)}"
                results["failed"].append(error_msg)
                self.logger.error(error_msg)

        return results
