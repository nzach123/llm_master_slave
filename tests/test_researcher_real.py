
import unittest
from unittest.mock import MagicMock, patch
import json
from core.hub import Spine
from core.specs import ResearcherOutput, DispatchStep, ProjectOverview, StructureMap, HardConstraints, SoftConstraints, KnownUnknowns, PlannerGuardrails, EvidenceIndex, FeasibilityCheck

class TestResearcherNegotiation(unittest.TestCase):
    @patch("core.hub.get_project_context")
    @patch("core.hub.os.path.exists") 
    @patch("core.hub.load_config")
    @patch("core.hub.setup_logging")
    @patch("core.hub.GeminiClient")
    def test_negotiation_flow(self, mock_planner_cls, mock_logging, mock_config, mock_exists, mock_get_context):
        # Setup mocks
        mock_config.return_value = {"OLLAMA_BASE_URL": "http://mock", "CODER_MODEL": "mock", "REVIEWER_MODEL": "mock"}
        
        # Mock Planner instance
        mock_planner = MagicMock()
        mock_planner_cls.return_value = mock_planner
        mock_get_context.return_value = "├── file1.py\n└── file2.py"
        mock_exists.return_value = False # Don't try to read GEMINI.md relevant here
        
        spine = Spine()
        # spine.planner is now the mock instance returned by mock_planner_cls
        spine.planner.generate_plan.return_value = DispatchStep(agent="coder", task="Do something")
        spine.scorer = MagicMock()
        spine.scorer.evaluate.return_value = 0.9 # High score to exit loop
        
        # Mock the dispatch_to_agent to return a valid ResearcherOutput
        mock_output = ResearcherOutput(
            project_overview=ProjectOverview(
                primary_language="Python",
                frameworks=["Flask"],
                runtime_targets=["Windows"],
                name="TestProject"
            ),
            structure_map=StructureMap(entry_points=[], core_modules=[]),
            hard_constraints=HardConstraints(framework_versions={}, external_interfaces=[], cannot_change=[]),
            soft_constraints=SoftConstraints(coding_patterns=[], style_conventions=[], existing_abstractions=[], tech_debt_notes=[]),
            known_unknowns=KnownUnknowns(missing_context=[], ambiguous_areas=[]),
            planner_guardrails=PlannerGuardrails(do_not_assume=[], requires_validation=[]),
            evidence_index=EvidenceIndex(files_examined=[], configs_examined=[], commands_run=[])
        )
        
        spine.dispatch_to_agent = MagicMock(return_value=mock_output)
        
        # Execute
        plan = spine._negotiate_plan("User intent")
        
        # Verify
        spine.dispatch_to_agent.assert_called()
        call_args = spine.dispatch_to_agent.call_args[0][0] # The DispatchStep
        self.assertIn("Project Structure", call_args.context_files[0])
        self.assertEqual(call_args.agent, "researcher")
        
        spine.scorer.evaluate.assert_called()
        # Verify scorer received the ResearcherOutput in the feedback
        feedback_arg = spine.scorer.evaluate.call_args[0][1] # FeasibilityCheck
        self.assertIsInstance(feedback_arg, FeasibilityCheck)
        self.assertIsInstance(feedback_arg.summary, ResearcherOutput)
        self.assertEqual(feedback_arg.summary.project_overview.primary_language, "Python")

if __name__ == "__main__":
    unittest.main()
