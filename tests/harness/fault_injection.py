"""
Fault Injection Module for Test Harness.

This module allows injection of various failure modes to test the robustness
of the orchestration system:

- Malformed worker responses
- Missing required fields
- Conflicting worker outputs
- Timeout simulation
- Partial responses
"""

from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass
from enum import Enum
import copy


class FaultType(str, Enum):
    MISSING_FIELD = "MISSING_FIELD"
    MALFORMED_JSON = "MALFORMED_JSON"
    CONFLICTING_OUTPUT = "CONFLICTING_OUTPUT"
    EMPTY_RESPONSE = "EMPTY_RESPONSE"
    TIMEOUT = "TIMEOUT"
    PARTIAL_RESPONSE = "PARTIAL_RESPONSE"
    WRONG_TYPE = "WRONG_TYPE"
    NULL_VALUE = "NULL_VALUE"


@dataclass
class FaultConfig:
    """Configuration for a specific fault injection."""
    fault_type: FaultType
    target_field: Optional[str] = None  # Field to corrupt
    replacement_value: Any = None  # Value to inject
    description: str = ""


class FaultInjector:
    """
    Injects faults into worker responses to test conductor resilience.
    """
    
    def __init__(self):
        self._active_faults: List[FaultConfig] = []
    
    def add_fault(self, config: FaultConfig):
        """Add a fault configuration to be applied."""
        self._active_faults.append(config)
    
    def clear_faults(self):
        """Remove all active fault configurations."""
        self._active_faults.clear()
    
    def inject(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply all active faults to a response.
        
        Args:
            response: The original, valid response
            
        Returns:
            The corrupted response
        """
        result = copy.deepcopy(response)
        
        for fault in self._active_faults:
            result = self._apply_fault(result, fault)
        
        return result
    
    def _apply_fault(self, response: Dict[str, Any], fault: FaultConfig) -> Dict[str, Any]:
        """Apply a single fault to a response."""
        
        if fault.fault_type == FaultType.MISSING_FIELD:
            if fault.target_field and fault.target_field in response:
                del response[fault.target_field]
        
        elif fault.fault_type == FaultType.EMPTY_RESPONSE:
            return {}
        
        elif fault.fault_type == FaultType.CONFLICTING_OUTPUT:
            if fault.target_field:
                response[fault.target_field] = fault.replacement_value
        
        elif fault.fault_type == FaultType.WRONG_TYPE:
            if fault.target_field and fault.target_field in response:
                # Convert to wrong type (e.g., list to string)
                original = response[fault.target_field]
                if isinstance(original, list):
                    response[fault.target_field] = str(original)
                elif isinstance(original, str):
                    response[fault.target_field] = [original]
                elif isinstance(original, bool):
                    response[fault.target_field] = "true" if original else "false"
        
        elif fault.fault_type == FaultType.NULL_VALUE:
            if fault.target_field:
                response[fault.target_field] = None
        
        elif fault.fault_type == FaultType.PARTIAL_RESPONSE:
            # Remove roughly half the expected fields
            keys = list(response.keys())
            for key in keys[len(keys)//2:]:
                del response[key]
        
        return response


# Pre-configured fault scenarios
def malformed_worker_response() -> Dict[str, Any]:
    """
    Returns a response missing the 'impure' field.
    Tests: Does the conductor detect missing required fields?
    """
    return {
        "pure": ["add"],
        # Missing "impure" field
    }


def conflicting_worker_response() -> Dict[str, Any]:
    """
    Returns a response with an incorrect classification.
    Tests: Does the conductor detect/resolve conflicting outputs?
    """
    return {
        "pure": ["append_item"],  # WRONG: append_item has side effects
        "impure": []
    }


def empty_worker_response() -> Dict[str, Any]:
    """
    Returns an empty response.
    Tests: Does the conductor handle empty responses gracefully?
    """
    return {}


def null_fields_response() -> Dict[str, Any]:
    """
    Returns a response with null values.
    Tests: Does the conductor handle null values?
    """
    return {
        "pure": None,
        "impure": None
    }


class MockWorkerFactory:
    """
    Factory for creating mock workers with specific behaviors.
    """
    
    @staticmethod
    def create_failing_worker(fail_count: int = 1) -> Callable:
        """
        Create a worker that fails N times before succeeding.
        
        Args:
            fail_count: Number of times to fail before success
            
        Returns:
            Callable mock worker
        """
        attempts = [0]
        
        def worker(task: Dict[str, Any]) -> Dict[str, Any]:
            attempts[0] += 1
            if attempts[0] <= fail_count:
                raise Exception(f"Simulated failure (attempt {attempts[0]})")
            return {"pure": ["add"], "impure": ["append_item", "now"]}
        
        return worker
    
    @staticmethod
    def create_conflicting_workers() -> List[Callable]:
        """
        Create two workers that produce conflicting outputs.
        
        Returns:
            List of two mock worker callables
        """
        def worker1(task: Dict[str, Any]) -> Dict[str, Any]:
            return {
                "pure": ["add"],
                "impure": ["append_item", "now"]
            }
        
        def worker2(task: Dict[str, Any]) -> Dict[str, Any]:
            return {
                "pure": ["add", "append_item"],  # CONFLICTS with worker1
                "impure": ["now"]
            }
        
        return [worker1, worker2]
    
    @staticmethod
    def create_partial_responder() -> Callable:
        """
        Create a worker that returns incomplete responses.
        
        Returns:
            Callable mock worker
        """
        def worker(task: Dict[str, Any]) -> Dict[str, Any]:
            return {
                "pure": ["add"],
                # Missing impure entirely
            }
        
        return worker
