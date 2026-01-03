"""
Message Capture and Logging Infrastructure for Test Harness.

This module captures all messages flowing through the orchestration system:
- Tester → Conductor
- Conductor → Workers
- Workers → Conductor

Each message is timestamped and validated for schema compliance.
"""

import json
import time
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Literal
from dataclasses import dataclass, field, asdict
from enum import Enum
from pydantic import BaseModel, ValidationError


class MessageDirection(str, Enum):
    TESTER_TO_CONDUCTOR = "TESTER→CONDUCTOR"
    CONDUCTOR_TO_WORKER = "CONDUCTOR→WORKER"
    WORKER_TO_CONDUCTOR = "WORKER→CONDUCTOR"


@dataclass
class CapturedMessage:
    """A record of a single message in the orchestration flow."""
    timestamp: str
    direction: MessageDirection
    source: str
    destination: str
    payload: Dict[str, Any]
    schema_valid: bool = True
    schema_errors: List[str] = field(default_factory=list)
    latency_ms: Optional[float] = None

    def to_dict(self) -> dict:
        return asdict(self)


class MessageCapture:
    """
    Captures and stores all messages flowing through the orchestration system.
    
    Usage:
        capture = MessageCapture()
        capture.record(direction, source, dest, payload)
        
        # After test
        report = capture.get_summary()
    """
    
    def __init__(self):
        self.messages: List[CapturedMessage] = []
        self._start_time: Optional[float] = None
        self._last_message_time: Optional[float] = None
    
    def start_capture(self):
        """Mark the start of a capture session."""
        self._start_time = time.time()
        self._last_message_time = self._start_time
        self.messages.clear()
    
    def record(
        self,
        direction: MessageDirection,
        source: str,
        destination: str,
        payload: Dict[str, Any],
        schema_model: Optional[type] = None
    ) -> CapturedMessage:
        """
        Record a message.
        
        Args:
            direction: The direction of the message flow
            source: Source component name
            destination: Destination component name
            payload: The message payload (dict)
            schema_model: Optional Pydantic model to validate against
            
        Returns:
            CapturedMessage record
        """
        now = time.time()
        latency = None
        if self._last_message_time:
            latency = (now - self._last_message_time) * 1000  # Convert to ms
        
        # Schema validation
        schema_valid = True
        schema_errors = []
        
        if schema_model:
            try:
                schema_model.model_validate(payload)
            except ValidationError as e:
                schema_valid = False
                schema_errors = [str(err) for err in e.errors()]
        
        message = CapturedMessage(
            timestamp=datetime.now(timezone.utc).isoformat(),
            direction=direction,
            source=source,
            destination=destination,
            payload=payload,
            schema_valid=schema_valid,
            schema_errors=schema_errors,
            latency_ms=latency
        )
        
        self.messages.append(message)
        self._last_message_time = now
        
        return message
    
    def get_messages_by_direction(self, direction: MessageDirection) -> List[CapturedMessage]:
        """Get all messages with a specific direction."""
        return [m for m in self.messages if m.direction == direction]
    
    def get_conductor_to_worker_messages(self) -> List[CapturedMessage]:
        """Get all messages from Conductor to Workers."""
        return self.get_messages_by_direction(MessageDirection.CONDUCTOR_TO_WORKER)
    
    def get_worker_to_conductor_messages(self) -> List[CapturedMessage]:
        """Get all messages from Workers to Conductor."""
        return self.get_messages_by_direction(MessageDirection.WORKER_TO_CONDUCTOR)
    
    def get_schema_violations(self) -> List[CapturedMessage]:
        """Get all messages that failed schema validation."""
        return [m for m in self.messages if not m.schema_valid]
    
    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of the capture session."""
        total_time_ms = 0
        if self._start_time and self._last_message_time:
            total_time_ms = (self._last_message_time - self._start_time) * 1000
        
        return {
            "total_messages": len(self.messages),
            "tester_to_conductor": len(self.get_messages_by_direction(MessageDirection.TESTER_TO_CONDUCTOR)),
            "conductor_to_worker": len(self.get_conductor_to_worker_messages()),
            "worker_to_conductor": len(self.get_worker_to_conductor_messages()),
            "schema_violations": len(self.get_schema_violations()),
            "total_time_ms": total_time_ms,
            "message_log": [m.to_dict() for m in self.messages]
        }
    
    def __len__(self):
        return len(self.messages)
