# Implementation Plan - Track: Spine Core

## Phase 1: Foundation & Contracts
- [x] Task: Create project structure (folders `core`, `tools`, `tests`). [517e308]
- [ ] Task: Create `specs.py` with Pydantic models.
    - [ ] Sub-task: Define `DispatchStep` model.
    - [ ] Sub-task: Define `AgentResult` model.
    - [ ] Sub-task: Write unit tests for schema validation (`tests/test_specs.py`).
- [ ] Task: Implement Git Safety Net (`tools/git_tools.py`).
    - [ ] Sub-task: Implement `create_checkpoint` using `GitPython`.
    - [ ] Sub-task: Implement `revert_to_main`.
    - [ ] Sub-task: Write unit tests for git operations (mocking the actual git binary).

## Phase 2: The Spine Controller
- [ ] Task: Implement Logging & Config.
    - [ ] Sub-task: Setup `python-dotenv` to load `.env`.
    - [ ] Sub-task: Configure standard logging to `activity.log`.
- [ ] Task: Create `core/hub.py` (The Spine).
    - [ ] Sub-task: Implement the `Spine` class initialization.
    - [ ] Sub-task: Implement a `run_mock_loop` method.
    - [ ] Sub-task: Integrate `tenacity` for a simple retry loop on a mock function.
- [ ] Task: Integration Test.
    - [ ] Sub-task: Create a `main.py` entrypoint that uses `Spine`.
    - [ ] Sub-task: Run the loop and verify `activity.log` contains expected entries.
    - [ ] Sub-task: Verify a git branch was created during the run.

## Phase 3: Final Verification
- [ ] Task: Run full test suite (`pytest`).
- [ ] Task: Conductor - User Manual Verification 'Final Verification' (Protocol in workflow.md)
