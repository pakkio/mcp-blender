"""Run the real-car regression and export intact/exploded visual evidence."""
import json
from pathlib import Path
import sys

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from tests_live.test_live_sketchfab_wheels import TestSketchfabWheels

case = TestSketchfabWheels('test_four_wheels_recovered_without_body_contamination')
case.setUp()
case.test_four_wheels_recovered_without_body_contamination()
objects = [o for o in bpy.context.scene.objects if o.type == 'MESH' and not o.hide_viewport]
colors = [(0.48, 0.5, 0.55, 1), (0.95, 0.18, 0.08, 1), (0.12, 0.5, 0.95, 1),
          (0.1, 0.8, 0.35, 1), (0.95, 0.65, 0.05, 1)]
wheels = []
for obj in objects:
    label = max(v.value for v in obj.data.attributes['reference_wheel'].data)
    obj.color = colors[label]
    if label:
        obj.name = f'Wheel_{label}'
        wheels.append(obj)
all_coords = [o.matrix_world @ v.co for o in objects for v in o.data.vertices]
lo = Vector(tuple(min(v[k] for v in all_coords) for k in range(3)))
hi = Vector(tuple(max(v[k] for v in all_coords) for k in range(3)))
center = (lo + hi) / 2
bpy.ops.object.camera_add(location=center + Vector((1, -1.5, 1)) * (hi-lo).length)
camera = bpy.context.object
camera.rotation_euler = (center-camera.location).to_track_quat('-Z','Y').to_euler()
camera.data.type = 'ORTHO'
camera.data.clip_end = 100000
camera.data.ortho_scale = (hi-lo).length * 1.1
scene = bpy.context.scene
scene.camera = camera
scene.render.engine = 'BLENDER_WORKBENCH'
scene.display.shading.color_type = 'OBJECT'
scene.display.shading.light = 'STUDIO'
scene.display.shading.show_shadows = True
scene.display.shading.show_cavity = True
scene.display.shading.background_type = 'WORLD'
if scene.world is None:
    scene.world = bpy.data.worlds.new('PreviewWorld')
scene.world.color = (0.04, 0.04, 0.04)
scene.render.resolution_x = 1200
scene.render.resolution_y = 900
scene.render.resolution_percentage = 100
out = ROOT / 'exports/segmentation_test'
out.mkdir(parents=True, exist_ok=True)
(out/'report.json').write_text(json.dumps(case.segmentation_report, indent=2)+'\n')
scene.render.filepath = str(out/'wheels_intact.png')
bpy.ops.render.render(write_still=True)
for obj in wheels:
    xs = [(obj.matrix_world @ v.co).x for v in obj.data.vertices]
    world = obj.matrix_world.copy()
    world.translation.x += 160 if sum(xs) > 0 else -160
    obj.matrix_world = world
scene.render.filepath = str(out/'wheels_exploded.png')
bpy.ops.render.render(write_still=True)
bpy.ops.wm.save_as_mainfile(filepath=str(out/'wheels_exploded.blend'))
