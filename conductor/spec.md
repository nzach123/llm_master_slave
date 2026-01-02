# System Specification: LLM Master-Slave (Async & Structured)

## 1. Project Overview
**System Name:** LLM Master-Slave (Conductor) v2
**Purpose:** An asynchronous, hub-and-spoke autonomous agent system where a cloud-based Planner (Gemini) orchestrates local, constrained Workers (Ollama) to build software.
**Core Philosophy:** "Plan in the Cloud, Execute Locally."
**Target Hardware:** Consumer GPU (RTX 3070, 8GB VRAM).

## 2. System Architecture

The v2 architecture shifts from a blocking synchronous loop to an **Asynchronous Event-Driven Controller**.

### High-Level Pattern
`Async Event Loop (Python/Asyncio)` -> `Task Queue` -> `Worker Dispatch`

### Major Subsystems

1.  **Hub (The Brain - Cloud):**
    * **Model:** Gemini 2.0 Flash.
    * **Role:** High-level planning, error analysis, and verification step generation.
    * **Interface:** Async Google GenAI SDK.

2.  **Spine (The Controller - Async):**
    * **Tech:** Python 3.11+ (`asyncio`, `aiohttp`).
    * **Responsibility:** Non-blocking orchestration. It manages the lifecycle of a task without freezing the UI/CLI.
    * **Key Change:** Uses `await` for all IO-bound operations (Ollama inference, file reads).

3.  **Spokes (The Workers - Local):**
    * **Models:** `qwen2.5-coder` (Coder), `phi3.5` (Reviewer/Judge).
    * **Interface:** Ollama API via `aiohttp`.
    * **Protocol:** **Structured JSON Outputs**. No more XML parsing. Agents must return valid JSON objects adhering to a schema.

4.  **Reliability Layer:**
    * **Fuzzy Patcher:** A file modification tool using `difflib` to apply patches even when whitespace doesn't match exactly (90% confidence threshold).
    * **Git Safety Net:** Automatic branching per task.

## 3. Data & Control Flow

### The Autonomous Loop (v2)
1.  **User Intent:** User submits request via CLI or MCP.
2.  **Planning (Gemini):** Hub generates a JSON `DispatchStep`.
3.  **Human Gate (Optional):** System pauses (`await input`) for user approval of the plan.
4.  **Dispatch (Ollama):** Spine sends task to Coder Spoke.
    * *Constraint:* Enforces sequential execution (Mutex lock on VRAM).
5.  **Execution (Tooling):**
    * Spoke returns JSON `ToolCall`.
    * Spine executes `FuzzyPatcher`.
6.  **Verification:**
    * System runs `pytest` (async subprocess).
    * If Pass: Commit.
    * If Fail: Send error context back to Gemini for re-planning.

## 4. Component Definitions

| Component | Path | Responsibility | Key Change in v2 |
| :--- | :--- | :--- | :--- |
| **Spine** | `core/hub.py` | Main Event Loop | `async def run_autonomous_loop` |
| **Spoke** | `core/spokes.py` | Model Adapter | `format='json'` in API call |
| **Patcher** | `tools/patcher.py` | File I/O | Implement `difflib` fuzzy matching |
| **Judge** | `core/judge.py` | Consensus | New Agent: "Pass/Fail" logic |
| **Monitor** | `tools/resources.py`| VRAM Guard | Async polling for resources |

## 5. Data Models (JSON Schema)

**DispatchStep (Hub Output):**
```json
{
  "agent": "coder",
  "task": "Implement login function",
  "context_files": ["src/auth.py"]
}
```

**ToolCall (Spoke Output):**
```json
{
  "action": "apply_patch",
  "path": "src/auth.py",
  "search": "def login():\n    pass",
  "replace": "def login():\n    return True"
}
```

## 6. Known Constraints

*   **VRAM Mutex:** Even though the app is async, inference MUST be serial. The Spine will use an `asyncio.Lock()` around the `dispatch_to_agent` call.
*   **Context Window:** Local models have limited context. The Researcher should still be used to prune context before passing it to the Coder.
