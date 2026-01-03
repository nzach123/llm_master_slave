"""
Validation Gate Module.

Provides explicit schema validation with clear error surfacing.
This addresses ISSUE-002: Schema Validation Not Explicitly Surfaced.

Key features:
- All validation errors are captured and surfaced clearly
- Errors include context for debugging
- Never silently accepts invalid data
"""

import json
import logging
from typing import Dict, Any, Type, Optional, List
from dataclasses import dataclass, field
from pydantic import BaseModel, ValidationError


@dataclass
class ValidationResult:
    """Result of a validation operation."""
    valid: bool
    data: Optional[BaseModel]
    errors: List[Dict[str, Any]]
    raw_input: Dict[str, Any]
    context: str = ""
    
    def to_dict(self) -> dict:
        return {
            "valid": self.valid,
            "errors": self.errors,
            "context": self.context,
            "raw_input_keys": list(self.raw_input.keys()) if self.raw_input else []
        }


class SchemaValidationError(Exception):
    """
    Explicit exception for schema validation failures.
    
    This exception is raised when validation fails and includes
    all error details for debugging.
    """
    
    def __init__(
        self, 
        message: str, 
        errors: List[Dict[str, Any]], 
        raw_input: Dict[str, Any],
        context: str = ""
    ):
        super().__init__(message)
        self.errors = errors
        self.raw_input = raw_input
        self.context = context
    
    def __str__(self) -> str:
        error_summary = "; ".join(
            f"{e.get('loc', 'unknown')}: {e.get('msg', 'no message')}"
            for e in self.errors[:3]  # Show first 3 errors
        )
        if len(self.errors) > 3:
            error_summary += f" (and {len(self.errors) - 3} more)"
        return f"{self.args[0]} [{self.context}]: {error_summary}"


class ValidationGate:
    """
    Explicit validation gate that surfaces all errors clearly.
    
    This class provides a clear, explicit validation step that:
    1. Validates data against Pydantic schemas
    2. Captures all errors with full context
    3. Never silently accepts invalid data
    4. Provides clear error messages for debugging
    
    Usage:
        validator = ValidationGate()
        result = validator.validate(data, MyModel, "context_name")
        
        if result.valid:
            use(result.data)
        else:
            handle_errors(result.errors)
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self._validation_count = 0
        self._failure_count = 0
    
    def validate(
        self, 
        data: Dict[str, Any], 
        schema: Type[BaseModel],
        context: str = ""
    ) -> ValidationResult:
        """
        Validate data against schema with explicit error surfacing.
        
        Args:
            data: Raw data dictionary to validate
            schema: Pydantic model class to validate against
            context: Context string for error messages (e.g., "ResearcherSpoke.handle_task")
            
        Returns:
            ValidationResult with validation status and any errors
        """
        self._validation_count += 1
        
        try:
            validated = schema.model_validate(data)
            self.logger.debug(f"Validation passed [{context}]")
            
            return ValidationResult(
                valid=True,
                data=validated,
                errors=[],
                raw_input=data,
                context=context
            )
            
        except ValidationError as e:
            self._failure_count += 1
            
            errors = [
                {
                    "loc": list(err["loc"]) if err.get("loc") else [],
                    "msg": err.get("msg", "unknown error"),
                    "type": err.get("type", "unknown")
                }
                for err in e.errors()
            ]
            
            self.logger.error(
                f"Validation FAILED [{context}]: {len(errors)} errors. "
                f"First error: {errors[0] if errors else 'none'}"
            )
            
            return ValidationResult(
                valid=False,
                data=None,
                errors=errors,
                raw_input=data,
                context=context
            )
    
    def require_valid(
        self, 
        data: Dict[str, Any], 
        schema: Type[BaseModel],
        context: str = ""
    ) -> BaseModel:
        """
        Validate and raise explicit exception if invalid.
        
        This is a stricter version of validate() that raises an exception
        instead of returning a ValidationResult on failure.
        
        Args:
            data: Raw data dictionary to validate
            schema: Pydantic model class to validate against
            context: Context string for error messages
            
        Returns:
            Validated Pydantic model instance
            
        Raises:
            SchemaValidationError: If validation fails
        """
        result = self.validate(data, schema, context)
        
        if not result.valid:
            raise SchemaValidationError(
                f"Schema validation failed",
                errors=result.errors,
                raw_input=result.raw_input,
                context=context
            )
        
        return result.data
    
    def validate_json(
        self,
        json_string: str,
        schema: Type[BaseModel],
        context: str = ""
    ) -> ValidationResult:
        """
        Parse JSON string and validate against schema.
        
        This combines JSON parsing and schema validation in one step,
        with clear error messages for both failure modes.
        
        Args:
            json_string: Raw JSON string to parse and validate
            schema: Pydantic model class to validate against
            context: Context string for error messages
            
        Returns:
            ValidationResult with validation status and any errors
        """
        # Try to parse JSON first
        try:
            data = json.loads(json_string)
        except json.JSONDecodeError as e:
            self._failure_count += 1
            self.logger.error(f"JSON parse FAILED [{context}]: {e}")
            
            return ValidationResult(
                valid=False,
                data=None,
                errors=[{
                    "loc": ["__json__"],
                    "msg": f"JSON parse error: {str(e)}",
                    "type": "json_parse_error"
                }],
                raw_input={"raw_content": json_string[:500]},  # Truncate for safety
                context=context
            )
        
        # Then validate schema
        return self.validate(data, schema, context)
    
    def require_valid_json(
        self,
        json_string: str,
        schema: Type[BaseModel],
        context: str = ""
    ) -> BaseModel:
        """
        Parse JSON and validate, raising exception on failure.
        
        Args:
            json_string: Raw JSON string to parse and validate
            schema: Pydantic model class to validate against
            context: Context string for error messages
            
        Returns:
            Validated Pydantic model instance
            
        Raises:
            SchemaValidationError: If JSON parsing or validation fails
        """
        result = self.validate_json(json_string, schema, context)
        
        if not result.valid:
            raise SchemaValidationError(
                f"JSON validation failed",
                errors=result.errors,
                raw_input=result.raw_input,
                context=context
            )
        
        return result.data
    
    @property
    def stats(self) -> Dict[str, int]:
        """Get validation statistics."""
        return {
            "total_validations": self._validation_count,
            "failures": self._failure_count,
            "success_rate": (
                (self._validation_count - self._failure_count) / self._validation_count
                if self._validation_count > 0 else 1.0
            )
        }
