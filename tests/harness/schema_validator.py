"""
Schema Validation Module for Test Harness.

This module provides strict schema validation for all message types
in the orchestration system. It validates:
- Required fields are present
- Types are correct
- Deterministic aggregation rules are followed
"""

from typing import Dict, Any, List, Optional, Set, Type
from pydantic import BaseModel, ValidationError
from dataclasses import dataclass


@dataclass 
class SchemaValidationResult:
    """Result of a schema validation check."""
    valid: bool
    missing_keys: List[str]
    extra_keys: List[str]
    type_errors: List[str]
    raw_errors: Optional[List[Dict[str, Any]]] = None

    @property
    def all_errors(self) -> List[str]:
        """Get all error messages."""
        errors = []
        if self.missing_keys:
            errors.append(f"Missing required keys: {self.missing_keys}")
        if self.extra_keys:
            errors.append(f"Unexpected keys: {self.extra_keys}")
        if self.type_errors:
            errors.extend(self.type_errors)
        return errors


def assert_schema(message: Dict[str, Any], required_keys: List[str]) -> SchemaValidationResult:
    """
    Assert that a message contains all required keys.
    
    Args:
        message: The message dictionary to validate
        required_keys: List of keys that must be present
        
    Returns:
        SchemaValidationResult with validation details
    """
    missing = [k for k in required_keys if k not in message]
    return SchemaValidationResult(
        valid=len(missing) == 0,
        missing_keys=missing,
        extra_keys=[],
        type_errors=[]
    )


def validate_against_model(
    data: Dict[str, Any], 
    model: Type[BaseModel],
    strict: bool = True
) -> SchemaValidationResult:
    """
    Validate a dictionary against a Pydantic model.
    
    Args:
        data: The data to validate
        model: The Pydantic model class
        strict: If True, fail on extra fields
        
    Returns:
        SchemaValidationResult with validation details
    """
    try:
        model.model_validate(data, strict=strict)
        return SchemaValidationResult(
            valid=True,
            missing_keys=[],
            extra_keys=[],
            type_errors=[]
        )
    except ValidationError as e:
        missing = []
        type_errors = []
        raw_errors = e.errors()
        
        for err in raw_errors:
            if err['type'] == 'missing':
                missing.extend(err['loc'])
            else:
                type_errors.append(f"{'.'.join(str(l) for l in err['loc'])}: {err['msg']}")
        
        return SchemaValidationResult(
            valid=False,
            missing_keys=[str(m) for m in missing],
            extra_keys=[],
            type_errors=type_errors,
            raw_errors=raw_errors
        )


class AggregationValidator:
    """
    Validates that the Conductor's aggregation of Worker responses is deterministic
    and correct.
    """
    
    @staticmethod
    def validate_no_fabrication(
        worker_outputs: List[Dict[str, Any]],
        aggregated_output: Dict[str, Any],
        key_paths: List[str]
    ) -> Dict[str, Any]:
        """
        Verify that aggregated output only contains data from worker outputs.
        
        Args:
            worker_outputs: List of raw worker response dicts
            aggregated_output: The conductor's aggregated result
            key_paths: Dot-separated paths to check (e.g., "pure", "impure")
            
        Returns:
            Dict with validation results per key path
        """
        results = {}
        
        for key_path in key_paths:
            # Get value from aggregated output
            agg_value = _get_nested_value(aggregated_output, key_path)
            
            # Collect all values from workers for this key
            worker_values = set()
            for worker in worker_outputs:
                worker_val = _get_nested_value(worker, key_path)
                if isinstance(worker_val, list):
                    worker_values.update(worker_val)
                elif worker_val is not None:
                    worker_values.add(worker_val)
            
            # Check if aggregated value exists in worker outputs
            if isinstance(agg_value, list):
                fabricated = [v for v in agg_value if v not in worker_values]
            else:
                fabricated = [] if agg_value in worker_values else [agg_value]
            
            results[key_path] = {
                "valid": len(fabricated) == 0,
                "fabricated_values": fabricated,
                "worker_provided_values": list(worker_values)
            }
        
        return results
    
    @staticmethod
    def validate_majority_vote(
        worker_outputs: List[Dict[str, Any]],
        aggregated_output: Dict[str, Any],
        item: str,
        category_key: str
    ) -> Dict[str, Any]:
        """
        Validate that an item's classification follows majority vote.
        
        Args:
            worker_outputs: List of worker responses
            aggregated_output: The aggregated result
            item: The item being classified (e.g., "add")
            category_key: The key where item should be found (e.g., "pure")
            
        Returns:
            Dict with vote analysis
        """
        votes_for = 0
        votes_against = 0
        
        for worker in worker_outputs:
            value = _get_nested_value(worker, category_key)
            if isinstance(value, list) and item in value:
                votes_for += 1
            else:
                votes_against += 1
        
        agg_value = _get_nested_value(aggregated_output, category_key) or []
        in_aggregated = item in agg_value if isinstance(agg_value, list) else False
        
        # Determine expected behavior
        should_be_included = votes_for > votes_against
        
        return {
            "item": item,
            "category": category_key,
            "votes_for": votes_for,
            "votes_against": votes_against,
            "in_aggregated_result": in_aggregated,
            "should_be_included": should_be_included,
            "correct": in_aggregated == should_be_included,
            "issue": None if in_aggregated == should_be_included else 
                     f"Item was {'included' if in_aggregated else 'excluded'} but majority vote was {'for' if should_be_included else 'against'}"
        }


def _get_nested_value(d: Dict[str, Any], path: str) -> Any:
    """Get a nested value from a dict using dot notation."""
    keys = path.split('.')
    value = d
    for key in keys:
        if isinstance(value, dict) and key in value:
            value = value[key]
        else:
            return None
    return value
