
import logging
import sys
import json
from unittest.mock import MagicMock, patch
from core.hub import Spine
from core.specs import DispatchStep, AgentResult

# Configure logging to stdout
logging.basicConfig(level=logging.INFO, format='%(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("e2e_verify")

def mock_ollama_response(*args, **kwargs):
    """Returns a valid JSON response matching the new Researcher schema."""
    logger.info("MOCK: Intercepted request to Ollama")
    
    # Verify the prompt contains the project context
    json_body = kwargs.get("json", {})
    messages = json_body.get("messages", [])
    user_content = next((m["content"] for m in messages if m["role"] == "user"), "")
    
    if "Project Structure" in user_content:
        logger.info("VERIFIED: Project Context WAS included in the prompt!")
    else:
        logger.error("FAILED: Project Context was NOT found in the prompt.")

    schema_response = {
        "project_overview": {
            "name": "LLM Master Slave",
            "primary_language": "Python",
            "frameworks": ["Tenacity", "Pydantic"],
            "runtime_targets": ["Windows"],
            "build_system": "None"
        },
        "structure_map": {
            "entry_points": [{"path": "main.py", "type": "script", "notes": "Entry point"}],
            "core_modules": [{"path": "core/hub.py", "responsibility": "Orchestration", "dependencies": ["core/spokes.py"]}]
        },
        "hard_constraints": {
            "language_version": "3.11",
            "framework_versions": {},
            "external_interfaces": [],
            "cannot_change": ["core/hub.py logic"]
        },
        "soft_constraints": {
            "coding_patterns": ["Functional"],
            "style_conventions": ["PEP8"],
            "existing_abstractions": [],
            "tech_debt_notes": []
        },
        "known_unknowns": {
            "missing_context": [],
            "ambiguous_areas": []
        },
        "planner_guardrails": {
            "do_not_assume": ["API Keys present"],
            "requires_validation": []
        },
        "evidence_index": {
            "files_examined": ["main.py"],
            "configs_examined": [],
            "commands_run": []
        }
    }
    
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"message": {"content": json.dumps(schema_response)}}
    return mock_resp

@patch("core.hub.load_config")
@patch("core.hub.setup_logging")
@patch("core.hub.GeminiClient")
@patch("httpx.Client.post", side_effect=mock_ollama_response)
def run_verification(mock_post, mock_planner_cls, mock_setup, mock_config):
    logger.info("Starting E2E Verification...")
    
    # Mock Config with "dirty" URL to test robustness
    mock_config.return_value = {
        "OLLAMA_BASE_URL": "http://localhost:11434/v1",
        "CODER_MODEL": "llama3", 
        "REVIEWER_MODEL": "llama3"
    }
    
    # Setup Spine
    spine = Spine()
    
    # Mock Planner to return a basic plan
    mock_planner_instance = MagicMock()
    mock_planner_instance.generate_plan.return_value = DispatchStep(
        agent_name="coder",
        task_description="Implement feature X",
        context=[]
    )
    # Ensure refine_plan returns the same plan to exit loop if needed
    mock_planner_instance.refine_plan.return_value = DispatchStep(
        agent_name="coder",
        task_description="Implement feature X (Refined)",
        context=[]
    )
    mock_planner_cls.return_value = mock_planner_instance
    
    # Mock Scorer to force consensus or refinement
    # Let's return low score first to verify loop, but for simplicity let's just match
    spine.scorer = MagicMock()
    spine.scorer.evaluate.return_value = 0.95 
    
    logger.info("Invoking _negotiate_plan...")
    final_plan = spine._negotiate_plan("I want to add a feature")
    
    logging.info(f"Negotiation Complete. Final Plan Task: {final_plan.task}")
    
    if mock_post.called:
        logger.info("SUCCESS: Ollama was called.")
    else:
        logger.error("FAILURE: Ollama was NOT called.")

if __name__ == "__main__":
    run_verification()
