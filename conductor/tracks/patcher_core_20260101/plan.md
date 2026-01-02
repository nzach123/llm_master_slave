# Plan: Patcher Core (Safe I/O)

## Phase 1: Core I/O [checkpoint: c237a29]
- [x] Task: Create `tests/test_patcher.py` (Failing/Empty) 7bd1e9d
- [x] Task: Implement `tools/patcher.py` structure and `read_file`, `write_file` 7bd1e9d
- [x] Task: Verify Core I/O with tests 7bd1e9d
- [x] Task: Conductor - User Manual Verification 'Core I/O' (Protocol in workflow.md) c237a29

## Phase 2: Patch Logic
- [x] Task: Add tests for `apply_patch` (Idempotency, Not Found, Success) d1da9f5
- [x] Task: Implement `apply_patch` logic d1da9f5
- [x] Task: Verify Patch Logic with tests d1da9f5
- [ ] Task: Conductor - User Manual Verification 'Patch Logic' (Protocol in workflow.md)

## Phase 3: Finalization
- [ ] Task: Run full test suite and check coverage
- [ ] Task: Lint and Code Style Check
- [ ] Task: Conductor - User Manual Verification 'Finalization' (Protocol in workflow.md)
