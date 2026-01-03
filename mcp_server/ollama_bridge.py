"""
MCP Server Bridge for Gemini CLI ↔ Ollama Integration.

This module exposes the llm_master_slave Spine controller as MCP tools,
enabling Gemini CLI to autonomously execute tasks via local Ollama models.

Run with: python -m mcp_server.ollama_bridge
"""

import os
import sys

# Ensure project root is in path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastmcp import FastMCP
from typing import Optional, List, Dict, Any

# Initialize MCP server
mcp = FastMCP(
    name="ollama-bridge",
    instructions="""
    This MCP server bridges Gemini CLI to local Ollama models via the Spine controller.
    
    Available capabilities:
    - dispatch_to_coder: Send coding tasks to local Ollama Coder agent
    - dispatch_to_researcher: Query the Researcher agent for context
    - run_autonomous_loop: Execute full Plan→Execute→Verify loop
    - add_task: Add a task to the persistent queue
    - get_pending_tasks: List pending tasks in queue
    - process_next_task: Execute the next pending task
    """
)

# Lazy initialization of Spine (heavy import)
_spine = None
_queue = None


def get_spine():
    """Lazy-load Spine to avoid import overhead on MCP discovery."""
    global _spine
    if _spine is None:
        from core.hub import Spine
        _spine = Spine()
    return _spine


def get_queue():
    """Lazy-load TaskQueue."""
    global _queue
    if _queue is None:
        from tools.queue import TaskQueue
        _queue = TaskQueue()
    return _queue


# =============================================================================
# Phase 1 & 2: Spoke Dispatch Tools
# =============================================================================

@mcp.tool()
async def dispatch_to_coder(task: str, context: Optional[Dict[str, Any]] = None) -> str:
    """
    Dispatch a coding task to the local Ollama Coder agent.
    
    Args:
        task: Description of the coding task to perform
        context: Optional dictionary of context (e.g., file contents, requirements)
    
    Returns:
        The Coder agent's response (may contain XML tool calls)
    """
    from core.specs import DispatchStep
    spine = get_spine()
    step = DispatchStep(
        agent_name="coder",
        task_description=task,
        context=context or {}
    )
    result = await spine.dispatch_to_agent(step)
    return result.message


@mcp.tool()
async def dispatch_to_researcher(query: str, context: Optional[Dict[str, Any]] = None) -> str:
    """
    Query the Researcher agent for project analysis or context gathering.
    
    Args:
        query: The research question or analysis request
        context: Optional additional context
    
    Returns:
        The Researcher agent's analysis (typically JSON or structured text)
    """
    from core.specs import DispatchStep
    spine = get_spine()
    step = DispatchStep(
        agent_name="researcher",
        task_description=query,
        context=context or {}
    )
    result = await spine.dispatch_to_agent(step)
    return result.message


@mcp.tool()
async def dispatch_to_reviewer(code: str, context: Optional[Dict[str, Any]] = None) -> str:
    """
    Send code to the Reviewer agent for quality analysis.
    
    Args:
        code: The code to review
        context: Optional context (e.g., requirements, style guide)
    
    Returns:
        The Reviewer's feedback
    """
    from core.specs import DispatchStep
    spine = get_spine()
    step = DispatchStep(
        agent_name="reviewer",
        task_description=f"Review the following code:\n\n{code}",
        context=context or {}
    )
    result = await spine.dispatch_to_agent(step)
    return result.message


# =============================================================================
# Phase 3: Autonomous Loop
# =============================================================================

@mcp.tool()
async def run_autonomous_loop(intent: str, max_retries: int = 3) -> str:
    """
    Execute the full autonomous loop: Plan → Execute → Verify.
    
    This will:
    1. Create a Git checkpoint
    2. Generate a plan using Gemini
    3. Dispatch to local agents
    4. Execute tool calls (file writes, patches)
    5. Run tests to verify
    6. Retry on failure, rollback on max retries
    
    Args:
        intent: High-level goal description
        max_retries: Maximum retry attempts (default: 3)
    
    Returns:
        Final result message with verification steps
    """
    spine = get_spine()
    result = await spine.run_autonomous_loop(intent, max_retries=max_retries)
    return f"Status: {result.status}\n\n{result.message}"


# =============================================================================
# Phase 4: Task Queue Integration (Mandatory)
# =============================================================================

@mcp.tool()
def add_task(intent: str, priority: int = 0) -> str:
    """
    Add a task to the persistent queue for later execution.
    
    Args:
        intent: The task description/goal
        priority: Task priority (higher = more urgent, default: 0)
    
    Returns:
        The assigned task ID
    """
    queue = get_queue()
    task_id = queue.add_task(intent)
    return f"Task added: {task_id}"


@mcp.tool()
def get_pending_tasks() -> List[Dict[str, Any]]:
    """
    List all pending tasks in the queue.
    
    Returns:
        List of task objects with id, intent, status, created_at
    """
    queue = get_queue()
    tasks = queue.get_pending_tasks()
    return [{"id": t["task_id"], "intent": t["intent"], "status": t["status"]} for t in tasks]


@mcp.tool()
async def process_next_task() -> str:
    """
    Execute the next pending task from the queue.
    
    Returns:
        Result of task execution
    """
    queue = get_queue()
    spine = get_spine()
    
    pending = queue.get_pending_tasks()
    if not pending:
        return "No pending tasks in queue."
    
    task = pending[0]
    queue.update_task_status(task["task_id"], "running")
    
    try:
        result = await spine.run_autonomous_loop(task["intent"], existing_task_id=task["task_id"])
        queue.update_task_status(task["task_id"], "completed", result.message)
        return f"Task {task['task_id']} completed: {result.message[:500]}"
    except Exception as e:
        queue.update_task_status(task["task_id"], "failed", str(e))
        return f"Task {task['task_id']} failed: {e}"


@mcp.tool()
def get_project_context(max_depth: int = 2) -> str:
    """
    Get the current project structure for context.
    
    Args:
        max_depth: Maximum directory depth to scan
    
    Returns:
        Formatted project tree structure
    """
    from tools.context import get_project_context as _get_context
    return _get_context(max_depth=max_depth)


# =============================================================================
# Entry Point
# =============================================================================

if __name__ == "__main__":
    mcp.run()
