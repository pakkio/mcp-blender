import math
import bpy

from .base import ToolBase


class CreateGeometryNodesTool(ToolBase):
    name = "create_geometry_nodes"
    description = "Create and configure a Geometry Nodes modifier on an object with built-in presets (EMPTY, SCATTER_ON_SURFACE, EXTRUDE_FACES, SUBDIVIDE_AND_NOISE, CURVE_TO_TUBE, WIREFRAME_LATTICE, PROCEDURAL_GRID_ARRAY)."

    def execute(self, params: dict) -> dict:
        object_name = params.get("object_name")
        mod_name = params.get("modifier_name", "GeometryNodes")
        preset = params.get("preset", "EMPTY").upper()
        p = params.get("preset_params") or {}

        if not object_name:
            return {"success": False, "message": "'object_name' is required"}

        obj = bpy.data.objects.get(object_name)
        if not obj:
            return {"success": False, "message": f"Object '{object_name}' not found"}

        # Create Geometry Nodes modifier
        mod = obj.modifiers.new(name=mod_name, type="NODES")

        # Create or assign Node Tree
        tree_name = f"GN_{object_name}_{preset}"
        tree = bpy.data.node_groups.new(name=tree_name, type="GeometryNodeTree")
        mod.node_group = tree

        # Setup standard input/output interface
        tree.is_modifier = True
        nodes = tree.nodes
        links = tree.links
        nodes.clear()

        # Create Group Input & Group Output
        input_node = nodes.new("NodeGroupInput")
        input_node.location = (-400, 0)

        output_node = nodes.new("NodeGroupOutput")
        output_node.location = (400, 0)

        # In modern Blender (4.x/5.x), interface items define the sockets
        if hasattr(tree, "interface"):
            if not any(item.name == "Geometry" for item in tree.interface.items_tree):
                tree.interface.new_socket(name="Geometry", in_out="INPUT", socket_type="NodeSocketGeometry")
                tree.interface.new_socket(name="Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")
        elif hasattr(tree, "inputs"):
            if "Geometry" not in tree.inputs:
                tree.inputs.new("NodeSocketGeometry", "Geometry")
            if "Geometry" not in tree.outputs:
                tree.outputs.new("NodeSocketGeometry", "Geometry")

        # Build Presets
        if preset == "EMPTY":
            links.new(input_node.outputs["Geometry"], output_node.inputs["Geometry"])

        elif preset == "SCATTER_ON_SURFACE":
            # Distribute Points + Instance on Points
            density = float(p.get("density", 10.0))
            dist_node = nodes.new("GeometryNodeDistributePointsOnFaces")
            dist_node.location = (-150, 0)
            if "Density" in dist_node.inputs:
                dist_node.inputs["Density"].default_value = density

            inst_node = nodes.new("GeometryNodeInstanceOnPoints")
            inst_node.location = (100, 0)

            # Create default pebble/cone primitive instance if none provided
            cube_node = nodes.new("GeometryNodeMeshCube")
            cube_node.location = (-150, -200)
            scale = float(p.get("instance_scale", 0.1))
            if "Size" in cube_node.inputs:
                cube_node.inputs["Size"].default_value = (scale, scale, scale)

            join_node = nodes.new("GeometryNodeJoinGeometry")
            join_node.location = (250, 0)

            links.new(input_node.outputs["Geometry"], dist_node.inputs["Mesh"])
            links.new(dist_node.outputs["Points"], inst_node.inputs["Points"])
            links.new(cube_node.outputs["Mesh"], inst_node.inputs["Instance"])

            links.new(input_node.outputs["Geometry"], join_node.inputs["Geometry"])
            links.new(inst_node.outputs["Instances"], join_node.inputs["Geometry"])
            links.new(join_node.outputs["Geometry"], output_node.inputs["Geometry"])

        elif preset == "EXTRUDE_FACES":
            extrude_node = nodes.new("GeometryNodeExtrudeMesh")
            extrude_node.location = (-100, 0)
            offset_scale = float(p.get("offset_scale", 0.2))
            if "Offset Scale" in extrude_node.inputs:
                extrude_node.inputs["Offset Scale"].default_value = offset_scale

            join_node = nodes.new("GeometryNodeJoinGeometry")
            join_node.location = (150, 0)

            links.new(input_node.outputs["Geometry"], extrude_node.inputs["Mesh"])
            links.new(input_node.outputs["Geometry"], join_node.inputs["Geometry"])
            links.new(extrude_node.outputs["Mesh"], join_node.inputs["Geometry"])
            links.new(join_node.outputs["Geometry"], output_node.inputs["Geometry"])

        elif preset == "SUBDIVIDE_AND_NOISE":
            subdiv_node = nodes.new("GeometryNodeSubdivideMesh")
            subdiv_node.location = (-200, 0)
            if "Level" in subdiv_node.inputs:
                subdiv_node.inputs["Level"].default_value = int(p.get("level", 2))

            set_pos = nodes.new("GeometryNodeSetPosition")
            set_pos.location = (100, 0)

            noise = nodes.new("ShaderNodeTexNoise")
            noise.location = (-100, -200)
            if "Scale" in noise.inputs:
                noise.inputs["Scale"].default_value = float(p.get("noise_scale", 3.0))

            vec_math = nodes.new("ShaderNodeVectorMath")
            vec_math.operation = "SCALE"
            vec_math.location = (0, -200)
            if "Scale" in vec_math.inputs:
                vec_math.inputs["Scale"].default_value = float(p.get("displacement_strength", 0.2))

            links.new(input_node.outputs["Geometry"], subdiv_node.inputs["Mesh"])
            links.new(subdiv_node.outputs["Mesh"], set_pos.inputs["Geometry"])
            links.new(noise.outputs.get("Color") or noise.outputs[0], vec_math.inputs["Vector"])
            links.new(vec_math.outputs["Vector"], set_pos.inputs["Offset"])
            links.new(set_pos.outputs["Geometry"], output_node.inputs["Geometry"])

        elif preset == "CURVE_TO_TUBE":
            c2m = nodes.new("GeometryNodeCurveToMesh")
            c2m.location = (0, 0)

            circle = nodes.new("GeometryNodeCurvePrimitiveCircle")
            circle.location = (-200, -150)
            radius = float(p.get("radius", 0.05))
            if "Radius" in circle.inputs:
                circle.inputs["Radius"].default_value = radius

            links.new(input_node.outputs["Geometry"], c2m.inputs["Curve"])
            links.new(circle.outputs["Curve"], c2m.inputs["Profile Curve"])
            links.new(c2m.outputs["Mesh"], output_node.inputs["Geometry"])

        elif preset == "WIREFRAME_LATTICE":
            m2c = nodes.new("GeometryNodeMeshToCurve")
            m2c.location = (-100, 0)

            c2m = nodes.new("GeometryNodeCurveToMesh")
            c2m.location = (100, 0)

            circle = nodes.new("GeometryNodeCurvePrimitiveCircle")
            circle.location = (-100, -200)
            if "Radius" in circle.inputs:
                circle.inputs["Radius"].default_value = float(p.get("wire_radius", 0.02))

            links.new(input_node.outputs["Geometry"], m2c.inputs["Mesh"])
            links.new(m2c.outputs["Curve"], c2m.inputs["Curve"])
            links.new(circle.outputs["Curve"], c2m.inputs["Profile Curve"])
            links.new(c2m.outputs["Mesh"], output_node.inputs["Geometry"])

        return {
            "success": True,
            "message": f"Created Geometry Nodes tree '{tree.name}' with preset '{preset}' on '{object_name}'",
            "object_name": object_name,
            "modifier_name": mod.name,
            "tree_name": tree.name,
            "preset": preset,
            "nodes_count": len(tree.nodes),
        }


class EditGeometryNodesTool(ToolBase):
    name = "edit_geometry_nodes"
    description = "Inspect and edit Geometry Nodes graphs: add/remove nodes, connect sockets, set exposed modifier input values, or query full node graph structure."

    def execute(self, params: dict) -> dict:
        object_name = params.get("object_name")
        mod_name = params.get("modifier_name", "GeometryNodes")
        action = params.get("action", "GET_GRAPH_INFO").upper()

        if not object_name:
            return {"success": False, "message": "'object_name' is required"}

        obj = bpy.data.objects.get(object_name)
        if not obj:
            return {"success": False, "message": f"Object '{object_name}' not found"}

        mod = obj.modifiers.get(mod_name)
        if not mod or mod.type != "NODES" or not mod.node_group:
            return {"success": False, "message": f"Geometry Nodes modifier '{mod_name}' not found on '{object_name}'"}

        tree = mod.node_group
        nodes = tree.nodes
        links = tree.links

        if action in ("GET_GRAPH_INFO", "INSPECT", "INSPECT_TREE"):
            node_list = []
            for n in nodes:
                node_list.append({
                    "name": n.name,
                    "type": n.type,
                    "label": n.label,
                    "location": [round(n.location.x, 1), round(n.location.y, 1)],
                    "inputs": [sock.name for sock in n.inputs],
                    "outputs": [sock.name for sock in n.outputs],
                })
            link_list = []
            for l in links:
                link_list.append({
                    "from_node": l.from_node.name,
                    "from_socket": l.from_socket.name,
                    "to_node": l.to_node.name,
                    "to_socket": l.to_socket.name,
                })

            return {
                "success": True,
                "tree_name": tree.name,
                "nodes": node_list,
                "links": link_list,
            }

        elif action == "ADD_NODE":
            node_type = params.get("node_type")
            node_name = params.get("node_name")
            loc = params.get("node_location", [0, 0])

            if not node_type:
                return {"success": False, "message": "'node_type' is required for ADD_NODE"}

            new_node = nodes.new(node_type)
            if node_name:
                new_node.name = node_name
            new_node.location = tuple(loc)

            return {
                "success": True,
                "message": f"Added node '{new_node.name}' ({node_type}) to '{tree.name}'",
                "node_name": new_node.name,
                "node_type": node_type,
            }

        elif action == "CONNECT_NODES":
            from_node_name = params.get("from_node")
            from_sock_name = params.get("from_socket", "Geometry")
            to_node_name = params.get("to_node")
            to_sock_name = params.get("to_socket", "Geometry")

            from_node = nodes.get(from_node_name)
            to_node = nodes.get(to_node_name)

            if not from_node:
                return {"success": False, "message": f"From node '{from_node_name}' not found"}
            if not to_node:
                return {"success": False, "message": f"To node '{to_node_name}' not found"}

            out_sock = from_node.outputs.get(from_sock_name) or from_node.outputs[0]
            in_sock = to_node.inputs.get(to_sock_name) or to_node.inputs[0]

            link = links.new(out_sock, in_sock)

            return {
                "success": True,
                "message": f"Connected '{from_node.name}.{out_sock.name}' -> '{to_node.name}.{in_sock.name}'",
            }

        elif action == "REMOVE_NODE":
            node_name = params.get("node_name")
            n = nodes.get(node_name)
            if not n:
                return {"success": False, "message": f"Node '{node_name}' not found in tree"}
            nodes.remove(n)
            return {"success": True, "message": f"Removed node '{node_name}' from '{tree.name}'"}

        elif action == "SET_INPUT_VALUE":
            input_name = params.get("input_name")
            val = params.get("input_value")

            if not input_name:
                return {"success": False, "message": "'input_name' is required for SET_INPUT_VALUE"}

            # Modifier IDProperty keys are non-human socket identifiers
            # (e.g. "Input_2"), not socket names -- resolve the identifier
            # via the node tree's interface first, exact-matched (case-
            # insensitively) against the socket's real name, rather than
            # substring-matching the identifiers directly (which could
            # match the wrong socket, e.g. "scale" inside "Input_2").
            identifier = None
            if hasattr(tree, "interface"):
                for item in tree.interface.items_tree:
                    if (
                        getattr(item, "item_type", None) == "SOCKET"
                        and getattr(item, "in_out", None) == "INPUT"
                        and item.name.lower() == input_name.lower()
                    ):
                        identifier = item.identifier
                        break
            elif hasattr(tree, "inputs"):
                for sock in tree.inputs:
                    if sock.name.lower() == input_name.lower():
                        identifier = sock.identifier
                        break

            if identifier is None or identifier not in mod:
                return {"success": False, "message": f"Input socket matching '{input_name}' not found on modifier '{mod_name}'"}

            mod[identifier] = val
            return {
                "success": True,
                "message": f"Set modifier input '{input_name}' ({identifier}) to {val}",
                "key": identifier,
                "value": val,
            }

        else:
            return {"success": False, "message": f"Unknown action '{action}'"}


class BakeGeometryNodesTool(ToolBase):
    name = "bake_geometry_nodes"
    description = "Permanently bake Geometry Nodes modifiers to real mesh geometry, with automatic realization of instanced meshes."

    def execute(self, params: dict) -> dict:
        object_name = params.get("object_name")
        mod_name = params.get("modifier_name", "GeometryNodes")

        if not object_name:
            return {"success": False, "message": "'object_name' is required"}

        obj = bpy.data.objects.get(object_name)
        if not obj:
            return {"success": False, "message": f"Object '{object_name}' not found"}

        mod = obj.modifiers.get(mod_name)
        if not mod or mod.type != "NODES":
            return {"success": False, "message": f"Geometry Nodes modifier '{mod_name}' not found on '{object_name}'"}

        # Ensure Realize Instances node is placed before output so instanced points become vertices
        if mod.node_group:
            tree = mod.node_group
            out_node = next((n for n in tree.nodes if n.type == "GROUP_OUTPUT"), None)
            if out_node and out_node.inputs and out_node.inputs[0].links:
                prev_link = out_node.inputs[0].links[0]
                from_sock = prev_link.from_socket

                realize_node = tree.nodes.new("GeometryNodeRealizeInstances")
                realize_node.location = (out_node.location.x - 150, out_node.location.y)
                tree.links.remove(prev_link)
                tree.links.new(from_sock, realize_node.inputs["Geometry"])
                tree.links.new(realize_node.outputs["Geometry"], out_node.inputs[0])

        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.modifier_apply(modifier=mod.name)

        verts_count = len(obj.data.vertices) if (obj.type == "MESH" and obj.data) else 0
        faces_count = len(obj.data.polygons) if (obj.type == "MESH" and obj.data) else 0

        return {
            "success": True,
            "message": f"Successfully baked Geometry Nodes '{mod_name}' into mesh on '{object_name}' ({verts_count} verts, {faces_count} faces)",
            "object_name": object_name,
            "result_vertices": verts_count,
            "result_faces": faces_count,
        }
