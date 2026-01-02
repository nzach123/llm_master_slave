# Agent Personas & Protocols

This document defines the specialized agents (Spokes) utilized by the Conductor system.

## 1. The Planner (Hub)
* **Model:** Gemini 2.0 Flash
* **Role:** Architect & Project Manager.
* **Responsibility:**
    * Understand vague user intents.
    * Break down tasks into atomic steps.
    * Analyze error logs and propose fixes.
* **Output:** `DispatchStep` (JSON).

## 2. The Coder (Spoke)
* **Model:** `qwen2.5-coder:7b`
* **Role:** Senior Python Developer.
* **System Prompt Strategy:**
    * Strict adherence to "Clean Code" principles.
    * **Constraint:** output MUST be a JSON object containing a list of `ToolCall`s.
    * **Prohibited:** Markdown text outside the JSON block.
* **Input:** Task description + File Context.
* **Output:**
    ```json
    {
      "thoughts": "Explanation of what I am changing...",
      "tool_calls": [
        { "action": "write_file", "path": "...", "content": "..." }
      ]
    }
    ```

## 3. The Reviewer (Spoke)
* **Model:** `phi3.5:latest` (or `mistral`)
* **Role:** QA Engineer.
* **Responsibility:**
    * Analyze code diffs.
    * Check for security vulnerabilities (injection, path traversal).
    * Verify logic against the Plan.
* **Output:** `ReviewResult` (JSON: `approved` boolean, `comments` list).

## 4. The Researcher (Spoke)
* **Model:** `qwen2.5-coder` or `phi3.5`
* **Role:** Technical Analyst.
* **Responsibility:**
    * Scan the codebase (via provided file tree or grep results).
    * Identify dependencies and potential breaking changes.
    * Output a "Knowledge Summary" to aid the Planner.

## 5. The Judge (New Spoke)
* **Model:** `phi3.5` (Low latency)
* **Role:** Tie-breaker / Consensus Mechanism.
* **Responsibility:**
    * Compare the `Planner`'s proposed plan against the `Researcher`'s constraint list.
    * Decide **Go / No-Go**.
* **Prompt:** "You are a safety officer. Given the plan and the system constraints, is this safe to execute? Respond with JSON: { 'safe': bool, 'reason': str }"
