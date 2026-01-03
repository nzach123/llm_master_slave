"""
Tests for ValidationGate module.

Verifies:
- Schema validation works correctly
- Errors are properly surfaced
- JSON parsing errors are handled
- Statistics are tracked
"""

import pytest
import json
from pydantic import BaseModel
from typing import List, Optional

from core.validation import ValidationGate, SchemaValidationError, ValidationResult


# Test models
class SimpleModel(BaseModel):
    name: str
    value: int

class NestedModel(BaseModel):
    items: List[str]
    metadata: Optional[dict] = None

class StrictModel(BaseModel):
    required_field: str
    another_required: int


class TestValidationGate:
    """Tests for ValidationGate class."""
    
    @pytest.fixture
    def validator(self):
        return ValidationGate()
    
    def test_valid_data_passes(self, validator):
        """Test that valid data passes validation."""
        data = {"name": "test", "value": 42}
        result = validator.validate(data, SimpleModel, "test_context")
        
        assert result.valid is True
        assert result.data is not None
        assert result.data.name == "test"
        assert result.data.value == 42
        assert len(result.errors) == 0
    
    def test_missing_field_fails(self, validator):
        """Test that missing required fields are detected."""
        data = {"name": "test"}  # Missing 'value'
        result = validator.validate(data, SimpleModel, "test_context")
        
        assert result.valid is False
        assert result.data is None
        assert len(result.errors) > 0
        assert any("value" in str(e.get("loc", [])) for e in result.errors)
    
    def test_wrong_type_fails(self, validator):
        """Test that wrong types are detected."""
        data = {"name": "test", "value": "not_an_int"}
        result = validator.validate(data, SimpleModel, "test_context")
        
        assert result.valid is False
        assert len(result.errors) > 0
    
    def test_require_valid_returns_model(self, validator):
        """Test that require_valid returns the model on success."""
        data = {"name": "test", "value": 42}
        model = validator.require_valid(data, SimpleModel, "test_context")
        
        assert isinstance(model, SimpleModel)
        assert model.name == "test"
    
    def test_require_valid_raises_on_invalid(self, validator):
        """Test that require_valid raises SchemaValidationError on failure."""
        data = {"name": "test"}  # Missing 'value'
        
        with pytest.raises(SchemaValidationError) as exc_info:
            validator.require_valid(data, SimpleModel, "test_context")
        
        assert "test_context" in str(exc_info.value)
        assert len(exc_info.value.errors) > 0
    
    def test_validate_json_valid(self, validator):
        """Test JSON string validation."""
        json_str = '{"name": "test", "value": 42}'
        result = validator.validate_json(json_str, SimpleModel, "test_context")
        
        assert result.valid is True
        assert result.data.name == "test"
    
    def test_validate_json_invalid_json(self, validator):
        """Test that invalid JSON is caught."""
        json_str = '{not valid json}'
        result = validator.validate_json(json_str, SimpleModel, "test_context")
        
        assert result.valid is False
        assert any(e.get("type") == "json_parse_error" for e in result.errors)
    
    def test_validate_json_valid_json_invalid_schema(self, validator):
        """Test valid JSON that fails schema validation."""
        json_str = '{"name": "test"}'  # Missing 'value'
        result = validator.validate_json(json_str, SimpleModel, "test_context")
        
        assert result.valid is False
        assert not any(e.get("type") == "json_parse_error" for e in result.errors)
    
    def test_require_valid_json_success(self, validator):
        """Test require_valid_json returns model on success."""
        json_str = '{"name": "test", "value": 42}'
        model = validator.require_valid_json(json_str, SimpleModel, "test_context")
        
        assert isinstance(model, SimpleModel)
    
    def test_require_valid_json_raises_on_invalid(self, validator):
        """Test require_valid_json raises on failure."""
        json_str = '{"name": "test"}'
        
        with pytest.raises(SchemaValidationError):
            validator.require_valid_json(json_str, SimpleModel, "test_context")
    
    def test_stats_tracking(self, validator):
        """Test that validation statistics are tracked."""
        # Do some validations
        validator.validate({"name": "a", "value": 1}, SimpleModel)
        validator.validate({"name": "b", "value": 2}, SimpleModel)
        validator.validate({"name": "c"}, SimpleModel)  # Fails
        
        stats = validator.stats
        
        assert stats["total_validations"] == 3
        assert stats["failures"] == 1
        assert stats["success_rate"] == pytest.approx(2/3)
    
    def test_nested_model_validation(self, validator):
        """Test validation of nested models."""
        data = {"items": ["a", "b", "c"], "metadata": {"key": "value"}}
        result = validator.validate(data, NestedModel, "nested_test")
        
        assert result.valid is True
        assert result.data.items == ["a", "b", "c"]
    
    def test_context_in_errors(self, validator):
        """Test that context is included in validation results."""
        data = {"wrong": "data"}
        result = validator.validate(data, SimpleModel, "my_special_context")
        
        assert result.context == "my_special_context"
    
    def test_schema_validation_error_str(self):
        """Test SchemaValidationError string representation."""
        error = SchemaValidationError(
            "Test error",
            errors=[
                {"loc": ["field1"], "msg": "field required", "type": "missing"},
                {"loc": ["field2"], "msg": "wrong type", "type": "type_error"},
            ],
            raw_input={"test": "data"},
            context="test_context"
        )
        
        error_str = str(error)
        assert "test_context" in error_str
        assert "field1" in error_str or "field2" in error_str


class TestValidationResult:
    """Tests for ValidationResult dataclass."""
    
    def test_to_dict(self):
        """Test ValidationResult serialization."""
        result = ValidationResult(
            valid=False,
            data=None,
            errors=[{"loc": ["test"], "msg": "error"}],
            raw_input={"key": "value"},
            context="test"
        )
        
        d = result.to_dict()
        
        assert d["valid"] is False
        assert d["errors"] == [{"loc": ["test"], "msg": "error"}]
        assert d["context"] == "test"
        assert "key" in d["raw_input_keys"]
