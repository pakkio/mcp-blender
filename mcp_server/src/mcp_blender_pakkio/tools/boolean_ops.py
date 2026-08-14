from typing import Literal, Optional
from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel

from ..bridge import BlenderBridge
from ..errors import BridgeError, ErrorType

BooleanOperation = Literal["UNION", "DIFFERENCE", "INTERSECT", "SLICE"]
BooleanSolver = Literal["FAST", "EXACT"]


class BooleanOperationParams(BaseModel):
    target_object: str
    operand_object: str
    operation: BooleanOperation = "UNION"
    solver: BooleanSolver = "EXACT"
    apply_immediately: bool = True
    delete_operand: bool = False


def register_boolean_tools(mcp: FastMCP, bridge: BlenderBridge):
    @mcp.tool(
        name="boolean_operation",
        description="Perform boolean operations (UNION, DIFFERENCE, INTERSECT, SLICE) between mesh objects using FAST or EXACT solvers.",
    )
    async def boolean_operation(
        target_object: str,
        operand_object: str,
        operation: BooleanOperation = "UNION",
        solver: BooleanSolver = "EXACT",
        apply_immediately: bool = True,
        delete_operand: bool = False,
    ) -> dict:
        params = BooleanOperationParams(
            target_object=target_object,
            operand_object=operand_object,
            operation=operation,
            solver=solver,
            apply_immediately=apply_immediately,
            delete_operand=delete_operand,
        )
        result = await bridge.send_request("boolean_operation", params.model_dump())
        if not result.get("success"):
            raise BridgeError(ErrorType.TOOL_EXECUTION, result.get("message", "boolean_operation failed"))
        return result

    return boolean_operation
