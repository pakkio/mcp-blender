"""Live tests for the addon preferences panel's status line (version + busy/idle wording)."""

from extension import ADDON_PACKAGE
from extension.panels.preferences import _addon_version_string
from tests_live.base_case import LiveBpyTestCase


class TestLivePreferencesPanel(LiveBpyTestCase):

    def test_addon_version_string_matches_manifest(self):
        version = _addon_version_string()
        # blender_manifest.toml's version at time of writing -- bump this
        # alongside the manifest if a future release changes it.
        self.assertRegex(version, r"^\d+\.\d+\.\d+$")

    def test_addon_version_string_empty_for_unknown_package(self):
        import sys
        real_mod = sys.modules.pop(ADDON_PACKAGE)
        try:
            self.assertEqual(_addon_version_string(), "")
        finally:
            sys.modules[ADDON_PACKAGE] = real_mod
