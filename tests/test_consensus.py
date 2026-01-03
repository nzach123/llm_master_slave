import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from core.hub import Spine
from core.specs import DispatchStep, ResearcherOutput, FeasibilityCheck, ProjectOverview, StructureMap, HardConstraints, SoftConstraints, KnownUnknowns, PlannerGuardrails, EvidenceIndex
from core.judge import JudgeResult

@pytest.mark.asyncio
async def test_negotiation_loop_success():
    """Test that negotiation stops when consensus is reached."""
    # Mock dependencies
    mock_planner = MagicMock()
    
    # Patch Spine to avoid real initializations
    with patch('core.hub.load_config', return_value={}), \
         patch('core.hub.setup_logging'), \
         patch('core.hub.CoderSpoke'), \
         patch('core.hub.ReviewerSpoke'), \
         patch('core.hub.ResearcherSpoke'), \
         patch('core.hub.Troubleshooter'), \
         patch('core.hub.GeminiClient', return_value=mock_planner), \
         patch('core.hub.TaskQueue'):

        spine = Spine()
        spine.planner = mock_planner

        # 1. Initial Plan
        initial_plan = DispatchStep(
            agent="coder",
            task="Build a spaceship",
            context_files=[]
        )
        mock_planner.generate_plan.return_value = initial_plan

        # 2. Researcher Feedback
        mock_researcher_output = ResearcherOutput(
            project_overview=ProjectOverview(name="test", primary_language="py", frameworks=[], runtime_targets=[], build_system=""),
            structure_map=StructureMap(entry_points=[], core_modules=[]),
            hard_constraints=HardConstraints(language_version="", framework_versions={}, external_interfaces=[], cannot_change=[]),
            soft_constraints=SoftConstraints(coding_patterns=[], style_conventions=[], existing_abstractions=[], tech_debt_notes=[]),
            known_unknowns=KnownUnknowns(missing_context=[], ambiguous_areas=[]),
            planner_guardrails=PlannerGuardrails(do_not_assume=[], requires_validation=[]),
            evidence_index=EvidenceIndex(files_examined=[], configs_examined=[], commands_run=[])
        )

        with patch.object(spine, "dispatch_to_agent", new_callable=AsyncMock) as mock_dispatch:
            mock_dispatch.side_effect = [
                mock_researcher_output,
                JudgeResult(score=0.9, reasoning="good", decision="APPROVE")
            ]

            # Execute
            final_plan = await spine._negotiate_plan("Build a spaceship")

            # Verify
            assert final_plan.task == "Build a spaceship"
            # Should run researcher (1) + judge (1) = 2 calls
            assert mock_dispatch.call_count == 2

@pytest.mark.asyncio
async def test_negotiation_loop_refinement():
    """Test that negotiation refines plan when score is low."""
    mock_planner = MagicMock()
    
    with patch('core.hub.load_config', return_value={}), \
         patch('core.hub.setup_logging'), \
         patch('core.hub.CoderSpoke'), \
         patch('core.hub.ReviewerSpoke'), \
         patch('core.hub.ResearcherSpoke'), \
         patch('core.hub.Troubleshooter'), \
         patch('core.hub.GeminiClient', return_value=mock_planner), \
         patch('core.hub.TaskQueue'):

        spine = Spine()
        spine.planner = mock_planner

        # 1. Initial Plan
        initial_plan = DispatchStep(
            agent="coder",
            task="Build a spaceship",
            context_files=[]
        )
        mock_planner.generate_plan.return_value = initial_plan

        # 2. Researcher Feedback
        mock_researcher_output = ResearcherOutput(
            project_overview=ProjectOverview(name="test", primary_language="py", frameworks=[], runtime_targets=[], build_system=""),
            structure_map=StructureMap(entry_points=[], core_modules=[]),
            hard_constraints=HardConstraints(language_version="", framework_versions={}, external_interfaces=[], cannot_change=[]),
            soft_constraints=SoftConstraints(coding_patterns=[], style_conventions=[], existing_abstractions=[], tech_debt_notes=[]),
            known_unknowns=KnownUnknowns(missing_context=[], ambiguous_areas=[]),
            planner_guardrails=PlannerGuardrails(do_not_assume=[], requires_validation=[]),
            evidence_index=EvidenceIndex(files_examined=[], configs_examined=[], commands_run=[])
        )

        # Mock Refinement
        refined_plan = DispatchStep(
            agent="coder",
            task="Build a glider instead",
            context_files=[]
        )
        mock_planner.refine_plan.return_value = refined_plan

        with patch.object(spine, "dispatch_to_agent", new_callable=AsyncMock) as mock_dispatch:
            mock_dispatch.side_effect = [
                mock_researcher_output, # Turn 1 Researcher
                JudgeResult(score=0.4, reasoning="too complex", decision="REJECT"), # Turn 1 Judge
                mock_researcher_output, # Turn 2 Researcher
                JudgeResult(score=0.9, reasoning="better", decision="APPROVE") # Turn 2 Judge
            ]

            # Execute
            final_plan = await spine._negotiate_plan("Build a spaceship")

            # Verify
            assert final_plan.task == "Build a glider instead"
            # researcher + judge + researcher + judge = 4 calls
            assert mock_dispatch.call_count == 4
            mock_planner.refine_plan.assert_called_once()
