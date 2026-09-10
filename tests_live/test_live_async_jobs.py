"""Live tests for cooperative async jobs: submit, pump chunk-by-chunk with
other tools interleaved, poll progress, cancel, and single-shot fallback."""

import os
from unittest import mock

import bpy
from tests_live.base_case import LiveBpyTestCase

from extension.bridge import dispatch, scheduler
from extension.bridge.jobs import GLOBAL_JOB_MANAGER, JobStatus
from extension.tools import TOOL_REGISTRY

TERMINAL = (JobStatus.COMPLETED, JobStatus.CANCELLED, JobStatus.FAILED)


def _pump_until(job_id, max_ticks=200):
    """Drive the scheduler manually (headless has no timer loop) until the
    job reaches a terminal state. Returns (job, ticks)."""
    ticks = 0
    while ticks < max_ticks:
        scheduler.pump_jobs()
        ticks += 1
        job = GLOBAL_JOB_MANAGER.get_job(job_id)
        if job is not None and job.status in TERMINAL:
            return job, ticks
    raise AssertionError(f"job '{job_id}' not terminal after {max_ticks} pump ticks")


class TestLiveAsyncJobs(LiveBpyTestCase):
    def setUp(self):
        super().setUp()
        scheduler.reset()

    def tearDown(self):
        scheduler.reset()
        super().tearDown()

    def test_submit_unknown_method_fails_fast(self):
        res = scheduler.submit_job("no_such_tool", {})
        self.assertFalse(res["success"])
        self.assertIn("Unknown method", res["message"])

    def test_submit_single_shot_tool_completes_with_result(self):
        res = scheduler.submit_job("list_jobs", {"limit": 5})
        self.assertTrue(res["success"], res)
        self.assertFalse(res["chunked"])
        job_id = res["job_id"]

        job, ticks = _pump_until(job_id)
        self.assertEqual(job.status, JobStatus.COMPLETED)
        self.assertGreaterEqual(ticks, 1)
        self.assertIn("jobs", job.result)

    def test_regen_job_chunks_and_matches_sync_result(self):
        root = bpy.context.scene.collection
        col = bpy.data.collections.new("Furniture")
        root.children.link(col)
        obj = bpy.data.objects.new("Chair_Mesh", bpy.data.meshes.new("Chair_MeshData"))
        col.objects.link(obj)

        res = scheduler.submit_job("regen_element_names", {"lang": "it"})
        self.assertTrue(res["success"], res)
        self.assertTrue(res["chunked"])
        job_id = res["job_id"]

        # Between two chunks the main thread is free: another tool runs fine
        # (this is the "do other work meanwhile" the scheduler exists for),
        # and the job record already shows progress.
        scheduler.pump_jobs()
        mid = GLOBAL_JOB_MANAGER.get_job(job_id)
        self.assertEqual(mid.status, JobStatus.RUNNING)
        status_tool = TOOL_REGISTRY["get_job_status"]
        poll = status_tool.execute({"job_id": job_id})
        self.assertTrue(poll["success"])
        self.assertEqual(poll["job"]["id"], job_id)
        # bridge_status exposes the running job too (MCP-visible busy).
        self.assertEqual(dispatch.get_status()["job"]["job_id"], job_id)

        job, ticks = _pump_until(job_id)
        self.assertEqual(job.status, JobStatus.COMPLETED)
        self.assertGreater(ticks, 1, "chunked job must take several pump ticks")
        self.assertTrue(job.result["success"])
        self.assertIsNotNone(bpy.data.collections.get("Arredamento"))
        self.assertIn("history", job.result)
        self.assertTrue(job.result["history"]["steps"])
        # Job slot released when done.
        self.assertIsNone(dispatch.get_status()["job"])

    def test_separate_job_chunks_per_group(self):
        bpy.ops.mesh.primitive_cube_add(location=(-2, 0, 0))
        a = bpy.context.active_object
        a.name = "PartCubeA"
        bpy.ops.mesh.primitive_cube_add(location=(2, 0, 0))
        b = bpy.context.active_object
        b.name = "PartCubeB"
        bpy.ops.object.select_all(action="DESELECT")
        a.select_set(True)
        b.select_set(True)
        bpy.context.view_layer.objects.active = a
        bpy.ops.object.join()
        joined = bpy.context.active_object
        joined.name = "TwoCubes"
        bpy.ops.object.select_all(action="DESELECT")
        joined.select_set(True)
        bpy.context.view_layer.objects.active = joined

        res = scheduler.submit_job("separate_logical_areas", {"lang": "it", "use_vision": False})
        self.assertTrue(res["success"], res)
        job_id = res["job_id"]

        job, ticks = _pump_until(job_id)
        self.assertEqual(job.status, JobStatus.COMPLETED, job.error)
        self.assertGreater(ticks, 3, "organize loop must yield per group")
        self.assertGreaterEqual(len(job.result["groups"]), 1)
        self.assertIn("history", job.result)
        phases = [s["status"] for s in job.result["history"]["steps"]]
        self.assertTrue(any(s.startswith("Placing group") for s in phases))
        self.assertTrue(any(s.startswith("Done:") for s in phases))

    def test_cancel_between_chunks_drops_remaining_work(self):
        bpy.ops.mesh.primitive_cube_add(location=(-2, 0, 0))
        a = bpy.context.active_object
        a.name = "CancelCubeA"
        bpy.ops.mesh.primitive_cube_add(location=(2, 0, 0))
        b = bpy.context.active_object
        b.name = "CancelCubeB"
        bpy.ops.object.select_all(action="DESELECT")
        a.select_set(True)
        b.select_set(True)
        bpy.context.view_layer.objects.active = a
        bpy.ops.object.join()
        joined = bpy.context.active_object
        joined.name = "CancelCubes"
        bpy.ops.object.select_all(action="DESELECT")
        joined.select_set(True)
        bpy.context.view_layer.objects.active = joined

        res = scheduler.submit_job("separate_logical_areas", {"lang": "it", "use_vision": False})
        job_id = res["job_id"]

        # Run until the classify step reported, then cancel mid-organize.
        for _ in range(50):
            scheduler.pump_jobs()
            mid = GLOBAL_JOB_MANAGER.get_job(job_id)
            if mid is not None and "Grouped into" in (mid.message or ""):
                break
        cancel_res = TOOL_REGISTRY["cancel_job"].execute({"job_id": job_id})
        self.assertTrue(cancel_res["success"])

        job, _ = _pump_until(job_id)
        self.assertEqual(job.status, JobStatus.CANCELLED)
        # Organize never finished: no root empty, no final report.
        self.assertIsNone(bpy.data.objects.get("CancelCubes_Organizzato"))
        self.assertIsNone(dispatch.get_status()["job"])

    def test_delete_and_prune_jobs(self):
        old = scheduler.submit_job("list_jobs", {})
        old_job, _ = _pump_until(old["job_id"])
        self.assertEqual(old_job.status, JobStatus.COMPLETED)
        # Backdate it 2 days (same-process record, safe to touch directly).
        old_job.start_time -= 2 * 86400
        old_job.end_time = old_job.start_time + 1.0

        fresh = scheduler.submit_job("list_jobs", {})
        fresh_job, _ = _pump_until(fresh["job_id"])
        self.assertEqual(fresh_job.status, JobStatus.COMPLETED)

        prune = TOOL_REGISTRY["prune_jobs"].execute({"older_than_days": 1.0})
        self.assertTrue(prune["success"], prune)
        self.assertGreaterEqual(prune["deleted"], 1)
        self.assertIsNone(GLOBAL_JOB_MANAGER.get_job(old_job.id))
        self.assertIsNotNone(GLOBAL_JOB_MANAGER.get_job(fresh_job.id))

        delete = TOOL_REGISTRY["delete_job"].execute({"job_id": fresh_job.id})
        self.assertTrue(delete["success"], delete)
        self.assertIsNone(GLOBAL_JOB_MANAGER.get_job(fresh_job.id))

        missing = TOOL_REGISTRY["delete_job"].execute({"job_id": "job_nope"})
        self.assertFalse(missing["success"])
        bad = TOOL_REGISTRY["prune_jobs"].execute({"older_than_days": -1})
        self.assertFalse(bad["success"])

    def test_delete_active_job_is_refused(self):
        sub = scheduler.submit_job("list_jobs", {})
        queued = GLOBAL_JOB_MANAGER.get_job(sub["job_id"])
        self.assertEqual(queued.status, JobStatus.QUEUED)

        refused = TOOL_REGISTRY["delete_job"].execute({"job_id": sub["job_id"]})
        self.assertFalse(refused["success"])
        self.assertIn("cancel_job", refused["message"])
        # Still there, still queued -- abort first, then delete works.
        TOOL_REGISTRY["cancel_job"].execute({"job_id": sub["job_id"]})
        job, _ = _pump_until(sub["job_id"])
        self.assertEqual(job.status, JobStatus.CANCELLED)
        gone = TOOL_REGISTRY["delete_job"].execute({"job_id": sub["job_id"]})
        self.assertTrue(gone["success"], gone)

    def test_separate_vision_steps_chunk_per_candidate(self):
        if not os.environ.get("OPENROUTER_API_KEY"):
            self.skipTest("needs OPENROUTER_API_KEY for the vision gate")
        bpy.ops.mesh.primitive_cube_add(location=(-2, 0, 0))
        a = bpy.context.active_object
        a.name = "VisCubeA"
        bpy.ops.mesh.primitive_cube_add(location=(2, 0, 0))
        b = bpy.context.active_object
        b.name = "VisCubeB"
        bpy.ops.object.select_all(action="DESELECT")
        a.select_set(True)
        b.select_set(True)
        bpy.context.view_layer.objects.active = a
        bpy.ops.object.join()
        joined = bpy.context.active_object
        joined.name = "VisCubes"
        bpy.ops.object.select_all(action="DESELECT")
        joined.select_set(True)
        bpy.context.view_layer.objects.active = joined

        calls = []

        def fake_vision(piece_obj, category_name, lang, vision_model=None):
            calls.append(piece_obj.name)
            return f"Vista_{len(calls)}"

        with mock.patch(
            "extension.tools.localization_ops._vision_rename_piece", side_effect=fake_vision
        ):
            res = scheduler.submit_job(
                "separate_logical_areas",
                {
                    "lang": "it",
                    "use_vision": True,
                    "vision_only_generic": False,
                    "max_vision_renames": 99,
                },
            )
            self.assertTrue(res["success"], res)
            job, ticks = _pump_until(res["job_id"])

        self.assertEqual(job.status, JobStatus.COMPLETED, job.error)
        self.assertEqual(len(calls), 2, "one vision chunk per separated part")
        self.assertEqual(len(job.result["vision_renames"]), 2)
        flat_parts = [p for g in job.result["groups"] for p in g["parts"]]
        self.assertIn("Vista_1", flat_parts)
        self.assertIn("Vista_2", flat_parts)
