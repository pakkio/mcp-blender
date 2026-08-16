"""Shared types for online asset providers.

Each provider implements search() (always keyless where the API allows it)
and download() (may require a token; must raise ProviderError with an
actionable message rather than a bare HTTP failure when a required key is
missing).
"""

from dataclasses import dataclass, field
from typing import Optional, Protocol


class ProviderError(Exception):
    pass


@dataclass
class AssetHit:
    id: str
    provider: str
    name: str
    asset_type: str  # "MODEL" | "TEXTURE" | "HDRI"
    license: str
    requires_token: bool
    preview_url: Optional[str] = None
    tri_count_hint: Optional[int] = None
    extra: dict = field(default_factory=dict)


@dataclass
class DownloadedAsset:
    filepath: str
    provider: str
    asset_id: str
    license: str
    attribution: str
    from_cache: bool


class AssetProvider(Protocol):
    name: str
    requires_token: bool

    def is_available(self) -> bool: ...

    async def search(self, query: str, asset_type: str, limit: int) -> list[AssetHit]: ...

    async def download(self, asset_id: str, dest_dir: str) -> DownloadedAsset: ...
