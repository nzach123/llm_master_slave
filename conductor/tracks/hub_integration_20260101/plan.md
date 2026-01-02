# Implementation Plan - Track: Hub Integration

## Phase 1: The Planner Client [checkpoint: 2def04c]
- [x] Task: Create `core/planner.py` skeleton and test file `tests/test_planner.py`. [d3635ac]
- [x] Task: Implement `GeminiClient` initialization (loading API key). [06f3ac6]
    - *Test:* Verify client fails gracefully without API key.
- [x] Task: Implement `generate_plan(user_intent: str) -> DispatchStep`. [1a489f8]
    - *Test:* Mock the network call to verify JSON parsing and Pydantic validation logic handles happy/sad paths.
    - *Constraint:* Must use `pydantic` for schema enforcement.
- [x] Task: Conductor - User Manual Verification 'The Planner Client' (Protocol in workflow.md) [2def04c]

## Phase 2: System Prompts & Context [checkpoint: 19fcb6a]
- [x] Task: Create `core/prompts.py` to store System Instructions. [b5e49f9]
    - *Requirement:* Must include "Product Guidelines" (Technical Minimalism).
- [x] Task: Integrate `core/specs.py` schema definitions into the System Prompt dynamically. [bb09564]
- [x] Task: Conductor - User Manual Verification 'System Prompts & Context' (Protocol in workflow.md) [19fcb6a]

## Phase 3: Hub Wiring [checkpoint: 5486172]
- [x] Task: Update `core/hub.py` to use `Planner` instead of mock data. [448c118]
- [x] Task: Integration Test - Run `main.py` with a real API key (or recorded mock) to verify the full loop. [e657603]
- [x] Task: Conductor - User Manual Verification 'Hub Wiring' (Protocol in workflow.md) [5486172]
