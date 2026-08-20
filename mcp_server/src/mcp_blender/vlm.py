"""Thin OpenRouter chat-completions client used as a vision fallback when the
host model calling this MCP server cannot itself see image content blocks.
"""

import base64
import os
from typing import Optional

import httpx

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
DEFAULT_VISION_MODEL = "google/gemini-2.5-flash"
REQUEST_TIMEOUT_S = 60.0


class VLMError(Exception):
    pass


def is_configured() -> bool:
    return bool(os.environ.get("OPENROUTER_API_KEY"))


def extract_png_bytes(result: dict, key: str) -> Optional[bytes]:
    """Shared by every caller that turns a bridge screenshot/capture result
    (base64, optionally as a data: URI) into raw bytes for critique_image."""
    raw = result.get(key)
    if not raw:
        return None
    if raw.startswith("data:"):
        raw = raw.split(",", 1)[1]
    return base64.b64decode(raw)


def resolve_model(override: str | None = None) -> str:
    return override or os.environ.get("OPENROUTER_VISION_MODEL") or DEFAULT_VISION_MODEL


async def critique_image(question: str, png_bytes: bytes, model: str | None = None) -> dict:
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        raise VLMError(
            "OPENROUTER_API_KEY is not set. Add it to .env to enable evaluate_scene_visually, "
            "or verify the render yourself via capture_multiview_audit(include_base64=True)."
        )

    resolved_model = resolve_model(model)
    data_uri = "data:image/png;base64," + base64.b64encode(png_bytes).decode("utf-8")

    payload = {
        "model": resolved_model,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": question},
                    {"type": "image_url", "image_url": {"url": data_uri}},
                ],
            }
        ],
    }

    _VISION_INCOMPATIBLE = ("does not support image", "image_url", "cannot read", "image input")

    tried_models = [resolved_model]
    async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT_S) as client:
        for attempt_model in tried_models:
            payload["model"] = attempt_model
            try:
                response = await client.post(
                    OPENROUTER_URL,
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                )
            except httpx.HTTPError as exc:
                raise VLMError(f"OpenRouter request failed: {exc}") from exc

            text = response.text[:2000]
            _body = {}
            try:
                _body = response.json() if response.status_code == 200 else {}
            except ValueError:
                pass

            # Check both HTTP error body and (crucially) 200 OK content for
            # vision-incompatibility signals -- some models return the error
            # as successful content rather than as an HTTP error.
            _critique_candidate = ""
            try:
                _critique_candidate = _body["choices"][0]["message"]["content"]
            except (KeyError, IndexError, TypeError):
                pass

            _combined = (text + " " + _critique_candidate).lower()
            vision_incompatible = any(sig in _combined for sig in _VISION_INCOMPATIBLE)

            if response.status_code == 200 and not vision_incompatible:
                critique = _critique_candidate
                break

            if vision_incompatible and attempt_model != DEFAULT_VISION_MODEL:
                tried_models.append(DEFAULT_VISION_MODEL)
                continue

            if vision_incompatible:
                raise VLMError(
                    f"The model '{attempt_model}' does not support image input. "
                    f"Set OPENROUTER_VISION_MODEL to a vision-capable model "
                    f"(e.g. 'google/gemini-2.5-flash' or 'qwen/qwen3-vl-32b-instruct') "
                    f"in your .env file, or remove the variable to use the default."
                )

            raise VLMError(f"OpenRouter returned {response.status_code}: {text}")

    usage = _body.get("usage", {})
    return {
        "critique": critique,
        "model": payload["model"],
        "prompt_tokens": usage.get("prompt_tokens"),
        "completion_tokens": usage.get("completion_tokens"),
    }
