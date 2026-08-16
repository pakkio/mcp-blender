from .providers.ambientcg import AmbientCGProvider
from .providers.base import AssetProvider
from .providers.polyhaven import PolyHavenProvider
from .providers.sketchfab import SketchfabProvider

_PROVIDERS: dict[str, AssetProvider] = {
    "polyhaven": PolyHavenProvider(),
    "ambientcg": AmbientCGProvider(),
    "sketchfab": SketchfabProvider(),
}


def get_provider(name: str) -> AssetProvider:
    provider = _PROVIDERS.get(name)
    if provider is None:
        raise KeyError(f"Unknown asset provider '{name}'. Available: {', '.join(_PROVIDERS)}")
    return provider


def all_providers() -> list[AssetProvider]:
    return list(_PROVIDERS.values())
