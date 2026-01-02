from typing import Dict, Any
from core.specs import KnowledgeSummary, FeasibilityCheck

class ConsensusScorer:
    def __init__(self):
        pass

    def evaluate(self, plan_v1: Dict[str, Any], feedback: FeasibilityCheck) -> float:
        """
        Calculates a consensus score (0.0 - 1.0) based on the plan and spoke feedback.

        This is a heuristic implementation. In a real scenario, this might use an LLM
        or more complex logic.

        Args:
            plan_v1: The original plan (dictionary).
            feedback: The feedback from the Researcher/Critic (FeasibilityCheck).

        Returns:
            float: The consensus score.
        """
        score = 0.6 # Base score (increased to allow reaching > 0.8 with good feasibility)

        # 1. Feasibility Boost
        if feedback.summary.feasibility_score:
            score += (feedback.summary.feasibility_score * 0.3)

        # 2. Constraint Penalty
        # If there are critical constraints that match the plan's weaknesses (mock logic here)
        # For now, we just penalize if there are many constraints identified
        constraint_count = len(feedback.summary.technical_constraints)
        if constraint_count > 0:
             score -= (constraint_count * 0.05)

        # 3. Missing Info Penalty
        missing_count = len(feedback.summary.missing_information)
        if missing_count > 0:
            score -= (missing_count * 0.05)

        # Clamp score to 0.0 - 1.0
        return max(0.0, min(1.0, score))
