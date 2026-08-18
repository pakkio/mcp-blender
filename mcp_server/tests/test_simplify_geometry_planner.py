"""Unit tests for the bpy-free simplify_geometry planner.

Loaded by path, like test_axis_utils.py, so this pure-arithmetic half is
testable without bpy.
"""

import importlib.util
from pathlib import Path

_MODULE_PATH = Path(__file__).resolve().parents[2] / "extension" / "tools" / "simplify_geometry_planner.py"
_spec = importlib.util.spec_from_file_location("simplify_geometry_planner", _MODULE_PATH)
planner = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(planner)


def test_resolve_target_preset():
    assert planner.resolve_target_vertices(preset="hero") == (30_000, None)
    assert planner.resolve_target_vertices(preset="MAX") == (100_000, None)
    _, err = planner.resolve_target_vertices(preset="ULTRA")
    assert "Unknown preset" in err


def test_resolve_target_vertices_unit():
    assert planner.resolve_target_vertices(target=5000, target_unit="VERTICES") == (5000, None)


def test_resolve_target_triangles_unit_converts():
    # 20000 verts / 10000 tris = 2 verts/tri; target 2000 tris -> 4000 verts
    target, err = planner.resolve_target_vertices(
        target=2000, target_unit="TRIANGLES", current_verts=20000, current_tris=10000
    )
    assert err is None
    assert target == 4000


def test_resolve_target_triangles_without_counts_errors():
    _, err = planner.resolve_target_vertices(target=2000, target_unit="TRIANGLES", current_verts=0, current_tris=0)
    assert "Cannot convert" in err


def test_resolve_target_requires_target_or_preset():
    _, err = planner.resolve_target_vertices()
    assert "required" in err


def test_resolve_target_rejects_nonpositive():
    _, err = planner.resolve_target_vertices(target=0)
    assert "positive" in err


def test_distribute_vertex_budget_proportional():
    counts = {"Big": 9000, "Small": 1000}
    result = planner.distribute_vertex_budget(counts, 1000)
    assert result["Big"] == 900
    assert result["Small"] == 100
    assert sum(result.values()) == 1000


def test_distribute_vertex_budget_minimum_and_drift_correction():
    # A near-zero object still gets the 4-vertex floor; drift goes to the largest.
    counts = {"Big": 9990, "Tiny": 10}
    result = planner.distribute_vertex_budget(counts, 100)
    assert result["Tiny"] == 4
    assert sum(result.values()) == 100


def test_distribute_vertex_budget_empty_total():
    assert planner.distribute_vertex_budget({"A": 0}, 100) == {"A": 0}


def test_estimate_initial_ratio_clamped():
    assert planner.estimate_initial_ratio(1000, 1000, 500) == 0.5
    assert planner.estimate_initial_ratio(1000, 1000, 5000) == 1.0
    assert planner.estimate_initial_ratio(0, 0, 500) == 1.0


def test_secant_next_ratio_moves_toward_target():
    # r=0.5 -> 500 verts, r=0.6 -> 600 verts, target 550 -> should land near 0.55
    next_ratio = planner.secant_next_ratio(0.5, 500, 0.6, 600, 550)
    assert 0.5 < next_ratio < 0.6


def test_secant_next_ratio_handles_flat_samples():
    # Both ratios produced the same count -- must nudge, not divide by zero.
    next_ratio = planner.secant_next_ratio(0.1, 200, 0.2, 200, 500)
    assert next_ratio > 0.2


def test_within_tolerance():
    assert planner.within_tolerance(1040, 1000, tolerance=0.05)
    assert not planner.within_tolerance(1200, 1000, tolerance=0.05)
    assert not planner.within_tolerance(100, 0, tolerance=0.05)


def test_evaluate_quality_gate_pass():
    gate = planner.evaluate_quality_gate(deviation_max_pct=1.0, new_boundary_edges=0)
    assert gate["passed"] is True


def test_evaluate_quality_gate_fails_on_deviation():
    gate = planner.evaluate_quality_gate(deviation_max_pct=5.0, new_boundary_edges=0, max_deviation_pct=2.0)
    assert gate["passed"] is False
    assert "deviation" in gate["reason"]


def test_evaluate_quality_gate_fails_on_new_holes():
    gate = planner.evaluate_quality_gate(deviation_max_pct=0.5, new_boundary_edges=3, allow_new_holes=0)
    assert gate["passed"] is False
    assert "boundary edge" in gate["reason"]


def test_evaluate_quality_gate_reports_both_failures():
    gate = planner.evaluate_quality_gate(deviation_max_pct=10.0, new_boundary_edges=5, max_deviation_pct=2.0, allow_new_holes=0)
    assert gate["passed"] is False
    assert "deviation" in gate["reason"] and "boundary edge" in gate["reason"]


def test_suggest_retry_target_scales_with_overshoot():
    suggestion = planner.suggest_retry_target(10000, deviation_max_pct=4.0, max_deviation_pct=2.0)
    assert suggestion == 20000


def test_suggest_retry_target_caps_scale_factor():
    suggestion = planner.suggest_retry_target(10000, deviation_max_pct=100.0, max_deviation_pct=2.0)
    assert suggestion == 40000  # capped at 4x


def test_suggest_retry_target_default_bump_when_gate_passed():
    suggestion = planner.suggest_retry_target(10000, deviation_max_pct=1.0, max_deviation_pct=2.0)
    assert suggestion == 15000
