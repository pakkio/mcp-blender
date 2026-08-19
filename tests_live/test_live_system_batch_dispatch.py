"""Live tests for Python escape hatch, batch execution, system ops, and dispatch queue inside Blender."""

import bpy
from extension.bridge import dispatch
from extension.tools import TOOL_REGISTRY
from extension.tools.base import ToolBase
from tests_live.base_case import LiveBpyTestCase


class TestLiveSystemBatchDispatch(LiveBpyTestCase):

    def test_execute_blender_python(self):
        code = "import bpy\nresult = len(bpy.data.scenes)"
        res = self.execute_tool("execute_blender_python", {"code": code})
        self.assertTrue(res.get("success"), res.get("message"))
        self.assertEqual(res.get("result"), "1")

    def test_execute_batch(self):
        batch_params = {
            "title": "Test Batch Creation",
            "update_hud": False,
            "commands": [
                {
                    "tool": "create_object",
                    "params": {"object_type": "CUBE", "name": "BatchCube1", "location": [0, 0, 0]},
                },
                {
                    "tool": "create_object",
                    "params": {"object_type": "CUBE", "name": "BatchCube2", "location": [2, 0, 0]},
                },
                {
                    "tool": "create_material",
                    "params": {"name": "BatchMat", "base_color": [1, 0, 0, 1]},
                },
                {
                    "tool": "assign_material",
                    "params": {"object_name": "BatchCube1", "material_name": "BatchMat"},
                },
            ],
        }
        res = self.execute_tool("execute_batch", batch_params)
        self.assertTrue(res.get("success"), res.get("message"))
        self.assertEqual(res.get("total_executed"), 4)
        self.assertIn("BatchCube1", bpy.data.objects)
        self.assertIn("BatchCube2", bpy.data.objects)
        self.assertIn("BatchMat", bpy.data.materials)

    def test_get_system_info(self):
        res = self.execute_tool("get_system_info", {})
        self.assertTrue(res.get("success"), res.get("message"))
        self.assertIn("blender_version", res)

    def test_bridge_dispatch_queue(self):
        # Test that dispatch.enqueue and dispatch.drain_queue work on Blender main thread
        fut = dispatch.enqueue("live-req-1", "create_object", {"object_type": "CUBE", "name": "DispatchCube"})
        self.assertFalse(fut.done())

        # Drain queue (simulating timer tick)
        dispatch.drain_queue()
        self.assertTrue(fut.done())

        response = fut.result()
        self.assertIn("result", response)
        self.assertTrue(response["result"]["success"])
        self.assertIn("DispatchCube", bpy.data.objects)

    def test_bridge_status_reflects_busy_state_around_execution(self):
        # Idle before anything is queued.
        self.assertFalse(dispatch.get_status()["busy"])

        seen_status_while_running = {}

        class _ProbeTool(ToolBase):
            name = "test_probe_busy_tool"
            description = "Live-test-only probe that reads dispatch status from inside its own execute()."

            def execute(self, params: dict) -> dict:
                seen_status_while_running.update(dispatch.get_status())
                return {"success": True}

        probe = _ProbeTool()
        TOOL_REGISTRY[probe.name] = probe
        try:
            fut = dispatch.enqueue("live-req-busy", probe.name, {"target": "SomeMesh"})
            dispatch.drain_queue()
        finally:
            del TOOL_REGISTRY[probe.name]

        self.assertTrue(fut.done())
        self.assertTrue(fut.result()["result"]["success"])

        # While the probe tool was executing, get_status() must have reported
        # busy=True with this exact method name, its params, an elapsed time,
        # and a human-readable description combining all three -- this is
        # what lets a client show "how many secs, doing exactly what" instead
        # of just a bare busy=True/False flag.
        current = seen_status_while_running["current"]
        self.assertTrue(seen_status_while_running["busy"])
        self.assertEqual(current["method"], probe.name)
        self.assertIn("SomeMesh", current["params_preview"])
        self.assertGreaterEqual(current["running_for_s"], 0)
        self.assertIn(probe.name, current["description"])
        self.assertIn("SomeMesh", current["description"])
        self.assertIn("running for", current["description"])

        # And idle again immediately after drain_queue() returns.
        self.assertFalse(dispatch.get_status()["busy"])

    def test_bridge_status_truncates_huge_params(self):
        seen = {}

        class _ProbeTool(ToolBase):
            name = "test_probe_huge_params_tool"
            description = "Live-test-only probe for the params_preview truncation guard."

            def execute(self, params: dict) -> dict:
                seen.update(dispatch.get_status())
                return {"success": True}

        probe = _ProbeTool()
        TOOL_REGISTRY[probe.name] = probe
        try:
            huge_code = "x = 1\n" * 5000  # e.g. execute_blender_python's "code" param
            fut = dispatch.enqueue("live-req-huge", probe.name, {"code": huge_code})
            dispatch.drain_queue()
        finally:
            del TOOL_REGISTRY[probe.name]

        self.assertTrue(fut.done())
        preview = seen["current"]["params_preview"]
        self.assertLess(len(preview), len(huge_code))
        self.assertIn("truncated", preview)

    def test_client_status_overlay_reports_busy_independent_of_dispatch_queue(self):
        # Idle: no bpy call in flight, no client_status pushed.
        status = dispatch.get_status()
        self.assertFalse(status["busy"])
        self.assertIsNone(status["client_status"])

        # mcp_server pushes a status describing work it's doing that never
        # touches bpy at all (e.g. downloading an asset over HTTP) -- this
        # must read back as busy even though the dispatch queue is empty and
        # nothing is running on the main thread.
        dispatch.set_client_status("Downloading 'chair1' from polyhaven...")
        status = dispatch.get_status()
        self.assertTrue(status["busy"])
        self.assertIsNone(status["current"])
        self.assertEqual(status["client_status"]["text"], "Downloading 'chair1' from polyhaven...")
        self.assertGreaterEqual(status["client_status"]["running_for_s"], 0)

        # Cleared the same way mcp_server clears it in its finally-block.
        dispatch.set_client_status(None)
        self.assertFalse(dispatch.get_status()["busy"])
        self.assertIsNone(dispatch.get_status()["client_status"])

    def test_client_status_and_dispatch_execution_can_both_be_reported(self):
        seen = {}

        class _ProbeTool(ToolBase):
            name = "test_probe_client_status_tool"
            description = "Live-test-only probe verifying current + client_status coexist."

            def execute(self, params: dict) -> dict:
                seen.update(dispatch.get_status())
                return {"success": True}

        dispatch.set_client_status("Simplifying 'Chair_Mesh' to 5200 vertices (asset 'chair1' from polyhaven)")
        probe = _ProbeTool()
        TOOL_REGISTRY[probe.name] = probe
        try:
            fut = dispatch.enqueue("live-req-both", probe.name, {})
            dispatch.drain_queue()
        finally:
            del TOOL_REGISTRY[probe.name]
            dispatch.set_client_status(None)

        self.assertTrue(fut.done())
        self.assertTrue(seen["busy"])
        self.assertEqual(seen["current"]["method"], probe.name)
        self.assertIn("5200", seen["client_status"]["text"])
