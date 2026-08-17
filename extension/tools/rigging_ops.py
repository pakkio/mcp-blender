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

        arm_data = bpy.data.armatures.new(f"{name}_Data")
        arm_obj = bpy.data.objects.new(name, arm_data)
        arm_obj.location = location
        bpy.context.scene.collection.objects.link(arm_obj)

        bpy.context.view_layer.objects.active = arm_obj
        bpy.ops.object.mode_set(mode="EDIT")

        created_bones = []
        try:
            if not bones_spec and "bone_names" in params:
                bone_names = params["bone_names"]
                positions = params.get("head_tail_positions", [])
                bones_spec = []
                for i, b_name in enumerate(bone_names):
                    if i < len(positions) and len(positions[i]) == 2:
                        h, t = positions[i]
                    else:
                        h, t = [0, 0, i], [0, 0, i + 1]
                    parent_b = bone_names[i - 1] if i > 0 else None
                    bones_spec.append({"name": b_name, "head": h, "tail": t, "parent": parent_b})

            if not bones_spec:
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
                else:
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


class SetupIKConstraintTool(ToolBase):
    name = "setup_ik_constraint"
    description = "Add an Inverse Kinematics (IK) constraint to a bone with target, pole target, pole angle, and chain length."

    def execute(self, params: dict) -> dict:
        armature_name = params.get("armature_name")
        bone_name = params.get("bone_name")
        target_name = params.get("target_name")
        target_bone = params.get("target_bone")
        pole_target_name = params.get("pole_target_name")
        pole_target_bone = params.get("pole_target_bone")
        pole_angle = float(params.get("pole_angle", 0.0))
        chain_length = int(params.get("chain_length", 2))
        weight = float(params.get("weight", 1.0))

        if not armature_name or not bone_name or not target_name:
            return {"success": False, "message": "'armature_name', 'bone_name', and 'target_name' are required"}

        arm_obj = bpy.data.objects.get(armature_name)
        if not arm_obj or arm_obj.type != "ARMATURE":
            return {"success": False, "message": f"Armature '{armature_name}' not found"}

        pbone = arm_obj.pose.bones.get(bone_name)
        if not pbone:
            return {"success": False, "message": f"Bone '{bone_name}' not found in '{armature_name}'"}

        target_obj = bpy.data.objects.get(target_name)
        if not target_obj:
            return {"success": False, "message": f"Target object '{target_name}' not found"}

        # Remove existing IK constraint if present
        for c in list(pbone.constraints):
            if c.type == "IK":
                pbone.constraints.remove(c)

        ik = pbone.constraints.new("IK")
        ik.target = target_obj
        if target_bone and target_obj.type == "ARMATURE":
            ik.subtarget = target_bone
        ik.chain_count = chain_length
        ik.influence = weight

        if pole_target_name:
            pole_obj = bpy.data.objects.get(pole_target_name)
            if pole_obj:
                ik.pole_target = pole_obj
                if pole_target_bone and pole_obj.type == "ARMATURE":
                    ik.pole_subtarget = pole_target_bone
                ik.pole_angle = math.radians(pole_angle)

        return {
            "success": True,
            "message": f"Added IK constraint on '{bone_name}' targeting '{target_name}' (chain_length={chain_length})",
            "armature_name": armature_name,
            "bone_name": bone_name,
            "target_name": target_name,
            "chain_length": chain_length,
            "pole_target_name": pole_target_name,
        }


class SetupHumanoidRigPresetTool(ToolBase):
    name = "setup_humanoid_rig_preset"
    description = "Generate a standard humanoid biped skeletal rig with anatomical bone proportions and optional automatic IK controls."

    def execute(self, params: dict) -> dict:
        name = params.get("name", "Humanoid_Rig")
        height = float(params.get("height", 1.8))
        generate_ik = bool(params.get("generate_ik", True))
        location = params.get("location", [0, 0, 0])

        arm_data = bpy.data.armatures.new(f"{name}_Data")
        arm_obj = bpy.data.objects.new(name, arm_data)
        arm_obj.location = location
        bpy.context.scene.collection.objects.link(arm_obj)
        bpy.context.view_layer.objects.active = arm_obj

        bpy.ops.object.mode_set(mode="EDIT")
        created_bones = []

        try:
            eb = arm_data.edit_bones

            # Root & Spine chain
            root = eb.new("Root")
            root.head = (0, 0, 0)
            root.tail = (0, 0.1, 0)

            hips = eb.new("Hips")
            hips.head = (0, 0, height * 0.52)
            hips.tail = (0, 0, height * 0.60)
            hips.parent = root

            spine = eb.new("Spine")
            spine.head = (0, 0, height * 0.60)
            spine.tail = (0, 0, height * 0.70)
            spine.parent = hips
            spine.use_connect = True

            chest = eb.new("Chest")
            chest.head = (0, 0, height * 0.70)
            chest.tail = (0, 0, height * 0.82)
            chest.parent = spine
            chest.use_connect = True

            neck = eb.new("Neck")
            neck.head = (0, 0, height * 0.82)
            neck.tail = (0, 0, height * 0.88)
            neck.parent = chest
            neck.use_connect = True

            head = eb.new("Head")
            head.head = (0, 0, height * 0.88)
            head.tail = (0, 0, height * 1.02)
            head.parent = neck
            head.use_connect = True

            # Arms (Left & Right)
            for side, sign in [("L", 1), ("R", -1)]:
                clavicle = eb.new(f"Clavicle_{side}")
                clavicle.head = (0, 0, height * 0.80)
                clavicle.tail = (sign * height * 0.10, 0, height * 0.80)
                clavicle.parent = chest

                upper_arm = eb.new(f"UpperArm_{side}")
                upper_arm.head = (sign * height * 0.10, 0, height * 0.80)
                upper_arm.tail = (sign * height * 0.26, 0, height * 0.65)
                upper_arm.parent = clavicle

                forearm = eb.new(f"Forearm_{side}")
                forearm.head = (sign * height * 0.26, 0, height * 0.65)
                forearm.tail = (sign * height * 0.40, 0, height * 0.50)
                forearm.parent = upper_arm
                forearm.use_connect = True

                hand = eb.new(f"Hand_{side}")
                hand.head = (sign * height * 0.40, 0, height * 0.50)
                hand.tail = (sign * height * 0.48, 0, height * 0.45)
                hand.parent = forearm
                hand.use_connect = True

                # Legs (Left & Right)
                thigh = eb.new(f"Thigh_{side}")
                thigh.head = (sign * height * 0.08, 0, height * 0.52)
                thigh.tail = (sign * height * 0.08, 0.01, height * 0.28)
                thigh.parent = hips

                shin = eb.new(f"Shin_{side}")
                shin.head = (sign * height * 0.08, 0.01, height * 0.28)
                shin.tail = (sign * height * 0.08, -0.01, height * 0.06)
                shin.parent = thigh
                shin.use_connect = True

                foot = eb.new(f"Foot_{side}")
                foot.head = (sign * height * 0.08, -0.01, height * 0.06)
                foot.tail = (sign * height * 0.08, 0.12, 0.0)
                foot.parent = shin
                foot.use_connect = True

            # IK targets if requested
            if generate_ik:
                for side, sign in [("L", 1), ("R", -1)]:
                    ik_foot = eb.new(f"IK_Foot_{side}")
                    ik_foot.head = (sign * height * 0.08, -0.01, height * 0.06)
                    ik_foot.tail = (sign * height * 0.08, 0.12, 0.0)
                    ik_foot.parent = root

                    pole_knee = eb.new(f"Pole_Knee_{side}")
                    pole_knee.head = (sign * height * 0.08, 0.35, height * 0.28)
                    pole_knee.tail = (sign * height * 0.08, 0.45, height * 0.28)
                    pole_knee.parent = root

                    ik_hand = eb.new(f"IK_Hand_{side}")
                    ik_hand.head = (sign * height * 0.40, 0, height * 0.50)
                    ik_hand.tail = (sign * height * 0.48, 0, height * 0.45)
                    ik_hand.parent = root

                    pole_elbow = eb.new(f"Pole_Elbow_{side}")
                    pole_elbow.head = (sign * height * 0.26, -0.30, height * 0.65)
                    pole_elbow.tail = (sign * height * 0.26, -0.40, height * 0.65)
                    pole_elbow.parent = root

            created_bones = [b.name for b in eb]
        finally:
            bpy.ops.object.mode_set(mode="OBJECT")

        # Apply IK constraints in pose mode if generated
        if generate_ik:
            for side in ("L", "R"):
                shin_bone = arm_obj.pose.bones.get(f"Shin_{side}")
                if shin_bone:
                    ik = shin_bone.constraints.new("IK")
                    ik.target = arm_obj
                    ik.subtarget = f"IK_Foot_{side}"
                    ik.pole_target = arm_obj
                    ik.pole_subtarget = f"Pole_Knee_{side}"
                    ik.chain_count = 2
                    ik.pole_angle = math.radians(-90)

                forearm_bone = arm_obj.pose.bones.get(f"Forearm_{side}")
                if forearm_bone:
                    ik = forearm_bone.constraints.new("IK")
                    ik.target = arm_obj
                    ik.subtarget = f"IK_Hand_{side}"
                    ik.pole_target = arm_obj
                    ik.pole_subtarget = f"Pole_Elbow_{side}"
                    ik.chain_count = 2
                    ik.pole_angle = math.radians(90)

        return {
            "success": True,
            "message": f"Generated humanoid rig '{arm_obj.name}' with {len(created_bones)} bones (IK={generate_ik})",
            "armature_name": arm_obj.name,
            "bones": created_bones,
            "has_ik": generate_ik,
        }


class SetupSplineIKConstraintTool(ToolBase):
    name = "setup_spline_ik_constraint"
    description = "Add a Spline IK constraint to a bone chain to deform along a 3D curve object (ropes, tails, spines, tentacles)."

    def execute(self, params: dict) -> dict:
        armature_name = params.get("armature_name")
        bone_name = params.get("bone_name")
        curve_name = params.get("curve_name")
        chain_length = int(params.get("chain_length", 4))

        if not armature_name or not bone_name or not curve_name:
            return {"success": False, "message": "'armature_name', 'bone_name', and 'curve_name' are required"}

        arm_obj = bpy.data.objects.get(armature_name)
        if not arm_obj or arm_obj.type != "ARMATURE":
            return {"success": False, "message": f"Armature '{armature_name}' not found"}

        pbone = arm_obj.pose.bones.get(bone_name)
        if not pbone:
            return {"success": False, "message": f"Bone '{bone_name}' not found in '{armature_name}'"}

        curve_obj = bpy.data.objects.get(curve_name)
        if not curve_obj or curve_obj.type != "CURVE":
            return {"success": False, "message": f"Curve object '{curve_name}' not found"}

        spline_ik = pbone.constraints.new("SPLINE_IK")
        spline_ik.target = curve_obj
        spline_ik.chain_count = chain_length

        return {
            "success": True,
            "message": f"Configured Spline IK on '{bone_name}' with curve '{curve_name}' (chain_count={chain_length})",
            "armature_name": armature_name,
            "bone_name": bone_name,
            "curve_name": curve_name,
            "chain_length": chain_length,
        }
