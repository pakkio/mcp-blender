"""Segmentation topology, transform, and NumPy clustering regressions."""
import math
from unittest.mock import patch

import bpy
import numpy as np

from tests_live.base_case import LiveBpyTestCase
from extension.tools.spatial_clustering import cluster_centers


class TestSegmentation(LiveBpyTestCase):
    def test_numpy_matches_reference_components(self):
        rng = np.random.default_rng(27)
        for points in (rng.normal(size=(160, 3)), np.zeros((30, 3)),
                       np.array([[i, 0, 0] for i in range(12)]), np.empty((0, 3))):
            for ratio in (0.08, 0.18, 0.32):
                threshold = max(float(np.linalg.norm(np.ptp(points, axis=0))) * ratio, 1e-6) if len(points) else 1e-6
                unseen = set(range(len(points)))
                expected = []
                while unseen:
                    pending = [unseen.pop()]
                    component = set(pending)
                    while pending:
                        i = pending.pop()
                        neighbors = {j for j in unseen if math.dist(points[i], points[j]) <= threshold}
                        unseen -= neighbors
                        component |= neighbors
                        pending.extend(neighbors)
                    expected.append(frozenset(component))
                self.assertEqual(set(expected), {frozenset(c) for c in cluster_centers(points, ratio)})

    def _source(self):
        bpy.ops.mesh.primitive_cube_add()
        first = bpy.context.object
        bpy.ops.mesh.primitive_cube_add(location=(2.01, 0, 0))
        second = bpy.context.object
        first.select_set(True)
        bpy.context.view_layer.objects.active = first
        bpy.ops.object.join()
        return first

    def _separate(self):
        with patch('extension.tools.localization_ops._call_llm_classify', return_value=None):
            result = self.execute_tool('separate_logical_areas', {'lang': 'en'})
        self.assertTrue(result['success'], result)
        bpy.context.view_layer.update()
        return [bpy.data.objects[name] for group in result['groups'] for name in group['parts']]

    def test_large_object_scale_does_not_weld_distinct_parts(self):
        source = self._source()
        source.scale = (1000, 1000, 1000)
        bpy.context.view_layer.update()
        pieces = self._separate()
        self.assertEqual(len(pieces), 2)
        self.assertEqual(sum(len(p.data.vertices) for p in pieces), 16)

    def test_parented_source_preserves_world_geometry(self):
        source = self._source()
        parent = bpy.data.objects.new('TransformedParent', None)
        bpy.context.scene.collection.objects.link(parent)
        parent.location = (12, -7, 4)
        parent.rotation_euler = (0.1, 0.2, 0.6)
        parent.scale = (2, 3, 1)
        source.parent = parent
        bpy.context.view_layer.update()
        def points(objects):
            return sorted(tuple(round(v, 4) for v in obj.matrix_world @ vertex.co)
                          for obj in objects for vertex in obj.data.vertices)
        before = points([source])
        pieces = self._separate()
        self.assertEqual(points(pieces), before)
        self.assertTrue(source.hide_viewport)
