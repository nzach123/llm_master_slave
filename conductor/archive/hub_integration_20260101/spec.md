# Track Specification: Hub (Gemini) Integration

## 1. Overview
This track focuses on integrating the `google-generativeai` SDK into the `Spine`. The goal is to replace the `run_mock_loop` with a real `run_autonomous_loop` that fetches plans from Gemini 2.0 Flash, validates them against our Pydantic schemas, and executes them.

## 2. Functional Requirements
### 2.1 The Planner (`core/planner.py`)
- **Client:** Wrapper around `google.generativeai`.
- **Configuration:** Must use `GEMINI_API_KEY` from `core/config.py`.
- **Prompt Engineering:**
    - System prompt must enforce the "Technical Minimalism" and "Strict JSON" guidelines.
    - Must inject strict JSON schemas (from `core/specs.py`) into the model context.
- **Output Validation:**
    - Raw string response -> JSON parse -> Pydantic Validation (`DispatchStep`).
    - **Retry Logic:** If validation fails, the error must be fed back to the model for correction (max retries).

### 2.2 Hub Integration (`core/hub.py`)
- **Upgrade:** Replace `run_mock_loop` with `run_autonomous_loop`.
- **Flow:**
    1. Checkpoint (Git).
    2. **NEW:** Fetch Plan from `Planner`.
    3. Dispatch to Agent (Mock for now, or actual execution).
    4. Report results.

## 3. Acceptance Criteria
- [ ] `core/planner.py` exists and passes unit tests.
- [ ] System can successfully send a prompt to Gemini 2.0 Flash and receive a valid JSON response.
- [ ] `DispatchStep` Pydantic models are used to validate real API responses.
- [ ] `activity.log` records the raw prompt and response tokens for debugging.
