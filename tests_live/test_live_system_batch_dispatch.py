"""Live tests for Python escape hatch, batch execution, system ops, and dispatch queue inside Blender."""

import bpy
from extension.bridge import dispatch
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
