import math
import bpy

from .base import ToolBase


class CreateArmatureTool(ToolBase):
    name = "create_armature"
    description = "Create an armature with one or more bones and optionally bind a mesh with automatic vertex weights."

    def execute(self, params: dict) -> dict:
        name = params.get("name", "Armature")
        location = params.get("location", [0, 0, 0])
        bones_spec = params.get("bones")
        bind_mesh_name = params.get("bind_mesh")
        bind_type = params.get("bind_type", "AUTOMATIC_WEIGHTS").upper()

        # Create armature data and object
        arm_data = bpy.data.armatures.new(f"{name}_Data")
        arm_obj = bpy.data.objects.new(name, arm_data)
        arm_obj.location = location
        bpy.context.scene.collection.objects.link(arm_obj)

        bpy.context.view_layer.objects.active = arm_obj
        bpy.ops.object.mode_set(mode="EDIT")

        created_bones = []
        try:
            if not bones_spec:
                # Default single root bone
                bone = arm_data.edit_bones.new("Bone")
                bone.head = (0, 0, 0)
                bone.tail = (0, 0, 1)
                created_bones.append("Bone")
            else:
                for b in bones_spec:
                    b_name = b.get("name", f"Bone_{len(created_bones)}")
                    bone = arm_data.edit_bones.new(b_name)
                    bone.head = tuple(b.get("head", [0, 0, 0]))
                    bone.tail = tuple(b.get("tail", [0, 0, 1]))
                    parent_name = b.get("parent")
                    if parent_name and parent_name in arm_data.edit_bones:
                        bone.parent = arm_data.edit_bones[parent_name]
                        bone.use_connect = bool(b.get("use_connect", True))
                    created_bones.append(b_name)
        finally:
            bpy.ops.object.mode_set(mode="OBJECT")

        # Bind mesh if requested
        bound_mesh = None
        if bind_mesh_name:
            mesh_obj = bpy.data.objects.get(bind_mesh_name)
            if mesh_obj and mesh_obj.type == "MESH":
                bpy.ops.object.select_all(action="DESELECT")
                mesh_obj.select_set(True)
                arm_obj.select_set(True)
                bpy.context.view_layer.objects.active = arm_obj

                if bind_type == "AUTOMATIC_WEIGHTS":
                    bpy.ops.object.parent_set(type="ARMATURE_AUTO")
                elif bind_type == "ENVELOPE_WEIGHTS":
                    bpy.ops.object.parent_set(type="ARMATURE_ENVELOPE")
                else:  # EMPTY_GROUPS
                    bpy.ops.object.parent_set(type="ARMATURE_NAME")
                bound_mesh = mesh_obj.name

        return {
            "success": True,
            "message": f"Created armature '{arm_obj.name}' with {len(created_bones)} bone(s)" + (f" bound to '{bound_mesh}'" if bound_mesh else ""),
            "armature_name": arm_obj.name,
            "bones": created_bones,
            "bound_mesh": bound_mesh,
        }


class PoseBoneTool(ToolBase):
    name = "pose_bone"
    description = "Transform a bone in Pose Mode (location, rotation, scale) and optionally insert keyframes for skeletal animation."

    def execute(self, params: dict) -> dict:
        armature_name = params.get("armature_name")
        bone_name = params.get("bone_name")
        location = params.get("location")
        rotation_euler = params.get("rotation_euler")
        rotation_quaternion = params.get("rotation_quaternion")
        scale = params.get("scale")
        frame = params.get("frame")

        if not armature_name:
            return {"success": False, "message": "'armature_name' is required"}
        if not bone_name:
            return {"success": False, "message": "'bone_name' is required"}

        arm_obj = bpy.data.objects.get(armature_name)
        if not arm_obj or arm_obj.type != "ARMATURE":
            return {"success": False, "message": f"Armature '{armature_name}' not found or not an ARMATURE"}

        pbone = arm_obj.pose.bones.get(bone_name)
        if not pbone:
            return {"success": False, "message": f"Bone '{bone_name}' not found in pose bones of '{armature_name}'"}

        if location is not None:
            pbone.location = tuple(location)
            if frame is not None:
                pbone.keyframe_insert(data_path="location", frame=frame)

        if rotation_euler is not None:
            pbone.rotation_mode = "XYZ"
            pbone.rotation_euler = tuple(rotation_euler)
            if frame is not None:
                pbone.keyframe_insert(data_path="rotation_euler", frame=frame)
        elif rotation_quaternion is not None:
            pbone.rotation_mode = "QUATERNION"
            pbone.rotation_quaternion = tuple(rotation_quaternion)
            if frame is not None:
                pbone.keyframe_insert(data_path="rotation_quaternion", frame=frame)

        if scale is not None:
            pbone.scale = tuple(scale)
            if frame is not None:
                pbone.keyframe_insert(data_path="scale", frame=frame)

        return {
            "success": True,
            "message": f"Updated pose for bone '{bone_name}' in armature '{armature_name}'" + (f" at frame {frame}" if frame is not None else ""),
            "armature_name": armature_name,
            "bone_name": bone_name,
            "frame": frame,
        }
