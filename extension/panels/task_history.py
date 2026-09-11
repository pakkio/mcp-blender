import datetime
import textwrap
import time

import bpy
from ..tools.task_history import TASKS


def _stamp(value):
    return datetime.datetime.fromtimestamp(value).astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")


class MCP_OT_task_history(bpy.types.Operator):
    bl_idname = "mcp_bridge.task_history"
    bl_label = "View Past Tasks"
    bl_description = "Browse this session's tasks and their timestamped progress messages"

    task_index: bpy.props.IntProperty(default=-1)
    page: bpy.props.IntProperty(default=0, min=0)

    def invoke(self, context, event):
        if self.task_index < 0:
            self.task_index = len(TASKS) - 1
        return context.window_manager.invoke_props_dialog(self, width=720)

    def draw(self, context):
        layout = self.layout
        if not TASKS:
            layout.label(text="No tasks recorded yet in this Blender session.")
            return
        index = max(0, min(self.task_index, len(TASKS) - 1))
        task = TASKS[index]
        layout.label(text=f"Task {index + 1} of {len(TASKS)}: {task['title']}")
        layout.label(text="Started: " + _stamp(task["started"]))
        layout.label(text="State: " + task["state"])
        if task["finished"] is not None:
            layout.label(text="Finished: " + _stamp(task["finished"]))
        duration = (task["finished"] or time.time()) - task["started"]
        layout.label(text=f"Duration: {duration:.1f} seconds")
        row = layout.row(align=True)
        for label, target in (("Previous Task", index - 1), ("Next Task", index + 1)):
            col = row.row(align=True)
            col.enabled = 0 <= target < len(TASKS)
            col.operator_context = "INVOKE_DEFAULT"
            op = col.operator(self.bl_idname, text=label)
            op.task_index = target
        messages = task["messages"]
        pages = max(1, (len(messages) + 9) // 10)
        page = min(self.page, pages - 1)
        layout.label(text=f"Messages — page {page + 1} of {pages}")
        for timestamp, message in messages[page * 10:(page + 1) * 10]:
            box = layout.box()
            box.label(text=_stamp(timestamp))
            for line in str(message).splitlines():
                for wrapped in textwrap.wrap(line, width=90):
                    box.label(text=wrapped)
        row = layout.row(align=True)
        for label, target in (("Earlier Messages", page - 1), ("Later Messages", page + 1)):
            col = row.row(align=True)
            col.enabled = 0 <= target < pages
            col.operator_context = "INVOKE_DEFAULT"
            op = col.operator(self.bl_idname, text=label)
            op.task_index = index
            op.page = max(0, target)

    def execute(self, context):
        return {"FINISHED"}


class VIEW3D_PT_mcp_task_history(bpy.types.Panel):
    bl_label = "Task History"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "MCP Bridge"

    def draw(self, context):
        self.layout.label(text=f"{len(TASKS)} tasks recorded this session")
        self.layout.operator(MCP_OT_task_history.bl_idname, icon="TIME")
        for index in range(len(TASKS) - 1, max(-1, len(TASKS) - 6), -1):
            task = TASKS[index]
            box = self.layout.box()
            box.label(text=task["title"])
            box.label(text=_stamp(task["started"]))
            box.label(text=task["state"], icon="ERROR" if task["state"] == "Failure" else "CHECKMARK" if task["state"] == "Success" else "TIME")
            box.operator_context = "INVOKE_DEFAULT"
            box.operator(MCP_OT_task_history.bl_idname, text="View Messages").task_index = index


CLASSES = (MCP_OT_task_history, VIEW3D_PT_mcp_task_history)
