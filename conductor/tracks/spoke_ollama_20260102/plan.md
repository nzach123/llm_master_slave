# Implementation Plan - Track: Spoke Integration (Ollama)

## Phase 1: Infrastructure & Environment [checkpoint: pending]
- [x] Task: Update Configuration. (2181e90)
    - [x] Sub-task: Add `OLLAMA_BASE_URL`, `CODER_MODEL`, and `REVIEWER_MODEL` to `core/config.py`.
    - [x] Sub-task: Update `tests/test_config.py` to verify new settings.
- [ ] Task: Implement Resource Monitoring (`tools/resource_monitor.py`).
    - [ ] Sub-task: Use `psutil` to implement `get_available_ram()` and `get_available_vram()`.
    - [ ] Sub-task: Create `tests/test_resource_monitor.py` to verify threshold logic (mocking `psutil`).
- [ ] Task: Conductor - User Manual Verification 'Infrastructure' (Protocol in workflow.md)

## Phase 2: Spoke Core & Worker Implementation [checkpoint: pending]
- [ ] Task: Create `core/spokes.py`.
    - [ ] Sub-task: Define `BaseSpoke` and specialized `CoderSpoke`/`ReviewerSpoke`.
    - [ ] Sub-task: Implement synchronous Ollama request logic using `httpx`.
- [ ] Task: Create `tests/test_spokes.py`.
    - [ ] Sub-task: Mock `httpx.Client.post` to verify prompt injection and error handling.
- [ ] Task: Conductor - User Manual Verification 'Spoke Implementation' (Protocol in workflow.md)

## Phase 3: Hub & Spine Integration [checkpoint: pending]
- [ ] Task: Update `core/hub.py` (Spine class).
    - [ ] Sub-task: Initialize Spokes and implement routing in `dispatch_to_agent`.
    - [ ] Sub-task: Implement pre-flight resource checks with Hard Fail policy.
- [ ] Task: Create `tests/test_hub_ollama.py`.
    - [ ] Sub-task: Verify that `dispatch_to_agent` correctly routes to Spokes and handles resource failures.
- [ ] Task: Conductor - User Manual Verification 'Integration' (Protocol in workflow.md)

## Phase 4: Final Verification [checkpoint: pending]
- [ ] Task: Run full test suite (`pytest`).
- [ ] Task: Conductor - User Manual Verification 'Final Verification' (Protocol in workflow.md)
