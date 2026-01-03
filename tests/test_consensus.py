import unittest
from unittest.mock import MagicMock, patch
from core.hub import Spine
from core.specs import DispatchStep, ResearcherOutput, FeasibilityCheck
from core.consensus import ConsensusScorer

class TestConsensusLoop(unittest.TestCase):
    def setUp(self):
        # Mock dependencies
        self.mock_planner = MagicMock()
        self.mock_scorer = ConsensusScorer()

        # Patch Spine to avoid real initializations
        with patch('core.hub.load_config', return_value={}), \
             patch('core.hub.setup_logging'), \
             patch('core.hub.CoderSpoke'), \
             patch('core.hub.ReviewerSpoke'), \
             patch('core.hub.ResearcherSpoke'), \
             patch('core.hub.Troubleshooter'), \
             patch('core.hub.GeminiClient', return_value=self.mock_planner), \
             patch('core.hub.TaskQueue'):

            self.spine = Spine()
            # Inject our mock planner explicitly just in case
            self.spine.planner = self.mock_planner
            self.spine.scorer = self.mock_scorer

    def _get_mock_researcher_output(self):
        # We don't actually use score inside ResearcherOutput,
        # the ConsensusScorer evaluates the output against the plan.
        # So we just return a valid structure.
        return ResearcherOutput(
            project_overview={
                "name": "Test", "primary_language": "Python", "frameworks": [],
                "runtime_targets": [], "build_system": None
            },
            structure_map={"entry_points": [], "core_modules": []},
            hard_constraints={"framework_versions": {}, "external_interfaces": [], "cannot_change": []},
            soft_constraints={"coding_patterns": [], "style_conventions": [], "existing_abstractions": [], "tech_debt_notes": []},
            known_unknowns={"missing_context": [], "ambiguous_areas": []},
            planner_guardrails={"do_not_assume": [], "requires_validation": []},
            evidence_index={"files_examined": [], "configs_examined": [], "commands_run": []}
        )

    def test_negotiation_loop_success(self):
        """Test that negotiation stops when consensus is reached."""

        # 1. Initial Plan
        initial_plan = DispatchStep(
            agent_name="coder",
            task_description="Build a spaceship",
            context_files=[]
        )
        self.mock_planner.generate_plan.return_value = initial_plan

        # 2. Researcher Feedback
        # The dispatch_to_agent now returns a ResearcherOutput object directly
        researcher_output = self._get_mock_researcher_output()
        self.spine.dispatch_to_agent = MagicMock(return_value=researcher_output)

        # Mock Consensus Scorer to return high score
        self.spine.scorer.evaluate = MagicMock(return_value=0.9)

        # Execute
        final_plan = self.spine._negotiate_plan("Build a spaceship")

        # Verify
        self.assertEqual(final_plan.task, "Build a spaceship")
        # Should only run 1 turn because score is high
        self.assertEqual(self.spine.dispatch_to_agent.call_count, 1)

    def test_negotiation_loop_refinement(self):
        """Test that negotiation refines plan when score is low."""

        # 1. Initial Plan
        initial_plan = DispatchStep(
            agent_name="coder",
            task_description="Build a spaceship",
            context_files=[]
        )
        self.mock_planner.generate_plan.return_value = initial_plan

        # 2. Researcher Feedback
        researcher_output = self._get_mock_researcher_output()
        self.spine.dispatch_to_agent = MagicMock(return_value=researcher_output)

        # Mock Consensus Scorer to return LOW then HIGH
        self.spine.scorer.evaluate = MagicMock(side_effect=[0.4, 0.9])

        # Mock Refinement
        refined_plan = DispatchStep(
            agent_name="coder",
            task_description="Build a glider instead",
            context_files=[]
        )
        self.mock_planner.refine_plan.return_value = refined_plan

        # Execute
        final_plan = self.spine._negotiate_plan("Build a spaceship")

        # Verify
        self.assertEqual(final_plan.task, "Build a glider instead")
        self.assertEqual(self.spine.dispatch_to_agent.call_count, 2)
        self.mock_planner.refine_plan.assert_called_once()

if __name__ == '__main__':
    unittest.main()
