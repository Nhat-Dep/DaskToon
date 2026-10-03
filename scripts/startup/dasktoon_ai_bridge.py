# SPDX-FileCopyrightText: 2026 DaskToon Authors
# SPDX-License-Identifier: GPL-2.0-or-later

"""
DaskToon Live AI Bridge Server
Provides a real-time TCP socket server inside DaskToon for MCP & AI assistants (Antigravity IDE, Claude, Cursor).
"""

import bpy
import socket
import select
import json
import sys
import io
import os
import tempfile
import base64
import traceback

HOST = "127.0.0.1"
PORT = 9998

server_socket = None
timer_handle = None
is_running = False


def handle_client_request(request_data):
    try:
        req = json.loads(request_data)
        action = req.get("action", "run_code")
        
        if action == "ping":
            return {"status": "ok", "message": "DaskToon AI Bridge is online", "version": "0.1-beta (Blender 5.2)"}
        
        elif action == "get_scene_info":
            scene = bpy.context.scene
            objects = [{"name": ob.name, "type": ob.type, "location": list(ob.location), "materials": [m.name for m in ob.data.materials if m] if hasattr(ob.data, 'materials') else []} for ob in scene.objects]
            materials = [m.name for m in bpy.data.materials]
            return {
                "status": "ok",
                "scene_name": scene.name,
                "render_engine": scene.render.engine,
                "frame_current": scene.frame_current,
                "frame_start": scene.frame_start,
                "frame_end": scene.frame_end,
                "active_object": bpy.context.active_object.name if bpy.context.active_object else None,
                "objects_count": len(objects),
                "objects": objects[:50],
                "materials": materials[:50]
            }

        elif action == "capture_viewport":
            temp_img = os.path.join(tempfile.gettempdir(), "dasktoon_viewport_mcp.png")
            # Force redraw
            for window in bpy.context.window_manager.windows:
                for area in window.screen.areas:
                    if area.type == 'VIEW_3D':
                        area.tag_redraw()
            try:
                bpy.ops.screen.screenshot(filepath=temp_img, check_existing=False)
                if os.path.exists(temp_img):
                    with open(temp_img, "rb") as f:
                        b64_data = base64.b64encode(f.read()).decode("ascii")
                    return {"status": "ok", "image_path": temp_img, "image_base64": b64_data}
            except Exception as e:
                return {"status": "error", "message": f"Screenshot failed: {str(e)}"}
            return {"status": "error", "message": "Screenshot file could not be generated"}

        elif action == "create_anime_material":
            mat_name = req.get("name", "Anime_Character_Material")
            base_col = req.get("base_color", [0.98, 0.88, 0.82, 1.0])
            shadow_col = req.get("shadow_color", [0.88, 0.65, 0.66, 1.0])
            rim_col = req.get("rim_color", [1.0, 0.95, 0.85, 1.0])
            target_obj_name = req.get("target_object", None)

            mat = bpy.data.materials.new(mat_name)
            mat.use_nodes = True
            nodes = mat.node_tree.nodes
            links = mat.node_tree.links
            nodes.clear()

            out_node = nodes.new('ShaderNodeOutputMaterial')
            out_node.location = (400, 0)

            anime_bsdf = nodes.new('ShaderNodeAnimeCharacter')
            anime_bsdf.location = (0, 0)

            # Set inputs
            if "Base Color" in anime_bsdf.inputs:
                anime_bsdf.inputs["Base Color"].default_value = base_col
            if "Shadow Color" in anime_bsdf.inputs:
                anime_bsdf.inputs["Shadow Color"].default_value = shadow_col
            if "Rim Color" in anime_bsdf.inputs:
                anime_bsdf.inputs["Rim Color"].default_value = rim_col
            if "Rim Intensity" in anime_bsdf.inputs:
                anime_bsdf.inputs["Rim Intensity"].default_value = req.get("rim_intensity", 0.6)

            bsdf_out = anime_bsdf.outputs.get("BSDF") or anime_bsdf.outputs[0]
            links.new(bsdf_out, out_node.inputs['Surface'])

            # Assign to target object if requested
            assigned_to = None
            if target_obj_name and target_obj_name in bpy.data.objects:
                obj = bpy.data.objects[target_obj_name]
                if obj.type == 'MESH':
                    if not obj.data.materials:
                        obj.data.materials.append(mat)
                    else:
                        obj.data.materials[0] = mat
                    assigned_to = obj.name
            elif bpy.context.active_object and bpy.context.active_object.type == 'MESH':
                obj = bpy.context.active_object
                if not obj.data.materials:
                    obj.data.materials.append(mat)
                else:
                    obj.data.materials[0] = mat
                assigned_to = obj.name

            return {
                "status": "ok",
                "material_name": mat.name,
                "assigned_to_object": assigned_to,
                "node_type": "ShaderNodeAnimeCharacter (Anime BSDF)"
            }

        elif action == "run_code":
            code = req.get("code", "")
            stdout_capture = io.StringIO()
            stderr_capture = io.StringIO()
            old_stdout = sys.stdout
            old_stderr = sys.stderr
            sys.stdout = stdout_capture
            sys.stderr = stderr_capture

            exec_globals = {
                "bpy": bpy,
                "context": bpy.context,
                "data": bpy.data,
                "ops": bpy.ops,
            }
            error_msg = None
            result_val = None
            try:
                # Try eval first for expressions, else exec
                try:
                    result_val = eval(code, exec_globals)
                except SyntaxError:
                    exec(code, exec_globals)
            except Exception:
                error_msg = traceback.format_exc()
            finally:
                sys.stdout = old_stdout
                sys.stderr = old_stderr

            output_str = stdout_capture.getvalue()
            err_str = stderr_capture.getvalue()
            if error_msg:
                err_str = (err_str + "\n" + error_msg).strip()

            return {
                "status": "error" if error_msg else "ok",
                "stdout": output_str,
                "stderr": err_str,
                "result": repr(result_val) if result_val is not None else None
            }

        else:
            return {"status": "error", "message": f"Unknown action: {action}"}

    except Exception as e:
        return {"status": "error", "message": str(e), "traceback": traceback.format_exc()}


def poll_socket():
    global server_socket, is_running
    if not is_running or not server_socket:
        return 0.1

    try:
        readable, _, _ = select.select([server_socket], [], [], 0.0)
        if readable:
            client, addr = server_socket.accept()
            client.settimeout(5.0)
            data_chunks = []
            while True:
                chunk = client.recv(65536)
                if not chunk:
                    break
                data_chunks.append(chunk)
                if b"\n" in chunk or len(chunk) < 65536:
                    break
            
            raw_msg = b"".join(data_chunks).decode("utf-8").strip()
            if raw_msg:
                resp = handle_client_request(raw_msg)
                resp_json = (json.dumps(resp) + "\n").encode("utf-8")
                client.sendall(resp_json)
            client.close()
    except Exception as e:
        # Silently keep running
        pass

    return 0.05


def start_server():
    global server_socket, is_running
    if is_running:
        return

    try:
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind((HOST, PORT))
        server_socket.listen(5)
        server_socket.setblocking(False)
        is_running = True
        
        if not bpy.app.timers.is_registered(poll_socket):
            bpy.app.timers.register(poll_socket, persistent=True)
        print(f"🤖 [DaskToon AI Bridge] Online and listening on tcp://{HOST}:{PORT}")
    except Exception as e:
        print(f"⚠️ [DaskToon AI Bridge] Failed to start server: {e}")
        is_running = False


def stop_server():
    global server_socket, is_running
    is_running = False
    if server_socket:
        try:
            server_socket.close()
        except Exception:
            pass
        server_socket = None
    if bpy.app.timers.is_registered(poll_socket):
        bpy.app.timers.unregister(poll_socket)
    print("🛑 [DaskToon AI Bridge] Server stopped.")


class DASKTOON_PT_ai_bridge(bpy.types.Panel):
    """Panel in 3D Viewport sidebar for AI Bridge status"""
    bl_label = "DaskToon AI Bridge (MCP)"
    bl_idname = "DASKTOON_PT_ai_bridge"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "DaskToon"

    def draw(self, context):
        layout = self.layout
        box = layout.box()
        if is_running:
            box.label(text="🟢 AI Bridge Online (Port 9998)", icon='RADIOBUT_ON')
            box.label(text="Ready for MCP / Antigravity IDE", icon='CHECKMARK')
        else:
            box.label(text="🔴 AI Bridge Offline", icon='RADIOBUT_OFF')
            box.operator("dasktoon.start_ai_bridge", text="Start AI Bridge", icon='PLAY')


class DASKTOON_OT_start_ai_bridge(bpy.types.Operator):
    bl_idname = "dasktoon.start_ai_bridge"
    bl_label = "Start AI Bridge"
    bl_description = "Start the DaskToon MCP AI Bridge server"

    def execute(self, context):
        start_server()
        return {'FINISHED'}


classes = (
    DASKTOON_PT_ai_bridge,
    DASKTOON_OT_start_ai_bridge,
)


def register():
    for cls in classes:
        try:
            bpy.utils.register_class(cls)
        except Exception:
            pass
    # Auto-start in GUI mode
    if not bpy.app.background:
        bpy.app.timers.register(start_server, first_interval=0.5)


def unregister():
    stop_server()
    for cls in reversed(classes):
        try:
            bpy.utils.unregister_class(cls)
        except Exception:
            pass


if __name__ == "__main__":
    register()
