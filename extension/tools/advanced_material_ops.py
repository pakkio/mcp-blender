import math
import random
import bpy

from .base import ToolBase


class EditMaterialNodesTool(ToolBase):
    name = "edit_material_nodes"
    description = "Full low-level control over shader node trees: add shader nodes, connect/disconnect sockets, set socket parameter values, remove nodes, and inspect full material node graphs."

    def execute(self, params: dict) -> dict:
        mat_name = params.get("material_name")
        action = params.get("action", "GET_NODE_TREE").upper()

        if not mat_name:
            return {"success": False, "message": "'material_name' is required"}

        mat = bpy.data.materials.get(mat_name)
        if not mat:
            mat = bpy.data.materials.new(name=mat_name)
            mat.use_nodes = True

        mat.use_nodes = True
        nodes = mat.node_tree.nodes
        links = mat.node_tree.links

        if action in ("GET_NODE_TREE", "INSPECT", "INSPECT_TREE"):
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
                "material_name": mat.name,
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
                "message": f"Added node '{new_node.name}' ({node_type}) to '{mat.name}'",
                "node_name": new_node.name,
                "node_type": node_type,
            }

        elif action == "CONNECT_NODES":
            from_node_name = params.get("from_node")
            from_sock_name = params.get("from_socket", "Color")
            to_node_name = params.get("to_node")
            to_sock_name = params.get("to_socket", "Base Color")

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

        elif action == "DISCONNECT_NODES":
            to_node_name = params.get("to_node")
            to_sock_name = params.get("to_socket")

            to_node = nodes.get(to_node_name)
            if not to_node:
                return {"success": False, "message": f"Node '{to_node_name}' not found"}

            removed = 0
            for l in list(links):
                if l.to_node == to_node:
                    if to_sock_name is None or l.to_socket.name == to_sock_name:
                        links.remove(l)
                        removed += 1

            return {"success": True, "message": f"Removed {removed} link(s) on '{to_node.name}'"}

        elif action == "SET_NODE_INPUT":
            node_name = params.get("node_name")
            sock_name = params.get("input_socket")
            val = params.get("input_value")

            node = nodes.get(node_name)
            if not node:
                return {"success": False, "message": f"Node '{node_name}' not found"}

            sock = node.inputs.get(sock_name) if sock_name else node.inputs[0]
            if not sock:
                return {"success": False, "message": f"Socket '{sock_name}' not found on node '{node_name}'"}

            if isinstance(val, list):
                sock.default_value = tuple(val)
            else:
                sock.default_value = val

            return {
                "success": True,
                "message": f"Set '{node.name}.{sock.name}' = {val}",
                "node_name": node.name,
                "socket": sock.name,
                "value": val,
            }

        elif action == "REMOVE_NODE":
            node_name = params.get("node_name")
            n = nodes.get(node_name)
            if not n:
                return {"success": False, "message": f"Node '{node_name}' not found in tree"}
            nodes.remove(n)
            return {"success": True, "message": f"Removed node '{node_name}' from '{mat.name}'"}

        else:
            return {"success": False, "message": f"Unknown action '{action}'"}


class ManageColorAttributesTool(ToolBase):
    name = "manage_color_attributes"
    description = "Manage vertex color attributes: create color layers, fill solid colors, generate height gradients, or random face island colors."

    def execute(self, params: dict) -> dict:
        object_name = params.get("object_name")
        action = params.get("action", "CREATE").upper()
        attr_name = params.get("attribute_name", "Color")
        domain = params.get("domain", "CORNER").upper()
        data_type = params.get("data_type", "FLOAT_COLOR").upper()
        color = params.get("color", [1.0, 0.0, 0.0, 1.0])
        fill_mode = params.get("fill_mode", "SOLID").upper()

        if not object_name:
            return {"success": False, "message": "'object_name' is required"}

        obj = bpy.data.objects.get(object_name)
        if not obj or obj.type != "MESH":
            return {"success": False, "message": f"Object '{object_name}' not found or not a MESH"}

        mesh = obj.data

        if action == "GET_ATTRIBUTES":
            attrs = []
            if hasattr(mesh, "color_attributes"):
                for a in mesh.color_attributes:
                    attrs.append({
                        "name": a.name,
                        "domain": a.domain,
                        "data_type": a.data_type,
                    })
            return {"success": True, "object_name": object_name, "color_attributes": attrs}

        elif action in ("CREATE", "SET_COLOR"):
            if hasattr(mesh, "color_attributes"):
                attr = mesh.color_attributes.get(attr_name)
                if not attr:
                    attr = mesh.color_attributes.new(
                        name=attr_name,
                        type=data_type,
                        domain=domain,
                    )
                mesh.color_attributes.active_color_name = attr_name

                # Fill color data
                if fill_mode == "SOLID":
                    c_val = tuple(color) if len(color) == 4 else (*color, 1.0)
                    for elem in attr.data:
                        elem.color = c_val
                elif fill_mode == "HEIGHT_GRADIENT":
                    # Compute min/max Z
                    z_coords = [v.co.z for v in mesh.vertices]
                    min_z = min(z_coords) if z_coords else 0.0
                    max_z = max(z_coords) if z_coords else 1.0
                    z_range = (max_z - min_z) or 1.0

                    if attr.domain == "POINT":
                        for i, elem in enumerate(attr.data):
                            t = (mesh.vertices[i].co.z - min_z) / z_range
                            elem.color = (t, 1.0 - t, 0.5, 1.0)
                    else:  # CORNER
                        for poly in mesh.polygons:
                            for loop_idx in poly.loop_indices:
                                vert_idx = mesh.loops[loop_idx].vertex_index
                                t = (mesh.vertices[vert_idx].co.z - min_z) / z_range
                                attr.data[loop_idx].color = (t, 1.0 - t, 0.5, 1.0)

            return {
                "success": True,
                "message": f"Configured color attribute '{attr_name}' ({fill_mode}) on '{object_name}'",
                "object_name": object_name,
                "attribute_name": attr_name,
                "fill_mode": fill_mode,
            }

        elif action == "DELETE":
            if hasattr(mesh, "color_attributes"):
                attr = mesh.color_attributes.get(attr_name)
                if attr:
                    mesh.color_attributes.remove(attr)
                    return {"success": True, "message": f"Deleted color attribute '{attr_name}' from '{object_name}'"}
            return {"success": False, "message": f"Color attribute '{attr_name}' not found on '{object_name}'"}

        else:
            return {"success": False, "message": f"Unknown action '{action}'"}
