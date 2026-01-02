# Specification: Patcher Core (Safe I/O)

## Overview
Implement a robust, safe file manipulation tool (`tools/patcher.py`) for the Conductor framework. This tool will handle file reading, atomic writing, and idempotent patching.

## Functional Requirements
1.  **read_file(path)**:
    -   Read file content as UTF-8 strict.
    -   Handle FileNotFoundError (logging).
2.  **write_file(path, content)**:
    -   Write content to file atomically (write to tmp, then move).
    -   Create parent directories if they don't exist.
3.  **apply_patch(path, search_block, replace_block)**:
    -   Read file.
    -   **Idempotency Check**: If `replace_block` exists and `search_block` does not, return True (already applied).
    -   **Safety Check**: If `search_block` is not found, return False (do not modify).
    -   **Apply**: Replace the *first occurrence* of `search_block` with `replace_block`.
    -   **Write**: Use atomic `write_file`.

## Non-Functional Requirements
-   **Zero External Dependencies**: Use standard library (`os`, `pathlib`, `logging`).
-   **TDD**: >80% coverage.
-   **Style**: Google Docstrings, Type Hints.

## Acceptance Criteria
-   All unit tests pass (Success, Idempotency, Not Found).
-   No partial writes on failure.
