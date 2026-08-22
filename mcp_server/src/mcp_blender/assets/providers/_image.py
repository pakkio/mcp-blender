"""Shared plumbing for image-to-3D generation.

An AI generation request that starts from an *image* instead of a prompt
needs three things no text provider needed before:

1. A way to turn a local file path into what every image-to-3D API actually
   accepts -- a base64 data URI (Meshy takes one directly; Tripo and HF
   Inference Endpoints both accept the same encoding as an upload).
2. A content-derived asset_id, so the existing find_cached_file() machinery
   gives repeat generations of the same picture a free disk hit without any
   new cache logic.
3. Light validation up front: a missing/mis-typed local path should fail
   with an actionable ProviderError here rather than as a confusing HTTP 400
   from a provider minutes into a paid generation run.
"""

import base64
import hashlib
import mimetypes
from pathlib import Path

from .base import ProviderError

_SUPPORTED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}
_MAX_IMAGE_BYTES = 20 * 1024 * 1024


def image_asset_id(image_path: str | Path) -> str:
    """Content-hash fragment shared by all providers' id schemes:
    '<provider>_img_<sha256[:8]>'. Same picture -> same id -> cache hit."""
    data = _read_image_bytes(image_path)
    return hashlib.sha256(data).hexdigest()[:8]


def to_data_uri(image_path: str | Path) -> str:
    """Local image file -> 'data:image/png;base64,...' for provider APIs."""
    data = _read_image_bytes(image_path)
    mime = mimetypes.guess_type(str(image_path))[0] or "image/png"
    return f"data:{mime};base64,{base64.b64encode(data).decode('ascii')}"


def _read_image_bytes(image_path: str | Path) -> bytes:
    path = Path(image_path)
    if not path.is_file():
        raise ProviderError(
            f"Image file not found: '{path}'. Pass image_path pointing to an existing "
            ".png/.jpg/.jpeg/.webp file on disk."
        )
    if path.suffix.lower() not in _SUPPORTED_EXTENSIONS:
        raise ProviderError(
            f"Unsupported image type '{path.suffix}' for '{path.name}'. "
            f"Supported: {', '.join(sorted(_SUPPORTED_EXTENSIONS))}."
        )
    data = path.read_bytes()
    if len(data) > _MAX_IMAGE_BYTES:
        raise ProviderError(
            f"Image '{path.name}' is {len(data) / 1024 / 1024:.1f} MB; providers cap "
            f"uploads at {_MAX_IMAGE_BYTES // (1024 * 1024)} MB."
        )
    if not data:
        raise ProviderError(f"Image file '{path}' is empty.")
    return data
