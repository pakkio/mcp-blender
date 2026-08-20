from .providers.ambientcg import AmbientCGProvider
from .providers.base import AssetProvider
from .providers.meshy import MeshyProvider
from .providers.polyhaven import PolyHavenProvider
from .providers.sketchfab import SketchfabProvider
from .providers.trellis import TrellisProvider
from .providers.tripo import TripoProvider

_PROVIDERS: dict[str, AssetProvider] = {
    "polyhaven": PolyHavenProvider(),
    "ambientcg": AmbientCGProvider(),
    "sketchfab": SketchfabProvider(),
    "meshy": MeshyProvider(),
    "tripo": TripoProvider(),
    "trellis": TrellisProvider(),
}


def get_provider(name: str) -> AssetProvider:
    provider = _PROVIDERS.get(name)
    if provider is None:
        raise KeyError(f"Unknown asset provider '{name}'. Available: {', '.join(_PROVIDERS)}")
    return provider


def all_providers() -> list[AssetProvider]:
    return list(_PROVIDERS.values())
