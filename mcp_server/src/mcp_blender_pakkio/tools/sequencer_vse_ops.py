from typing import Literal, Optional
from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel

from ..bridge import BlenderBridge
from ..errors import BridgeError, ErrorType

SequencerAction = Literal["ADD_SOUND", "ADD_AUDIO", "ADD_COLOR", "CLEAR_ALL"]


class ManageSequencerStripsParams(BaseModel):
    action: SequencerAction = "ADD_SOUND"
    filepath: Optional[str] = None
    name: str = "Strip"
    channel: int = 1
    frame_start: int = 1
    length: int = 50
    color: list[float] = [0.0, 0.0, 0.0]


class ConfigureSequencerAudioParams(BaseModel):
    strip_name: Optional[str] = None
    volume: Optional[float] = None
    pan: Optional[float] = None
    pitch: Optional[float] = None
    mute: Optional[bool] = None


def register_sequencer_vse_tools(mcp: FastMCP, bridge: BlenderBridge):
    @mcp.tool(
        name="manage_sequencer_strips",
        description="Add audio sound effects, background music, video clips, or color adjustment strips to Blender's Video Sequence Editor (VSE) timeline.",
    )
    async def manage_sequencer_strips(
        action: SequencerAction = "ADD_SOUND",
        filepath: Optional[str] = None,
        name: str = "Strip",
        channel: int = 1,
        frame_start: int = 1,
        length: int = 50,
        color: list[float] = [0.0, 0.0, 0.0],
    ) -> dict:
        params = ManageSequencerStripsParams(
            action=action,
            filepath=filepath,
            name=name,
            channel=channel,
            frame_start=frame_start,
            length=length,
            color=color,
        )
        result = await bridge.send_request("manage_sequencer_strips", params.model_dump())
        if not result.get("success"):
            raise BridgeError(ErrorType.TOOL_EXECUTION, result.get("message", "manage_sequencer_strips failed"))
        return result

    @mcp.tool(
        name="configure_sequencer_audio",
        description="Adjust audio volume, pan, pitch, and mute state on timeline audio strips.",
    )
    async def configure_sequencer_audio(
        strip_name: Optional[str] = None,
        volume: Optional[float] = None,
        pan: Optional[float] = None,
        pitch: Optional[float] = None,
        mute: Optional[bool] = None,
    ) -> dict:
        params = ConfigureSequencerAudioParams(
            strip_name=strip_name,
            volume=volume,
            pan=pan,
            pitch=pitch,
            mute=mute,
        )
        result = await bridge.send_request("configure_sequencer_audio", params.model_dump())
        if not result.get("success"):
            raise BridgeError(ErrorType.TOOL_EXECUTION, result.get("message", "configure_sequencer_audio failed"))
        return result

    return manage_sequencer_strips, configure_sequencer_audio
