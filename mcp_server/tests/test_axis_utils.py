"""Unit tests for the Blender-side axis helpers.

extension/tools/axis_utils.py is loaded by path so the test does not drag in
extension/tools/__init__.py, which imports bpy. Everything exercised here is
pure Python; the bpy/mathutils-dependent paths (conversion_matrix, apply_fix)
are covered by the live tests.
"""

import importlib.util
from pathlib import Path
from types import SimpleNamespace

import pytest

_MODULE_PATH = Path(__file__).resolve().parents[2] / "extension" / "tools" / "axis_utils.py"
_spec = importlib.util.spec_from_file_location("axis_utils", _MODULE_PATH)
axis_utils = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(axis_utils)


@pytest.mark.parametrize(
    "value,expected",
    [("y", "Y"), ("-z", "-Z"), ("NEGATIVE_Z", "-Z"), ("+X", "X"), ("W", None), (None, None)],
)
def test_normalize_axis(value, expected):
    assert axis_utils.normalize_axis(value) == expected


def test_resolve_axes_completes_partner_and_rejects_nonsense():
    assert axis_utils.resolve_axes(None, "Y") == ("-Z", "Y", None)
    assert axis_utils.resolve_axes("-Z", None) == ("-Z", "Y", None)
    assert axis_utils.resolve_axes(None, None) == (None, None, None)

    _, _, err = axis_utils.resolve_axes("Y", "-Y")
    assert "different axes" in err
    _, _, err = axis_utils.resolve_axes("W", None)
    assert "Invalid forward_axis" in err


def test_is_format_default_matches_importer_behavior():
    # STL does no conversion; OBJ/FBX already assume the Y-up convention.
    assert axis_utils.is_format_default("STL", "Y", "Z")
    assert not axis_utils.is_format_default("STL", "-Z", "Y")
    assert axis_utils.is_format_default("OBJ", "-Z", "Y")
    assert not axis_utils.is_format_default("GLB", "-Z", "Y")


def test_has_native_axis_args():
    assert axis_utils.has_native_axis_args("FBX")
    assert not axis_utils.has_native_axis_args("GLB")
    assert not axis_utils.has_native_axis_args("USD")


def _mesh(points):
    """Fake mesh object: identity matrix_world, vertices at `points`."""
    identity = SimpleNamespace(__matmul__=None)

    class Identity:
        def __matmul__(self, other):
            return other

    return SimpleNamespace(
        type="MESH",
        parent=None,
        matrix_world=Identity(),
        data=SimpleNamespace(vertices=[SimpleNamespace(co=SimpleNamespace(x=x, y=y, z=z)) for x, y, z in points]),
    )


def _cone(inverted=False):
    """Wide base tapering to a point (or the reverse when inverted)."""
    points = []
    for level in range(10):
        z = level / 9.0
        radius = 1.0 - z
        for step in range(12):
            angle = step / 12.0 * 6.28318
            import math

            points.append((radius * math.cos(angle), radius * math.sin(angle), z))
    if inverted:
        points = [(x, y, 1.0 - z) for x, y, z in points]
    return _mesh(points)


def test_upright_cone_reads_ok():
    report = axis_utils.analyze_orientation([_cone()])
    assert report["verdict"] == "ok"


def test_inverted_cone_is_flagged_upside_down():
    report = axis_utils.analyze_orientation([_cone(inverted=True)])
    assert report["verdict"] == "suspect_upside_down"
    assert (report["fix_axis"], report["fix_degrees"]) == ("X", 180)


def test_upright_table_is_not_flagged():
    """Top-heavy and wider at the top, but its legs give it a full-width base."""
    points = []
    for leg_x, leg_y in ((0.05, 0.05), (0.95, 0.05), (0.05, 0.95), (0.95, 0.95)):
        for level in range(18):
            points.append((leg_x, leg_y, level / 20.0))
    for x in range(11):
        for y in range(11):
            for z in (0.9, 1.0):
                points.append((x / 10.0, y / 10.0, z))
    report = axis_utils.analyze_orientation([_mesh(points)])
    assert report["verdict"] == "ok", report


def test_flat_elongated_mesh_is_flagged_lying_down():
    points = [(x, y, z * 0.02) for x in range(10) for y in range(3) for z in range(2)]
    report = axis_utils.analyze_orientation([_mesh(points)])
    assert report["verdict"] == "suspect_lying_down"
    assert (report["fix_axis"], report["fix_degrees"]) == ("X", 90)


def test_flat_square_mesh_is_left_alone():
    """A rug/plate/ground plane is flat on purpose."""
    points = [(x, y, z * 0.02) for x in range(6) for y in range(6) for z in range(2)]
    assert axis_utils.analyze_orientation([_mesh(points)])["verdict"] == "ok"


def test_no_geometry_is_unknown():
    assert axis_utils.analyze_orientation([])["verdict"] == "unknown"
