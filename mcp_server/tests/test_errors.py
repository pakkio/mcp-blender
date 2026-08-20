from mcp_blender.errors import BridgeError, ErrorType


def test_error_type_values_match_wire_strings():
    assert ErrorType.VALIDATION.value == "validation_error"
    assert ErrorType.TOOL_EXECUTION.value == "tool_execution_error"
    assert ErrorType.INTERNAL.value == "internal_error"
    assert ErrorType.INVALID_JSON.value == "invalid_json"
    assert ErrorType.UNKNOWN_METHOD.value == "unknown_method"
    assert ErrorType.CONNECTION.value == "connection_error"
    assert ErrorType.TIMEOUT.value == "timeout_error"


def test_bridge_error_round_trips_message_type_details():
    err = BridgeError(ErrorType.TOOL_EXECUTION, "Object not found", details="traceback here")
    assert err.error_type is ErrorType.TOOL_EXECUTION
    assert err.message == "Object not found"
    assert err.details == "traceback here"
    assert str(err) == "Object not found"


def test_bridge_error_details_optional():
    err = BridgeError(ErrorType.CONNECTION, "no connection")
    assert err.details is None
