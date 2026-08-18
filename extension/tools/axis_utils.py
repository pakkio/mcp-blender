"""Axis-convention helpers for file import/export.

Blender is Z-up / -Y-forward. Most other DCCs and interchange formats are not,
which is why an imported model's "up" often ends up horizontal:

  * glTF/GLB  - Y-up, +Z forward. Blender's importer converts automatically.
  * USD       - up axis is declared in the file; Blender's importer honours it.
  * FBX       - importer defaults to -Z forward / Y up (the Maya/Max convention).
  * OBJ       - importer defaults to -Z forward / Y up.
  * STL       - the format carries NO axis metadata, so Blender's importer does
                no conversion at all (Y forward / Z up). Any STL authored in a
                Y-up application therefore lands lying on its back.

So a caller needs a way to say "this file is Y-up" for the formats where the
convention cannot be inferred, and to override the default guess for the rest.
`forward_axis` / `up_axis` always describe the *source file's* convention.
"""

AXES = ("X", "Y", "Z", "-X", "-Y", "-Z")

# Blender's default source convention per format, i.e. what the importer already
# assumes when no axes are given. Formats that self-describe map to None.
_FORMAT_DEFAULT_AXES = {
    "FBX": ("-Z", "Y"),
    "OBJ": ("-Z", "Y"),
    "STL": ("Y", "Z"),
}

# Formats whose importer has no axis arguments; conversion is applied to the
# imported objects' transforms instead.
_NO_NATIVE_AXIS_ARGS = ("GLTF", "GLB", "USD", "BLEND")

_ENUM_NAMES = {
    "X": "X",
    "Y": "Y",
    "Z": "Z",
    "-X": "NEGATIVE_X",
    "-Y": "NEGATIVE_Y",
    "-Z": "NEGATIVE_Z",
}

# The forward axis conventionally paired with each up axis, so callers can pass
# just `up_axis="Y"` (by far the common case) and get a sane result.
_PARTNER_FORWARD = {"X": "-Z", "Y": "-Z", "Z": "Y", "-X": "-Z", "-Y": "-Z", "-Z": "Y"}
_PARTNER_UP = {"X": "Z", "Y": "Z", "Z": "Y", "-X": "Z", "-Y": "Z", "-Z": "Y"}


def normalize_axis(value):
    """Accept 'y', '-Z', 'NEGATIVE_Z' ... -> '-Z'. Returns None if unrecognized."""
    if value is None:
        return None
    text = str(value).strip().upper().replace(" ", "_")
    if text.startswith("NEGATIVE_"):
        text = "-" + text[len("NEGATIVE_"):]
    if text.startswith("+"):
        text = text[1:]
    return text if text in AXES else None


def resolve_axes(forward, up):
    """Normalize a (forward, up) request.

    Returns (forward, up, error). Both are None when nothing was requested.
    A single supplied axis is completed with its conventional partner.
    """
    raw_forward, raw_up = forward, up
    forward = normalize_axis(forward)
    up = normalize_axis(up)

    if raw_forward is not None and forward is None:
        return None, None, f"Invalid forward_axis '{raw_forward}'; expected one of {list(AXES)}"
    if raw_up is not None and up is None:
        return None, None, f"Invalid up_axis '{raw_up}'; expected one of {list(AXES)}"

    if forward is None and up is None:
        return None, None, None
    if forward is None:
        forward = _PARTNER_FORWARD[up]
    if up is None:
        up = _PARTNER_UP[forward]

    if forward.lstrip("-") == up.lstrip("-"):
        return None, None, f"forward_axis '{forward}' and up_axis '{up}' must use different axes"
    return forward, up, None


def is_format_default(file_format, forward, up):
    """True when the request matches what the importer would do anyway."""
    return _FORMAT_DEFAULT_AXES.get((file_format or "").upper()) == (forward, up)


def has_native_axis_args(file_format):
    return (file_format or "").upper() not in _NO_NATIVE_AXIS_ARGS


def native_axis_kwargs(operator, forward, up):
    """Axis kwargs for a Blender import/export operator.

    The modern C++ OBJ/STL operators use forward_axis/up_axis with
    'NEGATIVE_Z'-style enums; the legacy Python ones (and FBX) use
    axis_forward/axis_up with '-Z'-style enums.
    """
    try:
        modern = "forward_axis" in operator.get_rna_type().properties
    except Exception:
        modern = False

    if modern:
        return {"forward_axis": _ENUM_NAMES[forward], "up_axis": _ENUM_NAMES[up]}
    return {"axis_forward": forward, "axis_up": up}


def conversion_matrix(forward, up):
    """4x4 matrix taking (forward, up) source space into Blender space.

    Target is Y forward / Z up, the same identity Blender's own importers use
    via bpy_extras.io_utils.axis_conversion.
    """
    from bpy_extras.io_utils import axis_conversion

    return axis_conversion(from_forward=forward, from_up=up, to_forward="Y", to_up="Z").to_4x4()


def apply_conversion(objects, forward, up):
    """Rotate root objects of an imported set into Blender space.

    Only roots are touched: children inherit through their parents, so rotating
    them too would double-apply the conversion.
    """
    return _rotate_roots(objects, conversion_matrix(forward, up))


def _rotate_roots(objects, matrix):
    """Left-multiply a world matrix onto the root objects of a set.

    Only roots are touched: children inherit through their parents, so rotating
    them too would double-apply the transform.
    """
    members = set(objects)
    roots = [obj for obj in objects if obj.parent is None or obj.parent not in members]
    for obj in roots:
        obj.matrix_world = matrix @ obj.matrix_world
    return len(roots)


# --- orientation sanity check -------------------------------------------------
#
# Even with the right axis conversion, files arrive mis-authored: a model saved
# upside down, or with -Y as its up axis, imports flipped. There is no metadata
# to consult, so the check is geometric: does this thing look like it could
# stand up? Three signals, deliberately requiring all of them to agree, since a
# single one produces obvious false positives (a table is top-heavy and wider at
# the top, yet perfectly upright — its legs still give it a full-width base):
#
#   * volume distribution - cross-section-weighted centroid sits high
#   * top-heavy footprint - the top slab is much wider than the bottom slab
#   * no base             - the bottom slab is narrow against the widest slice,
#                           i.e. the model balances on a point
#
# The verdict is only ever "suspect": auto_orient acts on it, a bare import just
# reports it.

_SAMPLE_LIMIT = 20000
_SLAB = 0.15  # bottom/top slab thickness, as a fraction of total height


def _world_points(objects, limit=_SAMPLE_LIMIT):
    points = []
    meshes = [obj for obj in objects if getattr(obj, "type", None) == "MESH" and obj.data]
    total = sum(len(obj.data.vertices) for obj in meshes)
    stride = max(1, (total // limit) + 1) if total else 1
    for obj in meshes:
        matrix = obj.matrix_world
        vertices = obj.data.vertices
        for index in range(0, len(vertices), stride):
            points.append(matrix @ vertices[index].co)
    return points


def analyze_orientation(objects):
    """Report whether the imported geometry looks correctly oriented.

    Returns a dict with the measured signals, a verdict of 'ok', 'unknown',
    'suspect_upside_down' or 'suspect_lying_down', and the corrective rotation
    (axis + degrees) that would fix a suspect result.
    """
    points = _world_points(objects)
    if len(points) < 8:
        return {"verdict": "unknown", "reason": "no mesh geometry to measure"}

    min_x = min(p.x for p in points)
    max_x = max(p.x for p in points)
    min_y = min(p.y for p in points)
    max_y = max(p.y for p in points)
    min_z = min(p.z for p in points)
    max_z = max(p.z for p in points)
    dims = (max_x - min_x, max_y - min_y, max_z - min_z)
    height = dims[2]

    report = {
        "dimensions": [round(value, 4) for value in dims],
        "sampled_vertices": len(points),
    }

    if height <= 1e-6:
        # Zero height is as likely to be a ground plane or a decal as a model
        # on its side, and nothing in the geometry distinguishes them.
        report.update(verdict="unknown", reason="geometry is flat on the Z axis; nothing to measure")
        return report

    # Volume distribution: slice the bounds along Z and weight each slice by its
    # cross-section (squared horizontal spread, an area proxy). Counting raw
    # vertices instead would just measure tessellation density, which says
    # nothing about which end is the base.
    mass, spread_max = _volume_profile(points, min_z, height)
    # Footprint: how wide the geometry is in the bottom slab vs the top slab.
    spread_low = _spread([p for p in points if p.z <= min_z + _SLAB * height])
    spread_high = _spread([p for p in points if p.z >= max_z - _SLAB * height])

    report["mass_center_ratio"] = round(mass, 3)
    report["base_width"] = round(spread_low, 4)
    report["top_width"] = round(spread_high, 4)
    report["widest_width"] = round(spread_max, 4)

    top_heavy = mass > 0.58
    top_wider = spread_high > spread_low * 1.5
    no_base = spread_max > 0 and spread_low < 0.35 * spread_max

    if top_heavy and top_wider and no_base:
        report.update(
            verdict="suspect_upside_down",
            reason=(
                f"volume sits high (centroid at {mass:.0%} of height) and the model narrows to a "
                "point at the bottom, so it has nothing to stand on"
            ),
            fix_axis="X",
            fix_degrees=180,
        )
    elif (
        height < max(dims[0], dims[1]) * 0.2
        and max(dims[0], dims[1]) > min(dims[0], dims[1]) * 1.6
        and mass > 0.45
    ):
        # Flat AND elongated: the silhouette of something toppled over. A flat
        # but square/round mesh (rug, plate, ground plane) is left alone.
        report.update(
            verdict="suspect_lying_down",
            reason="geometry is flat and elongated, like a model rotated onto its side",
            fix_axis="X",
            fix_degrees=90,
        )
    else:
        report["verdict"] = "ok"
    return report


_SLICES = 12


def _volume_profile(points, min_z, height):
    """(centroid height 0..1, widest slice spread) from horizontal slices."""
    buckets = [[] for _ in range(_SLICES)]
    for point in points:
        index = int((point.z - min_z) / height * _SLICES)
        buckets[min(index, _SLICES - 1)].append(point)

    weighted = 0.0
    total = 0.0
    widest = 0.0
    for index, bucket in enumerate(buckets):
        if not bucket:
            continue
        spread = _spread(bucket)
        widest = max(widest, spread)
        weight = spread ** 2
        weighted += weight * ((index + 0.5) / _SLICES)
        total += weight
    if total <= 0:
        return (sum(p.z for p in points) / len(points) - min_z) / height, widest
    return weighted / total, widest


def _spread(points):
    """Horizontal extent (diagonal of the XY bounds) of a slab of points."""
    if not points:
        return 0.0
    width = max(p.x for p in points) - min(p.x for p in points)
    depth = max(p.y for p in points) - min(p.y for p in points)
    return (width * width + depth * depth) ** 0.5


def apply_fix(objects, axis, degrees):
    """Rotate roots by `degrees` about a world axis, pivoting on their bounds."""
    import math

    from mathutils import Matrix, Vector

    points = _world_points(objects)
    if not points:
        return 0
    center = Vector((
        (min(p.x for p in points) + max(p.x for p in points)) / 2,
        (min(p.y for p in points) + max(p.y for p in points)) / 2,
        (min(p.z for p in points) + max(p.z for p in points)) / 2,
    ))
    rotation = Matrix.Rotation(math.radians(degrees), 4, axis)
    pivoted = Matrix.Translation(center) @ rotation @ Matrix.Translation(-center)
    return _rotate_roots(objects, pivoted)
