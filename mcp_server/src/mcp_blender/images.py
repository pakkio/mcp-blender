"""Turns base64 image payloads inside bridge results into real MCP Image
content blocks, so vision-capable hosts actually see renders instead of
receiving an unreadable multi-hundred-KB base64 string as text.

Pass-through when no base64 was requested/returned, so tools stay
backward-compatible for callers that only want the metadata dict.
"""

import base64

from mcp.server.fastmcp import Image


def image_result(result: dict, key: str = "image_base64") -> list | dict:
    raw = result.get(key)
    if not raw:
        return result

    if raw.startswith("data:"):
        raw = raw.split(",", 1)[1]

    try:
        data = base64.b64decode(raw)
    except (ValueError, TypeError):
        return result

    metadata = {k: v for k, v in result.items() if k != key}
    return [Image(data=data, format="png"), metadata]
