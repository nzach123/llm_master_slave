# Technology Stack

## Core Language & Runtime
- **Python:** 3.11+ (Chosen for superior error tracebacks to aid autonomous debugging)
- **Package Manager:** `uv` (for fast dependency resolution and environment management)

## Hub (Planner)
- **Model:** Gemini 2.0 Flash
- **Interface:** `google-generativeai` (Official Python SDK)
- **Validation:** `pydantic` (for enforcing strict JSON schemas in model outputs)
- **Security:** `python-dotenv` (for safe API key management)

## Spine (Controller)
- **Framework:** Modular Python Package structure
- **Retry Logic:** `tenacity` (for robust task retries and error handling)
- **Networking:** `httpx` (Synchronous Mode - chosen to enforce strict sequential execution for VRAM management)
- **Version Control:** `GitPython` (for programmatic branch management and checkpointing)
- **Persistence:** `tinydb` (Lightweight JSON database for persisting the task queue and agent state across restarts)

## Spokes (Workers)
- **Local Runtime:** Ollama
- **Models:**
    - `qwen2.5-coder:7b-q4_k_m` (Primary Coder)
    - `mistral` (Primary Reviewer)
- **Constraint Management:** 
    - Strict sequential task routing.
    - `psutil` (for system resource monitoring and VRAM guarding before model loads)

## Infrastructure & Tools
- **Patcher:** Custom Search/Replace logic for idempotent file modifications.
- **Testing:** `pytest` (for unit testing and mocking agent responses).
- **Logging:** Standard Python `logging` with file persistence to `activity.log`.