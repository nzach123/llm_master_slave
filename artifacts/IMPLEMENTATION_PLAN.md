# Implementation Plan: Critical Findings Fix

## Overview

This plan addresses the critical and high-priority issues identified in the orchestration verification test harness.

---

## ISSUE-001: No Conflict Resolution Policy (CRITICAL)

### Current State
- When multiple workers produce conflicting outputs, no detection or resolution exists
- `ConsensusScorer` was deprecated
- `JudgeSpoke` evaluates plan quality but not item-level conflicts

### Proposed Solution

#### 1. Create `ConflictResolver` Class in `core/conflict_resolver.py`

```python
from typing import Dict, Any, List, Set, Tuple
from dataclasses import dataclass
from enum import Enum
import logging

class ConflictResolutionStrategy(str, Enum):
    MAJORITY_VOTE = "majority_vote"
    FIRST_RESPONDER = "first_responder"
    ESCALATE = "escalate"

@dataclass
class ConflictReport:
    item: str
    category: str
    votes: Dict[str, int]  # classification -> vote count
    resolution: str
    confidence: float
    requires_human_review: bool

class ConflictResolver:
    """
    Detects and resolves conflicts in multi-worker outputs.
    """
    
    def __init__(self, strategy: ConflictResolutionStrategy = ConflictResolutionStrategy.MAJORITY_VOTE):
        self.strategy = strategy
        self.logger = logging.getLogger(__name__)
    
    def detect_conflicts(
        self, 
        worker_outputs: List[Dict[str, Any]], 
        classification_keys: List[str]
    ) -> List[ConflictReport]:
        """
        Detect items that appear in conflicting categories across workers.
        """
        # Build item -> category mappings per worker
        item_classifications: Dict[str, Dict[str, int]] = {}
        
        for output in worker_outputs:
            for key in classification_keys:
                items = output.get(key, [])
                for item in items:
                    if item not in item_classifications:
                        item_classifications[item] = {}
                    item_classifications[item][key] = item_classifications[item].get(key, 0) + 1
        
        # Find conflicts (items in multiple categories)
        conflicts = []
        for item, votes in item_classifications.items():
            if len(votes) > 1:
                total_votes = sum(votes.values())
                max_category = max(votes, key=votes.get)
                max_votes = votes[max_category]
                confidence = max_votes / total_votes
                
                conflicts.append(ConflictReport(
                    item=item,
                    category=max_category,
                    votes=votes,
                    resolution=max_category if confidence > 0.5 else "escalate",
                    confidence=confidence,
                    requires_human_review=confidence <= 0.5
                ))
        
        return conflicts
    
    def resolve(
        self, 
        worker_outputs: List[Dict[str, Any]], 
        classification_keys: List[str]
    ) -> Tuple[Dict[str, List[str]], List[ConflictReport]]:
        """
        Resolve conflicts and produce merged output.
        
        Returns:
            Tuple of (merged_output, conflict_reports)
        """
        conflicts = self.detect_conflicts(worker_outputs, classification_keys)
        
        # Log conflicts
        for conflict in conflicts:
            if conflict.requires_human_review:
                self.logger.warning(f"Conflict requires human review: {conflict.item} - votes: {conflict.votes}")
            else:
                self.logger.info(f"Conflict auto-resolved: {conflict.item} -> {conflict.resolution} (confidence: {conflict.confidence:.2f})")
        
        # Build merged output using majority vote for non-conflicted items
        merged = {key: set() for key in classification_keys}
        
        for output in worker_outputs:
            for key in classification_keys:
                for item in output.get(key, []):
                    merged[key].add(item)
        
        # Apply conflict resolutions (remove from losing categories)
        for conflict in conflicts:
            if not conflict.requires_human_review:
                for key in classification_keys:
                    if key != conflict.resolution and conflict.item in merged[key]:
                        merged[key].remove(conflict.item)
        
        return {k: list(v) for k, v in merged.items()}, conflicts
```

#### 2. Integrate into `Spine` class in `core/hub.py`

Add import and initialization:
```python
from core.conflict_resolver import ConflictResolver, ConflictResolutionStrategy

class Spine:
    def __init__(self):
        # ... existing code ...
        self.conflict_resolver = ConflictResolver(ConflictResolutionStrategy.MAJORITY_VOTE)
```

Add method for multi-worker dispatch:
```python
async def dispatch_to_multiple_workers(
    self, 
    step: DispatchStep, 
    worker_count: int = 2
) -> Tuple[SpokeResponse, List[ConflictReport]]:
    """Dispatch same task to multiple workers and resolve conflicts."""
    responses = []
    
    for i in range(worker_count):
        response = await self.dispatch_to_agent(step)
        responses.append(response)
    
    # Convert SpokeResponse to dict for conflict resolution
    # (Only applicable for classification tasks)
    
    return merged_response, conflicts
```

---

## ISSUE-002: Schema Validation Not Explicitly Surfaced (HIGH)

### Current State
- Pydantic validation exists but errors may not surface clearly
- Errors logged but lost in retry loops

### Proposed Solution

#### 1. Create `ValidationGate` in `core/validation.py`

```python
from typing import Dict, Any, Type, Optional
from pydantic import BaseModel, ValidationError
from dataclasses import dataclass
import logging

@dataclass
class ValidationResult:
    valid: bool
    data: Optional[BaseModel]
    errors: list
    raw_input: Dict[str, Any]

class ValidationGate:
    """
    Explicit validation gate that surfaces all errors clearly.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def validate(
        self, 
        data: Dict[str, Any], 
        schema: Type[BaseModel],
        context: str = ""
    ) -> ValidationResult:
        """
        Validate data against schema with explicit error surfacing.
        
        Args:
            data: Raw data to validate
            schema: Pydantic model class
            context: Context string for error messages
            
        Returns:
            ValidationResult with all errors captured
        """
        try:
            validated = schema.model_validate(data)
            return ValidationResult(
                valid=True,
                data=validated,
                errors=[],
                raw_input=data
            )
        except ValidationError as e:
            errors = [
                {
                    "loc": err["loc"],
                    "msg": err["msg"],
                    "type": err["type"]
                }
                for err in e.errors()
            ]
            
            self.logger.error(f"Validation failed [{context}]: {errors}")
            
            return ValidationResult(
                valid=False,
                data=None,
                errors=errors,
                raw_input=data
            )
    
    def require_valid(
        self, 
        data: Dict[str, Any], 
        schema: Type[BaseModel],
        context: str = ""
    ) -> BaseModel:
        """
        Validate and raise explicit exception if invalid.
        """
        result = self.validate(data, schema, context)
        
        if not result.valid:
            raise SchemaValidationError(
                f"Schema validation failed for {context}",
                errors=result.errors,
                raw_input=result.raw_input
            )
        
        return result.data

class SchemaValidationError(Exception):
    """Explicit exception for schema validation failures."""
    
    def __init__(self, message: str, errors: list, raw_input: Dict[str, Any]):
        super().__init__(message)
        self.errors = errors
        self.raw_input = raw_input
```

#### 2. Integrate into `BaseSpoke` in `core/spokes.py`

```python
from core.validation import ValidationGate, SchemaValidationError

class BaseSpoke(ABC):
    def __init__(self, base_url: str, model: str):
        # ... existing code ...
        self.validator = ValidationGate()
    
    async def handle_task(self, step: DispatchStep) -> T:
        # ... existing HTTP call ...
        
        content = data["message"]["content"]
        
        # Parse JSON
        try:
            raw_data = json.loads(content)
        except json.JSONDecodeError as e:
            raise SchemaValidationError(
                f"Failed to parse JSON from {self.__class__.__name__}",
                errors=[{"msg": str(e), "type": "json_parse_error"}],
                raw_input={"raw_content": content}
            )
        
        # Explicit validation with surfacing
        return self.validator.require_valid(
            raw_data, 
            self.response_model,
            context=f"{self.__class__.__name__}.handle_task"
        )
```

---

## ISSUE-003: No Justification Traceability (MEDIUM)

### Proposed Solution

#### 1. Extend `SpokeResponse` in `core/specs.py`

```python
class ClassificationJustification(BaseModel):
    item: str
    classification: str
    reason: str
    confidence: Optional[float] = None

class SpokeResponse(BaseModel):
    thoughts: str
    tool_calls: List[ToolCall]
    justifications: Optional[List[ClassificationJustification]] = None
```

#### 2. Update System Prompts in `core/roles.py`

Add instruction to provide justifications:
```python
CODER_SYSTEM_PROMPT = """
...existing prompt...

For any classification task, provide justifications in this format:
{
    "justifications": [
        {"item": "function_name", "classification": "pure|impure", "reason": "one-line explanation"}
    ]
}
"""
```

---

## Implementation Order

1. **Phase 1: Validation Gate** (ISSUE-002)
   - Create `core/validation.py`
   - Update `core/spokes.py` to use ValidationGate
   - Add tests in `tests/test_validation.py`

2. **Phase 2: Conflict Resolver** (ISSUE-001)
   - Create `core/conflict_resolver.py`
   - Add multi-worker dispatch capability
   - Add tests in `tests/test_conflict_resolver.py`

3. **Phase 3: Justification Traceability** (ISSUE-003)
   - Update `core/specs.py`
   - Update `core/roles.py`
   - Add validation for justification presence

---

## Testing Strategy

Each phase includes:
1. Unit tests for the new component
2. Integration test with mocked workers
3. Harness verification test

---

## Rollback Plan

Each change is isolated to new files or additive changes:
- `core/validation.py` - new file
- `core/conflict_resolver.py` - new file
- Existing code changes are minimal and backward-compatible
