"""NumPy proximity clustering with bounded temporary arrays."""
import itertools

import numpy as np


def cluster_centers(centers, threshold_ratio=0.18):
    points = np.asarray(centers, dtype=np.float64).reshape(-1, 3)
    n = len(points)
    if not n:
        return []
    if not np.isfinite(points).all():
        raise ValueError("Part centers must contain finite coordinates")
    threshold = max(float(np.linalg.norm(np.ptp(points, axis=0))) * threshold_ratio, 1e-6)
    grid = {}
    for i, key in enumerate(np.floor((points - points.min(axis=0)) / threshold).astype(np.int64)):
        grid.setdefault(tuple(key), []).append(i)
    parent = np.arange(n)
    offsets = tuple(itertools.product((-1, 0, 1), repeat=3))

    def roots(indices):
        current = parent[indices]
        while True:
            following = parent[current]
            if np.array_equal(current, following):
                parent[indices] = current
                return current
            current = following

    for key, indices in grid.items():
        neighbors = np.asarray([
            j for offset in offsets
            for j in grid.get(tuple(key[k] + offset[k] for k in range(3)), ())
        ], dtype=np.intp)
        for i in indices:
            # No NxN distance matrix, even when all points share one cell.
            for start in range(0, len(neighbors), 4096):
                candidates = neighbors[start:start + 4096]
                candidates = candidates[candidates > i]
                if not len(candidates):
                    continue
                delta = points[candidates] - points[i]
                hits = candidates[np.einsum("ij,ij->i", delta, delta) <= threshold * threshold]
                if len(hits):
                    connected = roots(np.concatenate(([i], hits)))
                    parent[connected] = connected.min()
    labels = roots(np.arange(n))
    groups = {}
    for i, label in enumerate(labels):
        groups.setdefault(int(label), []).append(i)
    return list(groups.values())
