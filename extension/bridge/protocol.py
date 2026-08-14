"""Wire-envelope shaping shared by the server and the dispatcher.

Request:  {"id": "...", "method": "...", "params": {...}}
Success:  {"id": "...", "result": {...}}
Error:    {"id": "...", "error": {"type": "...", "message": "...", "details": ...}}

Kept deliberately small and dependency-free: a flat method-name-keyed RPC,
no JSON-RPC version field, no batching. See ../../mcp_server/src/
mcp_blender_pakkio/errors.py for the client-side mirror of ERROR_TYPES.
"""

VALIDATION_ERROR = "validation_error"
TOOL_EXECUTION_ERROR = "tool_execution_error"
INTERNAL_ERROR = "internal_error"
INVALID_JSON = "invalid_json"
UNKNOWN_METHOD = "unknown_method"


def success_envelope(request_id, result: dict) -> dict:
    return {"id": request_id, "result": result}


def error_envelope(request_id, error_type: str, message: str, details=None) -> dict:
    return {
        "id": request_id,
        "error": {"type": error_type, "message": message, "details": details},
    }
