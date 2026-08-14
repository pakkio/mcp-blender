"""Base test case for live in-Blender testing."""

import sys
import unittest
from pathlib import Path

import bpy

# Ensure extension root is on sys.path
EXTENSION_DIR = Path(__file__).resolve().parent.parent / "extension"
if str(EXTENSION_DIR.parent) not in sys.path:
    sys.path.insert(0, str(EXTENSION_DIR.parent))

from extension.tools import TOOL_REGISTRY


class LiveBpyTestCase(unittest.TestCase):
    """Base class for live Blender tests that resets scene state per test."""

    def setUp(self):
        # Reset to clean empty scene state before each test
        bpy.ops.wm.read_factory_settings(use_empty=True)
        # Ensure default collection exists
        if not bpy.data.collections:
            col = bpy.data.collections.new("Collection")
            bpy.context.scene.collection.children.link(col)

    def get_tool(self, name: str):
        tool = TOOL_REGISTRY.get(name)
        self.assertIsNotNone(tool, f"Tool '{name}' not found in TOOL_REGISTRY")
        return tool

    def execute_tool(self, name: str, params: dict = None) -> dict:
        tool = self.get_tool(name)
        result = tool.execute(params or {})
        return result
