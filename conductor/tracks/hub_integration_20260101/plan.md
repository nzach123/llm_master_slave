# Implementation Plan - Track: Hub Integration

## Phase 1: The Planner Client
- [x] Task: Create `core/planner.py` skeleton and test file `tests/test_planner.py`. [d3635ac]
- [x] Task: Implement `GeminiClient` initialization (loading API key). [06f3ac6]
    - *Test:* Verify client fails gracefully without API key.
- [x] Task: Implement `generate_plan(user_intent: str) -> DispatchStep`. [1a489f8]
    - *Test:* Mock the network call to verify JSON parsing and Pydantic validation logic handles happy/sad paths.
    - *Constraint:* Must use `pydantic` for schema enforcement.
- [ ] Task: Conductor - User Manual Verification 'The Planner Client' (Protocol in workflow.md)

## Phase 2: System Prompts & Context
- [ ] Task: Create `core/prompts.py` to store System Instructions.
    - *Requirement:* Must include "Product Guidelines" (Technical Minimalism).
- [ ] Task: Integrate `core/specs.py` schema definitions into the System Prompt dynamically.
- [ ] Task: Conductor - User Manual Verification 'System Prompts & Context' (Protocol in workflow.md)

## Phase 3: Hub Wiring
- [ ] Task: Update `core/hub.py` to use `Planner` instead of mock data.
- [ ] Task: Integration Test - Run `main.py` with a real API key (or recorded mock) to verify the full loop.
- [ ] Task: Conductor - User Manual Verification 'Hub Wiring' (Protocol in workflow.md)
