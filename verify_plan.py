"""
Plan Verification Script

Dispatches the implementation plan to 3 specialized agents for review:
1. Researcher Agent - Validates feasibility and identifies constraints
2. Coder Agent - Reviews code quality and implementation approach
3. Reviewer Agent - Final approval/rejection decision

Usage:
    python verify_plan.py
"""

import asyncio
import json
import os
import sys
from pathlib import Path
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from core.spokes import ResearcherSpoke, CoderSpoke, ReviewerSpoke
from core.specs import DispatchStep
from core.config import load_config

# Read the implementation plan
PLAN_PATH = Path(__file__).parent / "artifacts" / "IMPLEMENTATION_PLAN.md"


def load_plan() -> str:
    """Load the implementation plan from file."""
    with open(PLAN_PATH, "r", encoding="utf-8") as f:
        return f.read()


async def verify_with_researcher(base_url: str, model: str, plan: str) -> dict:
    """
    Agent 1: Researcher
    
    Role: Analyze feasibility, identify constraints, flag unknowns
    """
    print("\n" + "="*70)
    print("AGENT 1: RESEARCHER")
    print("="*70)
    
    researcher = ResearcherSpoke(base_url, model)
    
    step = DispatchStep(
        agent="researcher",
        task=f"""
Analyze the following implementation plan for feasibility.

FOCUS ON:
1. Hard constraints - What could prevent implementation?
2. Dependencies - What must exist first?
3. Missing information - What's unclear or unstated?
4. Risk assessment - What could go wrong?

RESPOND WITH YOUR STANDARD OUTPUT FORMAT.

IMPLEMENTATION PLAN:
{plan}
""",
        context_files=["core/hub.py", "core/spokes.py", "core/specs.py"]
    )
    
    try:
        result = await researcher.handle_task(step)
        print(f"\n✓ Researcher Response Received")
        return {
            "agent": "researcher",
            "status": "success",
            "output": result.model_dump()
        }
    except Exception as e:
        print(f"\n✗ Researcher Failed: {e}")
        return {
            "agent": "researcher",
            "status": "error",
            "error": str(e)
        }


async def verify_with_coder(base_url: str, model: str, plan: str) -> dict:
    """
    Agent 2: Coder
    
    Role: Review code quality, implementation approach, potential bugs
    """
    print("\n" + "="*70)
    print("AGENT 2: CODER")
    print("="*70)
    
    coder = CoderSpoke(base_url, model)
    
    step = DispatchStep(
        agent="coder",
        task=f"""
Review the following implementation plan from a code quality perspective.

EVALUATE:
1. Code design - Is the proposed architecture sound?
2. Edge cases - What edge cases are unhandled?
3. Performance - Any performance concerns?
4. Testability - Will this be easy to test?
5. Integration - How well does it integrate with existing code?

DO NOT write actual code. Just analyze and provide your thoughts.
Return an empty tool_calls list.

IMPLEMENTATION PLAN:
{plan}
""",
        context_files=["core/hub.py", "core/spokes.py", "core/specs.py"]
    )
    
    try:
        result = await coder.handle_task(step)
        print(f"\n✓ Coder Response Received")
        print(f"  Thoughts: {result.thoughts[:200]}...")
        return {
            "agent": "coder",
            "status": "success",
            "thoughts": result.thoughts,
            "tool_calls": [tc.model_dump() for tc in result.tool_calls]
        }
    except Exception as e:
        print(f"\n✗ Coder Failed: {e}")
        return {
            "agent": "coder",
            "status": "error",
            "error": str(e)
        }


async def verify_with_reviewer(base_url: str, model: str, plan: str, 
                                researcher_feedback: dict, 
                                coder_feedback: dict) -> dict:
    """
    Agent 3: Reviewer
    
    Role: Final approval decision based on all feedback
    """
    print("\n" + "="*70)
    print("AGENT 3: REVIEWER (Final Decision)")
    print("="*70)
    
    reviewer = ReviewerSpoke(base_url, model)
    
    # Compile feedback
    feedback_summary = f"""
RESEARCHER FEEDBACK:
{json.dumps(researcher_feedback, indent=2, default=str)[:2000]}

CODER FEEDBACK:
{json.dumps(coder_feedback, indent=2, default=str)[:2000]}
"""
    
    step = DispatchStep(
        agent="reviewer",
        task=f"""
You are the final reviewer for this implementation plan.

Based on the Researcher and Coder feedback below, make a final decision:
- approved: true/false
- comments: List of specific comments/concerns

DECISION CRITERIA:
1. Are all critical issues addressed?
2. Is the implementation approach sound?
3. Are there any blocking concerns?

{feedback_summary}

ORIGINAL PLAN SUMMARY:
- Phase 1: ValidationGate for explicit schema validation
- Phase 2: ConflictResolver for multi-worker conflict handling
- Phase 3: Justification traceability in responses
""",
        context_files=[]
    )
    
    try:
        result = await reviewer.handle_task(step)
        print(f"\n✓ Reviewer Response Received")
        print(f"  Approved: {result.approved}")
        print(f"  Comments: {result.comments}")
        return {
            "agent": "reviewer",
            "status": "success",
            "approved": result.approved,
            "comments": result.comments
        }
    except Exception as e:
        print(f"\n✗ Reviewer Failed: {e}")
        return {
            "agent": "reviewer",
            "status": "error",
            "error": str(e)
        }


async def run_verification():
    """Run the complete 3-agent verification pipeline."""
    print("="*70)
    print("IMPLEMENTATION PLAN VERIFICATION")
    print("3-Agent Review Pipeline")
    print("="*70)
    print(f"Started: {datetime.now().isoformat()}")
    
    # Load config
    config = load_config()
    base_url = config.get("OLLAMA_BASE_URL", "http://localhost:11434")
    coder_model = config.get("CODER_MODEL", "qwen2.5-coder:7b")
    reviewer_model = config.get("REVIEWER_MODEL", "phi3.5:latest")
    
    print(f"\nConfiguration:")
    print(f"  Ollama URL: {base_url}")
    print(f"  Coder Model: {coder_model}")
    print(f"  Reviewer Model: {reviewer_model}")
    
    # Load plan
    plan = load_plan()
    print(f"\nPlan loaded: {len(plan)} characters")
    
    # Run 3 agents sequentially
    results = {}
    
    # Agent 1: Researcher
    results["researcher"] = await verify_with_researcher(base_url, coder_model, plan)
    
    # Agent 2: Coder
    results["coder"] = await verify_with_coder(base_url, coder_model, plan)
    
    # Agent 3: Reviewer (with feedback from previous agents)
    results["reviewer"] = await verify_with_reviewer(
        base_url, 
        reviewer_model, 
        plan,
        results["researcher"],
        results["coder"]
    )
    
    # Generate summary
    print("\n" + "="*70)
    print("VERIFICATION SUMMARY")
    print("="*70)
    
    all_success = all(r.get("status") == "success" for r in results.values())
    approved = results.get("reviewer", {}).get("approved", False)
    
    print(f"\nAll Agents Responded: {all_success}")
    print(f"Final Approval: {approved}")
    
    if approved:
        print("\n✓ PLAN APPROVED - Proceed with implementation")
    else:
        print("\n✗ PLAN NEEDS REVISION")
        if "comments" in results.get("reviewer", {}):
            print("  Reviewer Comments:")
            for comment in results["reviewer"]["comments"]:
                print(f"    - {comment}")
    
    # Save results
    output_path = Path(__file__).parent / "artifacts" / "plan_verification_result.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "results": results,
            "summary": {
                "all_agents_responded": all_success,
                "approved": approved
            }
        }, f, indent=2, default=str)
    
    print(f"\nResults saved to: {output_path}")
    
    return results


def main():
    """Main entry point."""
    # Check if Ollama is likely running
    import socket
    try:
        sock = socket.create_connection(("localhost", 11434), timeout=2)
        sock.close()
    except (socket.timeout, ConnectionRefusedError):
        print("⚠️  Warning: Ollama doesn't appear to be running on localhost:11434")
        print("   Start Ollama or this verification will fail.")
        print()
    
    # Run async verification
    try:
        results = asyncio.run(run_verification())
        return 0 if results.get("reviewer", {}).get("approved", False) else 1
    except Exception as e:
        print(f"\n✗ Verification failed with error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
