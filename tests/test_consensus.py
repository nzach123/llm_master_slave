import unittest
from unittest.mock import MagicMock, patch
from core.hub import Spine
from core.specs import DispatchStep, KnowledgeSummary, FeasibilityCheck
from core.consensus import ConsensusScorer

class TestConsensusLoop(unittest.TestCase):
    def setUp(self):
        # Mock dependencies
        self.mock_tactician = MagicMock()
        self.mock_architect = MagicMock()
        self.mock_scorer = ConsensusScorer()

        # Patch Spine to avoid real initializations
        with patch('core.hub.load_config', return_value={}), \
             patch('core.hub.setup_logging'), \
             patch('core.hub.CoderSpoke'), \
             patch('core.hub.ReviewerSpoke'), \
             patch('core.hub.ResearcherSpoke'), \
             patch('core.hub.Tactician', return_value=self.mock_tactician), \
             patch('core.hub.Architect', return_value=self.mock_architect), \
             patch('core.hub.TaskQueue'):

            self.spine = Spine()
            # Inject our mock planner explicitly just in case
            self.spine.tactician = self.mock_tactician
            self.spine.architect = self.mock_architect
            self.spine.scorer = self.mock_scorer

    def test_negotiation_loop_success(self):
        """Test that negotiation stops when consensus is reached."""

        # 1. Initial Plan
        initial_plan = DispatchStep(
            agent_name="coder",
            task_description="Build a spaceship",
            context_files=[]
        )
        self.mock_tactician.generate_plan.return_value = initial_plan

        # 2. Researcher Feedback (Good)
        summary = KnowledgeSummary(
            relevant_files=[],
            technical_constraints=[],
            missing_information=[],
            feasibility_score=0.9
        )
        feedback_json = summary.model_dump_json()

        # Mock dispatcher to return Researcher feedback
        mock_result = MagicMock()
        mock_result.thoughts = feedback_json
        self.spine.dispatch_to_agent = MagicMock(return_value=mock_result)

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
        self.mock_tactician.generate_plan.return_value = initial_plan

        # 2. Researcher Feedback (Bad then Good)
        # Note: Hub expects ResearcherOutput now, not KnowledgeSummary.
        # But for mocking simplicity, we need to ensure the mock object behaves like ResearcherOutput.

        # We need to construct a valid ResearcherOutput model, but it's complex.
        # Instead, we will mock the return value of dispatch_to_agent to be a ResearcherOutput object directly.

        from core.specs import ResearcherOutput, ProjectOverview, StructureMap, HardConstraints, SoftConstraints, KnownUnknowns, PlannerGuardrails, EvidenceIndex

        # Helper to create dummy output
        def create_output(files, constraints):
            return ResearcherOutput(
                project_overview=ProjectOverview(primary_language="python", frameworks=[], runtime_targets=[]),
                structure_map=StructureMap(entry_points=[], core_modules=[]),
                hard_constraints=HardConstraints(framework_versions={}, external_interfaces=[], cannot_change=constraints),
                soft_constraints=SoftConstraints(coding_patterns=[], style_conventions=[], existing_abstractions=[], tech_debt_notes=[]),
                known_unknowns=KnownUnknowns(missing_context=[], ambiguous_areas=[]),
                planner_guardrails=PlannerGuardrails(do_not_assume=[], requires_validation=[]),
                evidence_index=EvidenceIndex(files_examined=files, configs_examined=[], commands_run=[])
            )

        output_bad = create_output([], ["No fuel"])
        output_good = create_output([], [])

        self.spine.dispatch_to_agent = MagicMock(side_effect=[output_bad, output_good])

        # Mock Refinement
        refined_plan = DispatchStep(
            agent_name="coder",
            task_description="Build a glider instead",
            context_files=[]
        )
        self.mock_tactician.refine_plan.return_value = refined_plan

        # Execute
        final_plan = self.spine._negotiate_plan("Build a spaceship")

        # Verify
        self.assertEqual(final_plan.task, "Build a glider instead")
        self.assertEqual(self.spine.dispatch_to_agent.call_count, 2)
        self.mock_tactician.refine_plan.assert_called_once()

if __name__ == '__main__':
    unittest.main()
