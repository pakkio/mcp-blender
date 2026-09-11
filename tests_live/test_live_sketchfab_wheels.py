"""Real Sketchfab geometry: recover wheels from a joined, anonymously named car."""
from collections import Counter
from pathlib import Path
import time
from unittest.mock import patch

import bpy
import numpy as np

from tests_live.base_case import LiveBpyTestCase

FIXTURE = Path(__file__).parent / 'fixtures/sketchfab_pony/scene.gltf'


class TestSketchfabWheels(LiveBpyTestCase):
    def test_four_wheels_recovered_without_body_contamination(self):
        self._check_vehicle(False)

    def test_four_wheels_with_rotation_translation_and_nonuniform_scale(self):
        self._check_vehicle(True)

    def _check_vehicle(self, transformed):
        bpy.ops.import_scene.gltf(filepath=str(FIXTURE))
        meshes = [o for o in bpy.context.scene.objects if o.type == 'MESH']
        body = next(o for o in meshes if len(o.data.polygons) == 5938)
        ground = next(o for o in meshes if len(o.data.polygons) == 2)
        bpy.data.objects.remove(ground, do_unlink=True)
        meshes.remove(ground)
        # Reviewed source triangle ranges, independent of the code under test.
        # 0 = body/interior/glass; 1..4 = the four wheels (320 faces each).
        for obj in meshes:
            attr = obj.data.attributes.new('reference_wheel', 'INT', 'FACE')
            labels = np.zeros(len(obj.data.polygons), dtype=np.int32)
            if obj == body:
                labels[:1280] = np.repeat(np.arange(1, 5), 320)
            attr.data.foreach_set('value', labels)
        bpy.ops.object.select_all(action='DESELECT')
        for obj in meshes:
            obj.select_set(True)
        bpy.context.view_layer.objects.active = body
        bpy.ops.object.join()
        source = bpy.context.object
        source.name = 'AnonymousVehicle'
        expected_faces = len(source.data.polygons)
        self.assertEqual(expected_faces, 8336)
        source_labels = np.array([v.value for v in source.data.attributes['reference_wheel'].data])
        before = Counter(source_labels)
        if transformed:
            parent = bpy.data.objects.new('VehicleTransform', None)
            bpy.context.scene.collection.objects.link(parent)
            parent.location = (35, -120, 20)
            parent.rotation_euler = (0.2, -0.3, 0.65)
            parent.scale = (0.01, 0.02, 0.015)
            source.parent = parent
            bpy.context.view_layer.update()
        expected_bounds = {}
        for label in range(1, 5):
            vertices = {i for p in source.data.polygons if source_labels[p.index] == label for i in p.vertices}
            coords = np.array([source.matrix_world @ source.data.vertices[i].co for i in vertices])
            self.assertEqual(before[label], 320)
            if not transformed:
                self.assertGreater(np.ptp(coords, axis=0)[1], 100)
                self.assertLess(np.ptp(coords, axis=0)[0], 80)
            expected_bounds[label] = (coords.min(axis=0), coords.max(axis=0))
        start = time.perf_counter()
        # Exercise actual geometry splitting + NumPy fallback; no network or
        # mocked segmentation/classification result containing the answer.
        with patch('extension.tools.localization_ops._call_llm_classify', return_value=None):
            result = self.execute_tool('separate_logical_areas', {'lang': 'en'})
        elapsed = time.perf_counter() - start
        self.assertTrue(result['success'], result)
        bpy.context.view_layer.update()
        pieces = [bpy.data.objects[n] for g in result['groups'] for n in g['parts']]
        self.assertGreater(len(pieces), 4)
        actual = Counter()
        wheel_pieces = {label: [] for label in range(1, 5)}
        for piece in pieces:
            attr = piece.data.attributes.get('reference_wheel')
            self.assertIsNotNone(attr)
            labels = [v.value for v in attr.data]
            actual.update(labels)
            wheel_labels = set(labels) - {0}
            if wheel_labels:
                self.assertEqual(len(set(labels)), 1, f'Wheel/body or wheel/wheel mixing: {piece.name}')
                label = next(iter(wheel_labels))
                wheel_pieces[label].append(piece)
        self.assertEqual(actual, before, 'Segmentation lost or duplicated faces')
        for label, objects in wheel_pieces.items():
            self.assertEqual(len(objects), 1, f'Wheel {label} must be one complete object')
            coords = np.array([o.matrix_world @ v.co for o in objects for v in o.data.vertices])
            np.testing.assert_allclose(coords.min(axis=0), expected_bounds[label][0], atol=1e-3, rtol=0)
            np.testing.assert_allclose(coords.max(axis=0), expected_bounds[label][1], atol=1e-3, rtol=0)
        self.assertTrue(source.hide_viewport)
        self.segmentation_report = {'source_faces': expected_faces, 'output_pieces': len(pieces),
                                    'wheels_recovered': 4, 'seconds': elapsed,
                                    'transformed': transformed, 'wheel_faces': [actual[i] for i in range(1, 5)],
                                    'body_contamination': False}
        print(f'SKETCHFAB WHEEL TEST: {expected_faces} faces, {len(pieces)} pieces, '
              f'4/4 wheels, no body contamination, {elapsed:.3f}s; '
              f'wheel piece counts={[len(v) for v in wheel_pieces.values()]}')
