"""Client-side error taxonomy.

Mirrors extension/bridge/protocol.py's wire-level error `type` strings for
the four that can actually arrive over the wire, plus two purely local
types (CONNECTION, TIMEOUT) synthesized here and never sent by Blender.
"""

from enum import Enum


class ErrorType(str, Enum):
    VALIDATION = "validation_error"
    TOOL_EXECUTION = "tool_execution_error"
    INTERNAL = "internal_error"
    INVALID_JSON = "invalid_json"
    UNKNOWN_METHOD = "unknown_method"
    CONNECTION = "connection_error"
    TIMEOUT = "timeout_error"


class BridgeError(Exception):
    def __init__(self, error_type: ErrorType, message: str, details: str | None = None):
        super().__init__(message)
        self.error_type = error_type
        self.message = message
        self.details = details

    def __repr__(self) -> str:
        return f"BridgeError({self.error_type.value}, {self.message!r})"
