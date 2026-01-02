# Implementation Plan - Track: Spoke Integration (Ollama)

## Phase 1: Infrastructure & Environment [checkpoint: 949262d]
- [x] Task: Update Configuration. (2181e90)
    - [x] Sub-task: Add `OLLAMA_BASE_URL`, `CODER_MODEL`, and `REVIEWER_MODEL` to `core/config.py`.
    - [x] Sub-task: Update `tests/test_config.py` to verify new settings.
- [x] Task: Implement Resource Monitoring (`tools/resource_monitor.py`). (ae7d77f)
    - [x] Sub-task: Use `psutil` to implement `get_available_ram()` and `get_available_vram()`.
    - [x] Sub-task: Create `tests/test_resource_monitor.py` to verify threshold logic (mocking `psutil`).
- [x] Task: Conductor - User Manual Verification 'Infrastructure' (Protocol in workflow.md)

## Phase 2: Spoke Core & Worker Implementation [checkpoint: 4e1a9c7]
- [x] Task: Create `core/spokes.py`. (48cfa8e)
    - [x] Sub-task: Define `BaseSpoke` and specialized `CoderSpoke`/`ReviewerSpoke`.
    - [x] Sub-task: Implement synchronous Ollama request logic using `httpx`.
- [x] Task: Create `tests/test_spokes.py`. (48cfa8e)
    - [x] Sub-task: Mock `httpx.Client.post` to verify prompt injection and error handling.
- [x] Task: Conductor - User Manual Verification 'Spoke Implementation' (Protocol in workflow.md)

## Phase 3: Hub & Spine Integration [checkpoint: c8273a0]
- [x] Task: Update `core/hub.py` (Spine class). (2a7d801)
    - [x] Sub-task: Initialize Spokes and implement routing in `dispatch_to_agent`.
    - [x] Sub-task: Implement pre-flight resource checks with Hard Fail policy.
- [x] Task: Create `tests/test_hub_ollama.py`. (2a7d801)
    - [x] Sub-task: Verify that `dispatch_to_agent` correctly routes to Spokes and handles resource failures.
- [x] Task: Conductor - User Manual Verification 'Integration' (Protocol in workflow.md)

## Phase 4: Final Verification [checkpoint: pending]
- [ ] Task: Run full test suite (`pytest`).
- [ ] Task: Conductor - User Manual Verification 'Final Verification' (Protocol in workflow.md)
