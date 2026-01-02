
import os
import json
import logging
from core.hub import Spine
from core.specs import DispatchStep, ResearcherOutput
from core.config import setup_logging

def test_live_researcher():
    setup_logging()
    logger = logging.getLogger(__name__)
    
    # Ensure SKIP_RESOURCE_CHECK is true for testing
    os.environ["SKIP_RESOURCE_CHECK"] = "true"
    
    try:
        spine = Spine()
        if not spine.planner:
            print("ERROR: Planner not initialized.")
            return

        print("DEBUG: Dispatching live research task...")
        
        from tools.context import get_project_context
        project_tree = get_project_context(".", max_depth=2)
        
        context_text = f"Project Structure:\n{project_tree}\n"
        if os.path.exists("GEMINI.md"):
            with open("GEMINI.md", "r", encoding="utf-8") as f:
                context_text += f"\nGEMINI.md:\n{f.read()}\n"

        research_step = DispatchStep(
            agent="researcher",
            task="Analyze the current project structure and identify the primary language and core modules.",
            context_files=[context_text]
        )

        # We will manually call handle_task to see the raw output if needed
        # but dispatch_to_agent should handle it.
        # Let's monkeypatch ResearcherSpoke.handle_task briefly to print raw JSON
        original_handle = spine.researcher.handle_task
        def patched_handle(step):
            # This is a bit hacky but works for local debug
            try:
                # We can't easily call original_handle because it validates.
                # Let's just catch the error in Spine.dispatch_to_agent or similar.
                return original_handle(step)
            except Exception as e:
                print(f"DEBUG: Validation failed. Error: {e}")
                raise e

        spine.researcher.handle_task = patched_handle

        result = spine.dispatch_to_agent(research_step)
        
        print("\nSUCCESS: Researcher Output Received:")
        print(json.dumps(result.model_dump(), indent=2))
        
        assert isinstance(result, ResearcherOutput)
        print("\nLIVE TEST PASSED!")

    except Exception as e:
        print(f"\nFAILURE: LIVE TEST FAILED: {str(e)}")

if __name__ == "__main__":
    test_live_researcher()
