import unittest
from unittest.mock import MagicMock, patch
from core.hub import Spine
from core.specs import DispatchStep, KnowledgeSummary, FeasibilityCheck
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
             patch('core.hub.GeminiClient', return_value=self.mock_planner), \
             patch('core.hub.TaskQueue'):

            self.spine = Spine()
            # Inject our mock planner explicitly just in case
            self.spine.planner = self.mock_planner
            self.spine.scorer = self.mock_scorer

    def test_negotiation_loop_success(self):
        """Test that negotiation stops when consensus is reached."""

        # 1. Initial Plan
        initial_plan = DispatchStep(
            agent_name="coder",
            task_description="Build a spaceship",
            context_files=[]
        )
        self.mock_planner.generate_plan.return_value = initial_plan

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
        self.mock_planner.generate_plan.return_value = initial_plan

        # 2. Researcher Feedback (Bad then Good)
        bad_summary = KnowledgeSummary(
            relevant_files=[],
            technical_constraints=["No fuel"],
            missing_information=[],
            feasibility_score=0.4
        )
        good_summary = KnowledgeSummary(
            relevant_files=[],
            technical_constraints=[],
            missing_information=[],
            feasibility_score=0.95
        )

        mock_result_bad = MagicMock()
        mock_result_bad.thoughts = bad_summary.model_dump_json()

        mock_result_good = MagicMock()
        mock_result_good.thoughts = good_summary.model_dump_json()

        self.spine.dispatch_to_agent = MagicMock(side_effect=[mock_result_bad, mock_result_good])

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
