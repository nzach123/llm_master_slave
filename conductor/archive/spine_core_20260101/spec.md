# Track Specification: Core Spine Controller & Communication Loop

## 1. Overview
This track focuses on building the foundational "Spine" of the application. The goal is to establish the core data structures (`specs.py`), the main application controller (`hub.py`), and the basic Git integration (`git_tools.py`) to enable a safe, validated communication loop between the Gemini Hub and the local system. This is the prerequisite for adding actual Ollama "Spokes" later.

## 2. Functional Requirements
### 2.1 Data Contracts (`specs.py`)
- **Strict Typing:** Must use `pydantic.BaseModel` for all schemas.
- **DispatchStep:** Define the schema for a task sent to an agent. Must include `agent_name`, `task_description`, and `context` dictionary.
- **AgentResult:** Define the schema for an agent's response. Must include `status` (ok/error), `message`, and `artifacts` list.
- **Validation:** All data passing through the Spine must be validated against these schemas.

### 2.2 Git Safety Net (`tools/git_tools.py`)
- **Checkpointing:** A function `create_checkpoint(task_id: str)` that:
    1. Checks for a clean working directory (no uncommitted changes).
    2. Creates and switches to a new branch named `task/{task_id}`.
- **Reverting:** A function `revert_to_main()` that discards the current branch and returns to `main`.
- **Integration:** Uses `GitPython` library.

### 2.3 The Spine Controller (`core/hub.py`)
- **Initialization:** Must load environment variables (API keys) via `python-dotenv`.
- **Main Loop:** A basic loop that:
    1. Initializes the Git checkpoint.
    2. (Mock) Simulates receiving a plan from Gemini (hardcoded for this track).
    3. (Mock) Simulates dispatching a step to a "Mock Agent".
    4. Validates the result using `specs.py`.
    5. Logs the activity to `activity.log`.

## 3. Non-Functional Requirements
- **Logging:** All actions must be logged with timestamps to `activity.log`.
- **Error Handling:** Use `tenacity` to retry the "Mock Dispatch" step at least once on failure.
- **Python Version:** Code must be compatible with Python 3.11+.

## 4. Acceptance Criteria
- [ ] `specs.py` exists and contains `DispatchStep` and `AgentResult` Pydantic models.
- [ ] `tools/git_tools.py` can successfully create a new branch and switch back to main.
- [ ] `core/hub.py` runs without error, creates a log file, and successfully "processes" a mock task.
- [ ] Unit tests exist for `specs.py` validation and `git_tools.py` logic.

## 5. Out of Scope
- Actual Gemini API integration (Mocking for now).
- Actual Ollama integration (Mocking for now).
- Complex Patcher logic (Next track).
