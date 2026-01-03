# LLM Master-Slave Test Harness Documentation

## Overview

This test harness provides comprehensive verification of the Conductor/Worker orchestration system. It was built following the principle of **verification over demonstration** - the goal is to find bugs and weaknesses, not to show that things work.

## Architecture

```
tests/harness/
├── __init__.py              # Package marker
├── message_capture.py       # Message logging infrastructure
├── schema_validator.py      # Schema validation & aggregation verification
├── fault_injection.py       # Fault injection module
├── test_report.py           # Report generation
└── run_harness.py           # Main runner (standalone execution)

tests/
└── test_orchestration_verification.py  # pytest test suite
```

## Components

### 1. Message Capture (`message_capture.py`)

Captures all messages flowing through the orchestration:
- **Tester → Conductor** - User intents and test prompts
- **Conductor → Worker** - Task dispatches
- **Worker → Conductor** - Responses

Features:
- Timestamps for each message
- Automatic schema validation
- Latency tracking
- Summary generation

```python
from tests.harness.message_capture import MessageCapture, MessageDirection

capture = MessageCapture()
capture.start_capture()

msg = capture.record(
    direction=MessageDirection.CONDUCTOR_TO_WORKER,
    source="Spine",
    destination="CoderSpoke",
    payload={"task": "Create file", ...},
    schema_model=DispatchStep  # Optional Pydantic model
)

summary = capture.get_summary()
```

### 2. Schema Validator (`schema_validator.py`)

Validates message schemas and aggregation correctness:

```python
from tests.harness.schema_validator import assert_schema, AggregationValidator

# Simple schema check
result = assert_schema(response, ["pure", "impure"])

# Verify no data fabrication
result = AggregationValidator.validate_no_fabrication(
    worker_outputs=[...],
    aggregated_output={...},
    key_paths=["pure", "impure"]
)

# Verify majority vote
result = AggregationValidator.validate_majority_vote(
    worker_outputs=[...],
    aggregated_output={...},
    item="append_item",
    category_key="impure"
)
```

### 3. Fault Injection (`fault_injection.py`)

Injects various failure modes:

| Fault Type | Description |
|------------|-------------|
| `MISSING_FIELD` | Remove a required field |
| `MALFORMED_JSON` | Corrupt the JSON structure |
| `CONFLICTING_OUTPUT` | Replace a field with conflicting value |
| `EMPTY_RESPONSE` | Return empty object |
| `TIMEOUT` | Simulate timeout |
| `PARTIAL_RESPONSE` | Return incomplete response |
| `WRONG_TYPE` | Replace value with wrong type |
| `NULL_VALUE` | Replace value with null |

```python
from tests.harness.fault_injection import FaultInjector, FaultConfig, FaultType

injector = FaultInjector()
injector.add_fault(FaultConfig(
    fault_type=FaultType.MISSING_FIELD,
    target_field="impure"
))

corrupted = injector.inject(valid_response)
```

### 4. Test Report (`test_report.py`)

Generates professional test reports:

```python
from tests.harness.test_report import TestReport, TestCase, IssueSeverity

report = TestReport(title="Verification Report", description="...")

test_case = TestCase(
    name="Function Purity",
    test_prompt={...},
    expected_behavior=[...]
)

test_case.add_assertion("Add is pure", expected=True, actual=True, passed=True)
test_case.add_issue(
    severity=IssueSeverity.CRITICAL,
    category="Conflict Resolution",
    description="No conflict resolution policy exists"
)

report.add_test_case(test_case)
print(report.to_markdown())
```

## Running the Tests

### Via pytest (recommended)
```powershell
.\run_tests.ps1 tests/test_orchestration_verification.py -v
```

### Standalone Harness
```powershell
python -m tests.harness.run_harness
```

This generates timestamped reports in `artifacts/`:
- `test_report_YYYYMMDD_HHMMSS.txt` - Plain text
- `test_report_YYYYMMDD_HHMMSS.md` - Markdown

## Canonical "Canary" Test

The harness includes a canonical test task intentionally chosen for its verifiability:

```python
test_prompt = {
    "task": "Classify Python functions by purity and side effects",
    "input": [
        "def add(a, b): return a + b",
        "def append_item(lst, item): lst.append(item)",
        "def now(): return datetime.now()"
    ],
    "output_format": {
        "pure": [],
        "impure": []
    }
}
```

**Why this works:**
- Requires decomposition (analysis + classification)
- Easy to verify independently
- Side effects are a known failure point for LLM reasoning
- JSON output is machine-checkable

**Expected Results:**
| Function | Classification | Reason |
|----------|---------------|--------|
| `add` | pure | No side effects, deterministic |
| `append_item` | impure | Mutates input list |
| `now` | impure | Non-deterministic (depends on time) |

## Issues Found

### Critical

1. **No Conflict Resolution Policy**
   - When workers disagree, there is no deterministic resolution
   - The ConsensusScorer was deprecated but Judge doesn't handle item-level conflicts
   - **Recommendation:** Implement majority vote with escalation path

### High

2. **Schema Validation Not Enforced**
   - Worker responses use Pydantic validation but failures may not surface properly
   - **Recommendation:** Add explicit pre-aggregation validation

### Medium

3. **No Justification Traceability**
   - Classifications lack justification strings
   - **Recommendation:** Require justification for each decision

## Unverifiable Assumptions

The following cannot be verified without additional context:

1. LLM reasoning correctness for edge cases (closures, global state)
2. Determinism of Ollama responses even with `temperature=0.1`
3. Correct handling of rare edge cases without production traffic
4. Worker model consistency across restarts/updates

## Integration with CI/CD

The harness can be integrated into CI/CD pipelines:

```yaml
# Example GitHub Actions
- name: Run Test Harness
  run: |
    python -m tests.harness.run_harness
    exit_code=$?
    if [ $exit_code -ne 0 ]; then
      echo "Test harness detected issues"
      exit 1
    fi
```

Exit codes:
- `0` - All tests passed, no critical issues
- `1` - Issues detected (check report)

## Extending the Harness

### Adding New Fault Types

```python
# In fault_injection.py
class FaultType(str, Enum):
    # ... existing types ...
    CUSTOM_FAULT = "CUSTOM_FAULT"

# Then in FaultInjector._apply_fault():
elif fault.fault_type == FaultType.CUSTOM_FAULT:
    # Your custom logic
    pass
```

### Adding New Test Scenarios

```python
# In test_orchestration_verification.py or run_harness.py
def run_my_new_test() -> TestCase:
    test_case = TestCase(
        name="My New Test",
        description="Tests some new scenario",
        test_prompt={...},
        expected_behavior=[...]
    )
    
    # Add your assertions
    test_case.add_assertion(...)
    
    test_case.calculate_result()
    return test_case
```

## Design Principles

1. **Assume Nothing** - Every claim is verified, not trusted
2. **Fail Fast** - Silent recovery is a failure mode
3. **Explicit Over Implicit** - All decisions are traceable
4. **Prefer Assertions Over Narrative** - Machine-checkable results
5. **Surface Uncertainty** - If something can't be verified, say so
