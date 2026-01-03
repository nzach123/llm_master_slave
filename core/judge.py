from typing import Dict, Any
from core.spokes import BaseSpoke
from core.specs import DispatchStep, FeasibilityCheck
from core.roles import JUDGE_SYSTEM_PROMPT
from pydantic import BaseModel

class JudgeResult(BaseModel):
    score: float
    reasoning: str
    decision: str # "APPROVE" or "REJECT"

class JudgeSpoke(BaseSpoke):
    def get_system_prompt(self) -> str:
        return JUDGE_SYSTEM_PROMPT

    @property
    def response_model(self):
        return JudgeResult

    async def evaluate_plan(self, plan: Dict[str, Any], feedback: FeasibilityCheck) -> JudgeResult:
        """
        Evaluates the plan and feedback to provide a consensus score.
        """
        task = (
            f"Evaluate the following plan against the researcher's feedback.\n\n"
            f"Plan Task: {plan.get('task')}\n"

            f"Researcher Feedback:\n"
            f"Hard Constraints: {feedback.summary.hard_constraints}\n"
            f"Soft Constraints: {feedback.summary.soft_constraints}\n"
            f"Missing Info/Unknowns: {feedback.summary.known_unknowns}\n"
            f"Message: {feedback.message}\n"
        )

        step = DispatchStep(
            agent="judge",
            task=task,
            context_files=[]
        )

        return await self.handle_task(step)
