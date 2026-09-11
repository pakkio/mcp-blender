# Sketchfab vehicle segmentation fixture

**Pony Cartoon**, by **Slava Z.** (https://sketchfab.com/slava).
Source: https://sketchfab.com/models/885d9f60b3a9429bb4077cfac5653cf9
License: [Creative Commons Attribution 4.0](https://creativecommons.org/licenses/by/4.0/).
Downloaded from https://github.com/jgbarah/aframe-playground/tree/master/assets/3d/auto
on 2026-09-11.

Changes: texture references removed from `scene.gltf`, plain material colors
substituted, texture images omitted. Geometry buffer is unchanged. The test
removes the ground plane and combines body, interior and glass into one mesh.

Original glTF SHA-256: `cb2aca62e75bb02505e599f9140b0c41a92351f72b9ad49d85248675b4ad9a7f`
Unmodified `scene.bin` SHA-256: `3d8cf3e149a43a61c3f04859970d2189babfa2ac5e28a1cae22e9d4c5de49fc8`

## Independent wheel reference

In mesh 0's first primitive, triangle ranges `[0,320)`, `[320,640)`,
`[640,960)` and `[960,1280)` are the four wheels. Each contains three
disconnected surface components in the raw glTF, together forming one wheel.
These ranges were inspected separately from the production segmentation code.
The wheels occupy the four lower corners of the car; each spans approximately
117 world units along Y and 115 along Z in the original import.

The test attaches these labels as a FACE attribute before joining, without
passing them to the classifier. It requires exactly one pure output object per
wheel, 320 triangles per wheel, preservation of all 8,336 car faces, and stable
wheel world-space bounds (absolute tolerance 0.001). It runs both the original
and a translated, rotated, nonuniformly scaled parented car.

The test exercises real splitting and NumPy heuristic classification. The
network LLM call is disabled; this does not test semantic wheel naming or claim
that the heuristic hierarchy always groups every vehicle correctly.

Run:

```powershell
blender --background --factory-startup --python-exit-code 1 --python scripts/run_live_bpy_tests.py -- --pattern test_live_sketchfab_wheels.py
blender --background --factory-startup --python-exit-code 1 --python scripts/inspect_segmentation_fixture.py
```

The second command writes intact/exploded previews, a `.blend` scene, and a
JSON report to `exports/segmentation_test/`. Wheel displacement in that scene
is only for inspection, applied after the regression assertions pass.
