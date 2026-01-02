# Product Guidelines

## 1. Aesthetic & User Experience
- **Technical Minimalism:** The system output should be raw, technical, and prioritized for high parsing speed and debugging.
- **Output Format:** Pure JSON and standard log outputs are preferred over heavy styling or ASCII art. This ensures that logs are easy to `grep` and analyze.

## 2. Technical Standards
- **Strict Typing:** All Python code MUST use PEP 484 type annotations. This includes all functions, classes, and variable declarations to ensure the integrity of the "Spine" controller.
- **Documentation (Google Style):** Every module, class, and method MUST include a Google-style docstring. Detailed sections for `Args`, `Returns`, and `Raises` are mandatory to provide sufficient context for autonomous agents.
- **Git Conventions:** The system MUST use the **Conventional Commits** specification for all autonomous git operations (e.g., `feat:`, `fix:`, `chore:`). This maintains a clear and auditable project history.

## 3. Workflow & Version Control
- **Episodic Branching:** Every significant autonomous task MUST be executed in its own isolated branch (e.g., `task/description-timestamp`).
- **Sandbox Management:** These branches serve as experimental "Pathways." Upon successful completion and review, they can be merged; if a task fails or goes out of bounds, the branch is discarded to keep the `main` branch clean.

## 4. Monitoring & Logging
- **Centralized Activity Logs:** The system MUST append detailed timestamps and status updates to a central `activity.log` file.
- **Persistence:** All progress, decisions made by the Hub, and errors encountered by the Spokes must be recorded in this file for historical auditing and real-time monitoring via `tail -f`.
