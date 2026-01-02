# Track Specification: Spoke Integration (Ollama)

## 1. Overview
Replace the `mock_agent` logic in the Spine with real interactions with a local Ollama instance. This track introduces the `Spoke` abstraction, handling model selection, prompt wrapping, and synchronous HTTP communication, supported by strict resource monitoring.

## 2. Functional Requirements
### 2.1 Ollama Client (`core/spokes.py`)
- **Protocol:** HTTP POST to `/v1/chat/completions` (OpenAI-compatible endpoint).
- **Library:** `httpx` (Synchronous) to ensure blocking sequential execution.
- **Error Handling:** Must catch `httpx.ConnectError` (Ollama not running) and raise a clean error for the Hub to log.

### 2.2 Worker Identities
- **Coder Spoke:**
    - Model: `qwen2.5-coder:7b` (default).
    - Behavior: Receives a coding task, outputs code blocks.
- **Reviewer Spoke:**
    - Model: `phi3.5:latest` (default).
    - Behavior: Analyzes code, outputs strict "Approve/Reject" with reasoning.

### 2.3 Resource Guarding (`tools/resource_monitor.py`)
- **Pre-flight Check:** Integrated into `Spine.dispatch_to_agent`.
- **Metrics:** Monitor both Available System RAM and Available VRAM using `psutil`.
- **Threshold:** 2GB minimum available for both RAM and VRAM (where applicable).
- **Failure Policy:** **Hard Fail.** Log a critical error and terminate the loop immediately.

## 3. Integration Logic
- **Routing:** `Spine` routes `DispatchStep.agent_name` to the corresponding `Spoke` instance.
- **Context Injection:** Spokes prepend `DispatchStep.context` (file contents, error logs) to the user prompt.
- **Configuration:** Update `core/config.py` to include `OLLAMA_BASE_URL`, `CODER_MODEL`, and `REVIEWER_MODEL`.

## 4. Acceptance Criteria
- [ ] `core/spokes.py` implements the `Spoke` base class and specialized workers.
- [ ] `Spine` successfully blocks and waits for Ollama response.
- [ ] System performs a "Hard Fail" if RAM/VRAM is < 2GB before inference.
- [ ] Unit tests mock `httpx` to verify payload structure.
