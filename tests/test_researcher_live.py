import os
import json
import logging
import pytest
from core.hub import Spine
from core.specs import DispatchStep, ResearcherOutput
from core.config import setup_logging

@pytest.mark.asyncio
async def test_live_researcher():
    setup_logging()
    logger = logging.getLogger(__name__)
    
    # Ensure SKIP_RESOURCE_CHECK is true for testing
    os.environ["SKIP_RESOURCE_CHECK"] = "true"
    
    try:
        # We need to mock Ollama or actually have it running. 
        # Since this is a 'live' test, we assume Ollama is running or we mock it if it fails.
        spine = Spine()
        
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

        # Mock the actual Ollama call if we are in environment without Ollama
        # But for 'live' test we usually want real calls.
        # For CI safety, let's mock it if it's not a real live run.
        if os.getenv("REAL_LIVE_TEST") != "true":
             from unittest.mock import AsyncMock
             spine.researcher.handle_task = AsyncMock(return_value=ResearcherOutput(
                project_overview={"name": "test", "primary_language": "py", "frameworks": [], "runtime_targets": [], "build_system": ""},
                structure_map={"entry_points": [], "core_modules": []},
                hard_constraints={"framework_versions": {}, "external_interfaces": [], "cannot_change": []},
                soft_constraints={"coding_patterns": [], "style_conventions": [], "existing_abstractions": [], "tech_debt_notes": []},
                known_unknowns={"missing_context": [], "ambiguous_areas": []},
                planner_guardrails={"do_not_assume": [], "requires_validation": []},
                evidence_index={"files_examined": [], "configs_examined": [], "commands_run": []}
             ))

        result = await spine.dispatch_to_agent(research_step)
        
        assert isinstance(result, ResearcherOutput)

    except Exception as e:
        pytest.fail(f"LIVE TEST FAILED: {str(e)}")
