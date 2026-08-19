from typing import Literal, Optional
from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel

from ..bridge import BlenderBridge
from ..errors import BridgeError, ErrorType
from ..vlm import VLMError, critique_image, extract_png_bytes, is_configured

EvalView = Literal["MULTIVIEW", "FOCUS"]


class EvaluateSceneVisuallyParams(BaseModel):
    question: str
    target_object: Optional[str] = None
    view: EvalView = "MULTIVIEW"
    model: Optional[str] = None


def register_vision_eval_tools(mcp: FastMCP, bridge: BlenderBridge):
    @mcp.tool(
        name="evaluate_scene_visually",
        description="When you cannot see rendered images yourself, use this to get a text critique of the scene from a "
        "cheap vision-capable model via OpenRouter. Captures a multiview audit (or a focused close-up on target_object) "
        "and asks the given question about it. Requires OPENROUTER_API_KEY in .env; without it, returns guidance "
        "pointing at capture_multiview_audit instead of failing silently.",
    )
    async def evaluate_scene_visually(
        question: str,
        target_object: Optional[str] = None,
        view: EvalView = "MULTIVIEW",
        model: Optional[str] = None,
    ) -> dict:
        params = EvaluateSceneVisuallyParams(
            question=question, target_object=target_object, view=view, model=model
        )

        if not is_configured():
            return {
                "success": False,
                "message": (
                    "OPENROUTER_API_KEY is not set, so evaluate_scene_visually cannot run. "
                    "Add it to .env, or call capture_multiview_audit(include_base64=True) yourself and "
                    "look at the returned image directly if you are a vision-capable model."
                ),
            }

        if params.view == "FOCUS":
            if not params.target_object:
                raise BridgeError(ErrorType.VALIDATION, "target_object is required when view='FOCUS'")
            capture = await bridge.send_request(
                "inspect_focus_shot",
                {"target_object": params.target_object, "include_base64": True},
            )
            image_key = "image_base64"
        else:
            capture = await bridge.send_request(
                "capture_multiview_audit",
                {"target_object": params.target_object, "include_base64": True},
            )
            image_key = "base64_data_uri"

        if not capture.get("success"):
            raise BridgeError(ErrorType.TOOL_EXECUTION, capture.get("message", "scene capture failed"))

        png_bytes = extract_png_bytes(capture, image_key)
        if not png_bytes:
            raise BridgeError(ErrorType.TOOL_EXECUTION, "Scene capture did not return image data")

        try:
            verdict = await critique_image(params.question, png_bytes, params.model)
        except VLMError as exc:
            return {"success": False, "message": str(exc)}

        return {
            "success": True,
            "question": params.question,
            "critique": verdict["critique"],
            "model": verdict["model"],
            "prompt_tokens": verdict["prompt_tokens"],
            "completion_tokens": verdict["completion_tokens"],
        }

    return evaluate_scene_visually
