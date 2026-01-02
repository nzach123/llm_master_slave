# Initial Concept

**Project:** Hub-and-Spoke Agent System project for LLM ingestion

**User Profile:**
- Role: Senior Python Developer.
- Hardware: RTX 3070 (8GB VRAM).
- Constraint: Local inference limited to single active quantization (q4_k_m) model; concurrent local models impossible.
- OS: Windows/Linux (implied via uv usage).

**System Architecture:**
- **Pattern:** Hub-and-Spoke / Controller-Worker (Synchronous, Blocking).
- **Hub (Planner):** Gemini 2.0 Flash (Cloud API) via `google-generativeai` SDK.
    - Responsibility: Intent parsing, task decomposition, JSON generation.
    - Output: Strict JSON Plan schema.
    - **Interface:** Python SDK. Chosen for reliability, structured output support, and low latency compared to CLI wrapping.
- **Spine (Controller):** Python 3.10+ Application.
    - Responsibility: Routing, Validation, Retry Logic (tenacity), Tool Execution.
- **Spokes (Workers):** Local Ollama instances.
    - Coder: qwen2.5-coder:7b-q4_k_m.
    - Reviewer: mistral (or similar).
    - Responsibility: Atomic task execution, distinct persona checks.

**Key Decisions:**
- **Communication Protocol:** No direct Agent-to-Agent comms. All routing via Hub Controller.
- **File Operations:** No full file rewrites. Use Patcher class (Search/Replace blocks) for idempotency and token efficiency.
- **Error Handling:** Hub implements retry loop with Context Injection (passing error msg back to agent in next prompt).
- **Dependency Management:** uv for package management.
- **Typing:** Strict enforcement via dataclasses and TypedDict in specs.py.

**Technical Implementation:**
- **File Structure:**
    - `specs.py`: IDL/Contracts (DispatchStep, AgentResult, Artifact).
    - `core/planner.py`: Gemini SDK wrapper, forces JSON schema.
    - `core/hub.py`: Main loop, error injection, retries.
    - `workers/`: Wrapper classes for Ollama models (e.g., CoderAgent).
    - `tools/patcher.py`: Safe I/O logic.
- **Data Schemas:**
    - `DispatchStep`: `{ agent: str, task: str, context: Dict }`
    - `AgentResult`: `{ status: Literal["ok", "error"], message: str, artifacts: List[Artifact] }`

**Active Constraints:**
- **VRAM:** Aggressive model unloading required. No parallel local inference.
- **Latency:** Model swapping (Coder <-> Reviewer) incurs delay; architecture must tolerate blocking I/O.
- **Context:** Workers are stateless/amnesiac. Context must be passed explicitly in DispatchStep.
- **Safety:** Agents cannot execute arbitrary shell commands; must use defined Tools.

- **Implementation Status:**
- **Phase 1, 2 & 3 Complete:** Core architecture and Hub Integration are complete.
    - **Hub (Planner):** `core/planner.py` uses `google-generativeai` (Gemini 2.0 Flash) to parse user intent into strict JSON plans (`DispatchStep`).
    - **Spine (Controller):** `core/hub.py` now runs an autonomous loop that generates a plan, checkpoints via git, and dispatches tasks.
- **Phase 4 Complete:** Spoke Integration (Ollama) is complete.
    - **Spokes (Workers):** `core/spokes.py` implements the `Spoke` abstraction for Ollama.
    - **Resource Guarding:** `tools/resource_monitor.py` implements RAM and VRAM monitoring with a "Hard Fail" policy to ensure system stability.
- **Next:** Implement the "Patcher" logic for safe file I/O.

# Product Definition

## 1. Interaction Model
- **Hybrid Autonomous-Interactive Hub:**
    - **Interactive Mode:** The user (Spine Controller) delegates tasks directly via CLI/API. The Hub (Gemini) generates plans, and local agents (Spokes) execute them.
    - **Autonomous Mode:** The system runs in a background loop. Local agents can "prompt" the Hub for guidance or next steps when the user is away, effectively allowing the system to work through a queue or goal autonomously.
    - **Mechanism:** A polling or event-driven loop where the Hub checks for agent status or backlog items when no user input is detected.

## 2. Autonomy Strategy
- **Aggressive Autonomy with Git Safety Net & Branching:**
    - The system prioritizes forward momentum and self-correction.
    - **Version Control Integration:**
        - **Checkpointing:** Before starting a significant autonomous task chain, the system creates a new git branch or checkpoint.
        - **Branching/Logging:** The system logs different "Pathways" or "Drafts" in distinct git branches. This allows the system to explore solutions without polluting the main branch.
        - **Fail-Safe:** If a critical error or unresolvable loop occurs, the system automatically reverts the working directory to the last known good state or the pre-task checkpoint.
        - **Review Loop:** Successful or "Candidate" autonomous runs are kept in their respective branches for the user to review, merge, or discard upon return.

## 3. Core Features
- **Centralized Hub (Gemini 2.0 Flash SDK):** Acts as the brain, converting high-level intent into strict JSON plans. Accessed via `google-generativeai` SDK for reliability.
- **Local Workers (Ollama):** Specialized agents (Coder, Reviewer) running locally on restricted hardware (RTX 3070).
- **Resource Management:** Strict sequential execution to respect VRAM limits. No concurrent local models.
- **Idempotent Patching:** All file modifications use a search/replace Patcher to ensure safety and minimal token usage.
- **TDD-Driven Autonomy:**
    - **Self-Correcting Unit Tests:** The system generates unit tests for new features *before* implementation.
    - **Validation:** Autonomous agents run these tests to verify their own code. Test failures trigger the "Retry Logic" in the Hub, providing immediate feedback loops without user intervention.
