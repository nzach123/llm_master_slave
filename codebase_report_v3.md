```markdown
## Codebase Analysis Report: LLM Master-Slave Project

### 1. System Overview

The system employs a Hub-and-Spoke architecture for LLM-driven autonomous code modification. A central "Hub" (using Gemini 2.0 Flash) decomposes user intents into structured plans. These plans are dispatched to local "Spokes" (Ollama instances acting as Coder and Reviewer agents) for execution. The Hub implements a retry loop with context injection for error handling. File modifications are handled via a custom "Patcher" for idempotency. The system includes resource monitoring and Git-based checkpointing for safety and recovery. The system supports both interactive (user-driven task delegation) and autonomous modes.

### 2. Key Components

*   **`core/hub.py` (Spine Controller):** The central control logic. It orchestrates the autonomous loop, manages task dispatch to Spokes, parses tool call outputs from Spokes, executes file modifications using the `patcher` module, and handles retries. It also integrates resource monitoring and Git checkpointing.
*   **`core/planner.py` (Hub Planner):** Implements the Gemini 2.0 Flash client using the `google-generativeai` SDK. It's responsible for generating `DispatchStep` plans from user intents, including error context injection during retries. It enforces a strict JSON schema for plan outputs.
*   **`core/spokes.py` (Spokes - Workers):** Defines the `BaseSpoke` abstraction and concrete `CoderSpoke` and `ReviewerSpoke` implementations. These classes encapsulate the interaction with local Ollama instances, constructing prompts and handling responses. They provide distinct system prompts for Coder and Reviewer roles.
*   **`tools/patcher.py`:** Provides safe file I/O logic, specifically `write_file` and `apply_patch` functions. It aims for idempotent file modifications using search/replace operations, enhancing token efficiency.
*   **`tools/resource_monitor.py`:** Implements RAM and VRAM monitoring with a hard-fail policy to prevent system instability.

### 3. Current Status

Based on the documentation and code, the following components are implemented:

*   **Hub (Planner):** Gemini integration using `google-generativeai`.
*   **Spine (Controller):** Autonomous loop with task generation and dispatch.
*   **Spokes (Workers):** Ollama integration with Coder and Reviewer agents.
*   **Resource Monitoring:** Implemented with a hard-fail policy.
*   **Patcher logic:** Implemented and integrated within the Spine Controller.
*   **Testing:** A suite of tests exists, covering configuration, Hub functionality, spokes, and tool integrations.

The system is in a state where it can autonomously generate plans, dispatch them to Ollama-based agents, execute code modifications, and perform basic resource monitoring.

### 4. Implementation Next Steps

Prioritized list of concrete implementation tasks:

1.  **Robust Error Handling and Reporting:** Enhance error reporting in the autonomous loop. Include more detailed information about failures (e.g., specific test failures, patch application errors) in the `AgentResult`. Consider adding a dedicated error reporting artifact.
2.  **Improve Test Coverage:** Increase test coverage, especially for the `patcher` module and edge cases in XML parsing within `core/hub.py`. Focus on testing failure scenarios (e.g., invalid XML, file not found).
3.  **Implement Git Reversion on Critical Errors:** Fully implement the Git reversion mechanism described in `product.md`. If the autonomous loop fails after multiple retries, automatically revert the working directory to the last known good state.
4.  **Refine Tool Call Parsing:** Improve the robustness of XML parsing in `core/hub.py` to handle variations in LLM output. Consider adding more specific error handling for different types of parsing errors.
5.  **Implement Comprehensive Logging:** Ensure all key actions and decisions within the autonomous loop are logged with sufficient detail for debugging and auditing. This includes planner inputs, agent outputs, tool execution results, and test results.
6.  **Implement interactive mode**: Allow users to delegate tasks directly via CLI/API.

### 5. Technical Recommendations

*   **Centralized Configuration Management:** Consolidate all configurable parameters into the `config.py` module and ensure consistent access throughout the system. Consider using a more robust configuration management library for complex configurations.
*   **Asynchronous Spoke Execution (Future):** While currently synchronous to manage VRAM, explore asynchronous task execution with appropriate resource management (e.g., model loading queues) to improve performance. This would require significant refactoring and careful VRAM monitoring.
*   **Standardize Logging:** Enforce a consistent logging format and level across all modules. Utilize structured logging for easier analysis.
*   **Improve Git Integration:** Enhance Git integration for better tracking of changes and easier rollback capabilities.
*   **Implement Task Queue Persistence:** Use `tinydb` as described in the `tech-stack.md` document to persist tasks across restarts.
