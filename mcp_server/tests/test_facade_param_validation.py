"""Regression tests for facade parameter hygiene.

The facades used to forward `params` verbatim, so a misnamed key was dropped in
silence and the call reported success while doing nothing -- create_material
with `color=` produced a default grey material, and create_lighting_rig with
`target=`/`distance=` built the rig at the world origin. These tests lock in
both the alias resolution and the loud rejection of genuinely unknown keys.
"""

import pytest

from mcp_blender_pakkio.errors import BridgeError, ErrorType
from mcp_blender_pakkio.tools.domain_facades import _normalise_params


def test_unspecced_method_passes_through_unchanged():
    params = {"anything": 1, "goes": "here"}
    assert _normalise_params("some_other_method", params) == params


class TestCreateMaterial:
    def test_color_alias_resolves_to_base_color(self):
        out = _normalise_params("create_material", {"name": "Red", "color": [0.8, 0, 0, 1]})
        assert out == {"name": "Red", "base_color": [0.8, 0, 0, 1]}

    def test_object_name_alias_resolves_to_assign_to_object(self):
        out = _normalise_params("create_material", {"name": "Red", "object_name": "Cube"})
        assert out == {"name": "Red", "assign_to_object": "Cube"}

    def test_canonical_names_are_left_alone(self):
        params = {"name": "Red", "base_color": [1, 0, 0, 1], "assign_to_object": "Cube"}
        assert _normalise_params("create_material", params) == params

    def test_unknown_key_raises_instead_of_being_dropped(self):
        with pytest.raises(BridgeError) as exc:
            _normalise_params("create_material", {"name": "Red", "colour": [1, 0, 0, 1]})
        assert exc.value.error_type == ErrorType.VALIDATION
        assert "colour" in str(exc.value)

    def test_error_lists_the_accepted_names(self):
        with pytest.raises(BridgeError) as exc:
            _normalise_params("create_material", {"nonsense": 1})
        assert "base_color" in str(exc.value)


class TestCreateLightingRig:
    def test_target_as_coordinates_becomes_target_location(self):
        out = _normalise_params("create_lighting_rig", {"target": [1, 1, 2]})
        assert out == {"target_location": [1, 1, 2]}

    def test_target_as_string_becomes_target_object(self):
        out = _normalise_params("create_lighting_rig", {"target": "Cube"})
        assert out == {"target_object": "Cube"}

    def test_distance_is_accepted(self):
        out = _normalise_params("create_lighting_rig", {"distance": 8})
        assert out == {"distance": 8}

    def test_radius_aliases_to_distance(self):
        assert _normalise_params("create_lighting_rig", {"radius": 8}) == {"distance": 8}

    def test_unknown_key_raises(self):
        with pytest.raises(BridgeError) as exc:
            _normalise_params("create_lighting_rig", {"intensity": 5})
        assert exc.value.error_type == ErrorType.VALIDATION


class TestAssignMaterial:
    def test_short_aliases_resolve(self):
        out = _normalise_params("assign_material", {"object": "Cube", "material": "Red"})
        assert out == {"object_name": "Cube", "material_name": "Red"}

    def test_unknown_key_raises(self):
        with pytest.raises(BridgeError):
            _normalise_params("assign_material", {"obj": "Cube"})
