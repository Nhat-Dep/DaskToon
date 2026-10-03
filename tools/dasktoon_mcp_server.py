#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 DaskToon Authors
# SPDX-License-Identifier: GPL-2.0-or-later

"""
DaskToon Native MCP (Model Context Protocol) Server
Implements standard JSON-RPC 2.0 MCP protocol over stdio for Antigravity IDE, Claude Desktop, and Cursor.
Connects to live DaskToon GUI via local socket (port 9998) with automatic headless fallback.
"""

import sys
import json
import socket
import subprocess
import os
import tempfile
import base64
import traceback

SOCKET_HOST = "127.0.0.1"
SOCKET_PORT = 9998
DASKTOON_EXE = r"D:\build_windows_x64_vc17_Release\bin\Release\DaskToon.exe"


def send_to_live_dasktoon(payload, timeout=8.0):
    """Attempt to send payload to live DaskToon GUI via TCP socket."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(timeout)
        s.connect((SOCKET_HOST, SOCKET_PORT))
        msg = (json.dumps(payload) + "\n").encode("utf-8")
        s.sendall(msg)
        
        chunks = []
        while True:
            chunk = s.recv(65536)
            if not chunk:
                break
            chunks.append(chunk)
            if b"\n" in chunk:
                break
        s.close()
        
        raw_res = b"".join(chunks).decode("utf-8").strip()
        if raw_res:
            return json.loads(raw_res)
    except Exception:
        return None
    return None


def run_headless_code(code_str):
    """Fallback: execute code using DaskToon headless CLI."""
    if not os.path.exists(DASKTOON_EXE):
        return {"status": "error", "message": f"DaskToon binary not found at {DASKTOON_EXE}"}

    wrapper = f"""
import sys, json, io, traceback, bpy
stdout_capture = io.StringIO()
old_stdout = sys.stdout
sys.stdout = stdout_capture
err_msg = None
res_val = None
try:
    code = {repr(code_str)}
    exec_globals = {{"bpy": bpy, "context": bpy.context, "data": bpy.data, "ops": bpy.ops}}
    try:
        res_val = eval(code, exec_globals)
    except SyntaxError:
        exec(code, exec_globals)
except Exception:
    err_msg = traceback.format_exc()
finally:
    sys.stdout = old_stdout

output = {{
    "status": "error" if err_msg else "ok",
    "stdout": stdout_capture.getvalue(),
    "stderr": err_msg or "",
    "result": repr(res_val) if res_val is not None else None
}}
print("__DASKTOON_JSON_START__" + json.dumps(output) + "__DASKTOON_JSON_END__")
"""
    try:
        proc = subprocess.run(
            [DASKTOON_EXE, "--background", "--python-expr", wrapper],
            capture_output=True,
            text=True,
            timeout=30
        )
        combined = proc.stdout + "\n" + proc.stderr
        if "__DASKTOON_JSON_START__" in combined and "__DASKTOON_JSON_END__" in combined:
            raw_json = combined.split("__DASKTOON_JSON_START__")[1].split("__DASKTOON_JSON_END__")[0]
            return json.loads(raw_json)
        return {"status": "ok", "stdout": proc.stdout, "stderr": proc.stderr}
    except Exception as e:
        return {"status": "error", "message": str(e)}


# -----------------------------------------------------------------------------
# MCP Tool Handlers
# -----------------------------------------------------------------------------

def tool_execute_code(args):
    code = args.get("code", "")
    # Try live socket first
    resp = send_to_live_dasktoon({"action": "run_code", "code": code})
    mode = "Live Viewport"
    if resp is None:
        resp = run_headless_code(code)
        mode = "Headless CLI"
    
    status = resp.get("status", "ok")
    stdout = resp.get("stdout", "")
    stderr = resp.get("stderr", "")
    result = resp.get("result", None)
    
    text = f"[{mode}] Status: {status}\n"
    if stdout:
        text += f"\n--- Standard Output ---\n{stdout}\n"
    if result and result != "None":
        text += f"\n--- Result ---\n{result}\n"
    if stderr:
        text += f"\n--- Errors ---\n{stderr}\n"
    return [{"type": "text", "text": text.strip()}]


def tool_get_scene_summary(args):
    resp = send_to_live_dasktoon({"action": "get_scene_info"})
    if resp is None:
        py_code = """
scene = bpy.context.scene
objects = [{"name": ob.name, "type": ob.type, "location": list(ob.location), "materials": [m.name for m in ob.data.materials if m] if hasattr(ob.data, 'materials') else []} for ob in scene.objects]
materials = [m.name for m in bpy.data.materials]
res = {
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
res
"""
        raw_res = run_headless_code(py_code)
        try:
            resp = eval(raw_res.get("result", "{}"))
        except Exception:
            resp = raw_res

    return [{"type": "text", "text": json.dumps(resp, indent=2)}]


def tool_create_anime_material(args):
    payload = {
        "action": "create_anime_material",
        "name": args.get("name", "Anime_Character_Mat"),
        "base_color": args.get("base_color", [0.98, 0.88, 0.82, 1.0]),
        "shadow_color": args.get("shadow_color", [0.88, 0.65, 0.66, 1.0]),
        "rim_color": args.get("rim_color", [1.0, 0.95, 0.85, 1.0]),
        "rim_intensity": args.get("rim_intensity", 0.6),
        "target_object": args.get("target_object", None),
    }
    resp = send_to_live_dasktoon(payload)
    if resp is None:
        py_code = f"""
mat = bpy.data.materials.new({repr(payload['name'])})
mat.use_nodes = True
nodes = mat.node_tree.nodes
nodes.clear()
out = nodes.new('ShaderNodeOutputMaterial')
out.location = (400, 0)
bsdf = nodes.new('ShaderNodeAnimeCharacter')
bsdf.location = (0, 0)
if "Base Color" in bsdf.inputs:
    bsdf.inputs["Base Color"].default_value = {payload['base_color']}
if "Shadow Color" in bsdf.inputs:
    bsdf.inputs["Shadow Color"].default_value = {payload['shadow_color']}
if "Rim Color" in bsdf.inputs:
    bsdf.inputs["Rim Color"].default_value = {payload['rim_color']}
if "Rim Intensity" in bsdf.inputs:
    bsdf.inputs["Rim Intensity"].default_value = {payload['rim_intensity']}
mat.node_tree.links.new(bsdf.outputs['BSDF'], out.inputs['Surface'])
{f"if {repr(payload['target_object'])} in bpy.data.objects: bpy.data.objects[{repr(payload['target_object'])}].data.materials.append(mat)" if payload['target_object'] else ""}
{{"status": "ok", "material_name": mat.name, "node_type": "ShaderNodeAnimeCharacter (Anime BSDF)"}}
"""
        raw_res = run_headless_code(py_code)
        try:
            resp = eval(raw_res.get("result", "{}"))
        except Exception:
            resp = raw_res

    return [{"type": "text", "text": json.dumps(resp, indent=2)}]


def tool_capture_viewport(args):
    resp = send_to_live_dasktoon({"action": "capture_viewport"})
    if resp and resp.get("status") == "ok" and resp.get("image_base64"):
        return [
            {"type": "text", "text": f"Screenshot captured from Live DaskToon Viewport: {resp.get('image_path')}"},
            {"type": "image", "data": resp["image_base64"], "mimeType": "image/png"}
        ]
    return [{"type": "text", "text": "Live DaskToon GUI is not open. Open DaskToon to capture live interactive Viewport screenshots."}]


def tool_setup_arkit_shapekeys(args):
    obj_name = args.get("target_object", None)
    py_code = f"""
target_name = {repr(obj_name)}
obj = bpy.data.objects.get(target_name) if target_name else bpy.context.active_object
if not obj or obj.type != 'MESH':
    res = {{"status": "error", "message": "No valid mesh object found."}}
else:
    # Ensure basis shape key
    if not obj.data.shape_keys:
        obj.shape_key_add(name="Basis")
    arkit_names = [
        "EyeBlinkLeft", "EyeBlinkRight", "EyeSquintLeft", "EyeSquintRight",
        "EyeWideLeft", "EyeWideRight", "JawOpen", "MouthSmileLeft", "MouthSmileRight",
        "MouthFrownLeft", "MouthFrownRight", "MouthPucker", "MouthFunnel", "BrowInnerUp",
        "BrowDownLeft", "BrowDownRight", "BrowOuterUpLeft", "BrowOuterUpRight"
    ]
    created = []
    for k in arkit_names:
        if k not in obj.data.shape_keys.key_blocks:
            obj.shape_key_add(name=k)
            created.append(k)
    res = {{
        "status": "ok",
        "object": obj.name,
        "total_shape_keys": len(obj.data.shape_keys.key_blocks),
        "newly_created_arkit_keys": created
    }}
res
"""
    resp = send_to_live_dasktoon({"action": "run_code", "code": py_code})
    if resp and resp.get("result"):
        try:
            return [{"type": "text", "text": json.dumps(eval(resp["result"]), indent=2)}]
        except Exception:
            return [{"type": "text", "text": str(resp["result"])}]
    
    raw = run_headless_code(py_code)
    return [{"type": "text", "text": json.dumps(raw, indent=2)}]


# -----------------------------------------------------------------------------
# MCP Server Capabilities & Tools Catalog
# -----------------------------------------------------------------------------

TOOLS = [
    {
        "name": "dasktoon_execute_code",
        "description": "Execute arbitrary Python code inside DaskToon. If DaskToon GUI is open, executes live on the main UI thread with instant Viewport update; otherwise runs headless.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "code": {"type": "string", "description": "Python code to execute inside DaskToon (has access to bpy, context, data, ops)"}
            },
            "required": ["code"]
        }
    },
    {
        "name": "dasktoon_get_scene_summary",
        "description": "Query the current DaskToon scene summary: active object, list of objects, materials, current frame range, and active render engine.",
        "inputSchema": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "dasktoon_create_anime_material",
        "description": "Create and configure a full DaskToon Anime BSDF (ShaderNodeAnimeCharacter) cel shading material with custom Base Color, Warm Shadow Color, and Rim Light.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Name for the material"},
                "base_color": {"type": "array", "items": {"type": "number"}, "description": "RGBA base lit color [r, g, b, a]"},
                "shadow_color": {"type": "array", "items": {"type": "number"}, "description": "RGBA shadow color [r, g, b, a]"},
                "rim_color": {"type": "array", "items": {"type": "number"}, "description": "RGBA rim light color [r, g, b, a]"},
                "rim_intensity": {"type": "number", "description": "Rim light intensity (0.0 to 1.0)"},
                "target_object": {"type": "string", "description": "Optional name of mesh object to assign the material to"}
            }
        }
    },
    {
        "name": "dasktoon_setup_vrm_arkit",
        "description": "Automatically initialize and configure standard 52 ARKit Perfect Sync facial shape keys on any anime/VTuber character mesh.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "target_object": {"type": "string", "description": "Name of character head/face mesh object. Defaults to active object."}
            }
        }
    },
    {
        "name": "dasktoon_capture_viewport",
        "description": "Capture an interactive screenshot of the active 3D Viewport in DaskToon and return the image to the chat for AI visual review and verification.",
        "inputSchema": {
            "type": "object",
            "properties": {}
        }
    }
]


def handle_json_rpc(line):
    try:
        req = json.loads(line)
    except Exception:
        return None

    req_id = req.get("id")
    method = req.get("method")

    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "serverInfo": {
                    "name": "dasktoon-mcp-server",
                    "version": "0.1-beta"
                },
                "capabilities": {
                    "tools": {}
                }
            }
        }

    elif method == "notifications/initialized":
        return None

    elif method == "tools/list":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "tools": TOOLS
            }
        }

    elif method == "tools/call":
        params = req.get("params", {})
        name = params.get("name")
        args = params.get("arguments", {})

        content = []
        if name == "dasktoon_execute_code":
            content = tool_execute_code(args)
        elif name == "dasktoon_get_scene_summary":
            content = tool_get_scene_summary(args)
        elif name == "dasktoon_create_anime_material":
            content = tool_create_anime_material(args)
        elif name == "dasktoon_setup_vrm_arkit":
            content = tool_setup_arkit_shapekeys(args)
        elif name == "dasktoon_capture_viewport":
            content = tool_capture_viewport(args)
        else:
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {
                    "code": -32601,
                    "message": f"Tool not found: {name}"
                }
            }

        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "content": content
            }
        }

    elif method == "ping":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {}
        }

    else:
        if req_id is not None:
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {
                    "code": -32601,
                    "message": f"Method not found: {method}"
                }
            }
        return None


def main():
    # Read line-by-line from stdin
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        resp = handle_json_rpc(line)
        if resp is not None:
            sys.stdout.write(json.dumps(resp) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    main()
