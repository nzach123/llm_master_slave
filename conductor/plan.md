# Implementation Plan: V2 Refactor

**Goal:** Transform the system into a robust, async, structured-output agentic workflow.

## Phase 1: The Reliability Layer (Week 1)
*Focus: Stop the system from failing on syntax and whitespace errors.*

- [ ] **Task 1.1: Implement Fuzzy Patcher**
    - [ ] Create `tools/fuzzy_match.py` using `difflib.SequenceMatcher`.
    - [ ] Update `tools/patcher.py` to fallback to fuzzy match if exact match fails.
    - [ ] Add logging for "Confidence Score" when patching.
    - [ ] Unit Test: Verify patching works with varying indentation/whitespace.

- [ ] **Task 1.2: Enforce JSON Schemas**
    - [ ] Update `core/specs.py`: Define Pydantic models for `SpokeResponse`.
    - [ ] Update `core/spokes.py`: Add `format="json"` to Ollama API payload.
    - [ ] Refactor `core/roles.py`: Update System Prompts to demand JSON, remove XML instructions.
    - [ ] Remove `core/parsing.py` (TagParser) and replace with `pydantic.model_validate_json`.

## Phase 2: The Async Core (Week 2)
*Focus: Modernize the runtime for responsiveness and MCP compatibility.*

- [ ] **Task 2.1: Asyncio Migration**
    - [ ] Replace `requests`/`httpx` (sync) with `aiohttp` or `httpx.AsyncClient` in `core/spokes.py`.
    - [ ] Update `core/hub.py`: Convert `Spine` methods to `async def`.
    - [ ] Update `main.py`: Use `asyncio.run(main())`.

- [ ] **Task 2.2: Resource Mutex**
    - [ ] Implement `asyncio.Lock()` in `Spine` to prevent concurrent local inference.
    - [ ] Update `tools/resource_monitor.py` to be an async polling loop.

- [ ] **Task 2.3: MCP Server Update**
    - [ ] Update `mcp_server/ollama_bridge.py` to await the new async Spine methods.

## Phase 3: Intelligence & Interactivity (Week 3)
*Focus: Better reasoning and user control.*

- [x] **Task 3.1: The Judge Agent**
    - [x] Create `core/judge.py`.
    - [x] Implement simple prompt loop using `phi3.5`.
    - [x] Integrate Judge into the `_negotiate_plan` method in `Spine`.

- [x] **Task 3.2: Interactive Gating**
    - [x] Add `await input("Press Enter to execute Plan...")` in `run_autonomous_loop`.
    - [ ] (Optional) Allow user to edit the JSON plan before confirmation.

- [x] **Task 3.3: Rich Logging**
    - [x] Install `rich` library.
    - [x] Create `tools/logger.py` to render the Plan as a Tree and status as Spinners.

## Success Criteria
1.  **Zero Parse Errors:** System never fails due to malformed LLM output.
2.  **Patch Resilience:** Patches succeed >95% of the time without retry loops.
3.  **Responsiveness:** CLI responds to Ctrl+C immediately.
