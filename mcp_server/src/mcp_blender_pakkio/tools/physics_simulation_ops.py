from typing import Literal, Optional
from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel

from ..bridge import BlenderBridge
from ..errors import BridgeError, ErrorType

RigidBodyType = Literal["ACTIVE", "PASSIVE"]
CollisionShape = Literal[
    "BOX",
    "SPHERE",
    "CAPSULE",
    "CYLINDER",
    "CONE",
    "CONVEX_HULL",
    "MESH",
]
ClothPreset = Literal["SILK", "COTTON", "LEATHER", "DENIM", "RUBBER"]
ForceFieldType = Literal["WIND", "VORTEX", "TURBULENCE", "FORCE", "MAGNETIC"]


class SetupRigidBodySimulationParams(BaseModel):
    object_name: str
    body_type: RigidBodyType = "ACTIVE"
    mass: float = 1.0
    friction: float = 0.5
    bounciness: float = 0.1
    collision_shape: CollisionShape = "CONVEX_HULL"
    settle_simulation: bool = False
    settle_frames: int = 40


class SetupClothSimulationParams(BaseModel):
    object_name: str
    preset: ClothPreset = "COTTON"
    pin_vertex_group: Optional[str] = None
    use_pressure: bool = False
    pressure: float = 1.0


class AddForceFieldParams(BaseModel):
    field_type: ForceFieldType = "WIND"
    strength: float = 10.0
    flow: float = 1.0
    location: list[float] = [0.0, 0.0, 0.0]
    rotation: list[float] = [0.0, 0.0, 0.0]


def register_physics_simulation_tools(mcp: FastMCP, bridge: BlenderBridge):
    @mcp.tool(
        name="setup_rigid_body_simulation",
        description="Configure rigid body physics (Active/Passive, mass, friction, bounciness, collision shapes) with optional 'settle_simulation' to naturally drop and rest props onto surfaces.",
    )
    async def setup_rigid_body_simulation(
        object_name: str,
        body_type: RigidBodyType = "ACTIVE",
        mass: float = 1.0,
        friction: float = 0.5,
        bounciness: float = 0.1,
        collision_shape: CollisionShape = "CONVEX_HULL",
        settle_simulation: bool = False,
        settle_frames: int = 40,
    ) -> dict:
        params = SetupRigidBodySimulationParams(
            object_name=object_name,
            body_type=body_type,
            mass=mass,
            friction=friction,
            bounciness=bounciness,
            collision_shape=collision_shape,
            settle_simulation=settle_simulation,
            settle_frames=settle_frames,
        )
        result = await bridge.send_request("setup_rigid_body_simulation", params.model_dump())
        if not result.get("success"):
            raise BridgeError(ErrorType.TOOL_EXECUTION, result.get("message", "setup_rigid_body_simulation failed"))
        return result

    @mcp.tool(
        name="setup_cloth_simulation",
        description="Add and configure Cloth physics simulations with fabric presets (SILK, COTTON, LEATHER, DENIM, RUBBER), pinning groups, and internal pressure.",
    )
    async def setup_cloth_simulation(
        object_name: str,
        preset: ClothPreset = "COTTON",
        pin_vertex_group: Optional[str] = None,
        use_pressure: bool = False,
        pressure: float = 1.0,
    ) -> dict:
        params = SetupClothSimulationParams(
            object_name=object_name,
            preset=preset,
            pin_vertex_group=pin_vertex_group,
            use_pressure=use_pressure,
            pressure=pressure,
        )
        result = await bridge.send_request("setup_cloth_simulation", params.model_dump())
        if not result.get("success"):
            raise BridgeError(ErrorType.TOOL_EXECUTION, result.get("message", "setup_cloth_simulation failed"))
        return result

    @mcp.tool(
        name="add_force_field",
        description="Add a 3D Physics Force Field (WIND, VORTEX, TURBULENCE, FORCE, MAGNETIC) with strength and direction.",
    )
    async def add_force_field(
        field_type: ForceFieldType = "WIND",
        strength: float = 10.0,
        flow: float = 1.0,
        location: list[float] = [0.0, 0.0, 0.0],
        rotation: list[float] = [0.0, 0.0, 0.0],
    ) -> dict:
        params = AddForceFieldParams(
            field_type=field_type,
            strength=strength,
            flow=flow,
            location=location,
            rotation=rotation,
        )
        result = await bridge.send_request("add_force_field", params.model_dump())
        if not result.get("success"):
            raise BridgeError(ErrorType.TOOL_EXECUTION, result.get("message", "add_force_field failed"))
        return result

    return setup_rigid_body_simulation, setup_cloth_simulation, add_force_field
