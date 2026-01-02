# LLM Master-Slave Autonomous Agent System

## Project Overview
This is a Hub-and-Spoke autonomous agent system. Gemini (you) act as the Hub for planning, while local Ollama models execute specialized tasks.

## Available MCP Tools

### Spoke Dispatch (Bidirectional Prompting)
- `dispatch_to_coder(task, context)` - Send coding tasks to Ollama Coder
- `dispatch_to_researcher(query, context)` - Get project analysis
- `dispatch_to_reviewer(code, context)` - Code review and feedback

### Autonomous Execution
- `run_autonomous_loop(intent)` - Full Plan→Execute→Verify cycle with Git safety

### Task Queue (Persistent)
- `add_task(intent)` - Add task to queue for later execution
- `get_pending_tasks()` - List queued tasks
- `process_next_task()` - Execute next task in queue

### Context Gathering
- `get_project_context(max_depth)` - Get project file tree

## Autonomous Workflow

When given a high-level goal:

1. **Analyze** - Use `get_project_context()` and `dispatch_to_researcher()` to understand state
2. **Plan** - Decompose goal into steps
3. **Execute** - Use `run_autonomous_loop(intent)` for complex changes OR `dispatch_to_coder()` for quick edits
4. **Verify** - Review results, run tests
5. **Queue Next** - If more work needed, use `add_task()` to queue follow-up tasks

## Self-Tasking Protocol

For multi-step implementations:
1. Complete current task
2. Evaluate remaining work
3. Call `add_task()` for each subsequent step
4. Call `process_next_task()` to continue OR let user trigger later

## Project Structure
```
├── core/           # Hub logic (Spine, Planner, Spokes)
├── tools/          # File patcher, executor, queue
├── mcp_server/     # This MCP bridge
├── tests/          # pytest test suite
└── conductor/      # Documentation
```

## Safety Features
- Git checkpoints before autonomous changes
- Rollback on max retries
- Path whitelisting (cannot write outside project)
- Resource monitoring (VRAM/RAM)
