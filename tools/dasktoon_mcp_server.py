#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 DaskToon Authors
# SPDX-License-Identifier: GPL-2.0-or-later

"""
DaskToon Native MCP (Model Context Protocol) Server
Implements standard JSON-RPC 2.0 MCP protocol over stdio for Antigravity IDE, Claude Desktop, and Cursor.
Every tool runs in a background DaskToon process. The live AI Bridge (a socket on port 9998 inside the DaskToon window)
was removed: any program on the computer could run Python inside DaskToon through it.

A background DaskToon does not see an open DaskToon window. Each tool therefore takes `blend_file` (the .blend to open;
a new empty scene when left out) and, when it changes something, `save_as`: the result is saved there, a NEW path. The
opened file is never written, and every answer says which file was read and where (if anywhere) the change was kept,
so an assistant cannot mistake a change made in a throw-away scene for a change to the user's scene.
"""

import ast
import json
import os
import subprocess
import sys
import tempfile

# The Visual Studio 2026 build; the old vc17 tree no longer builds. DASKTOON_EXE in the environment overrides it.
DASKTOON_EXE = os.environ.get("DASKTOON_EXE", r"D:\build_windows_x64_vc18_Release\bin\Release\DaskToon.exe")
TIMEOUT = 600  # seconds: opening a large character file alone can take a minute

NOT_SAVED = "not saved: the change was made in a background copy and thrown away; pass save_as to keep it"

WRAPPER = """
import io, json, os, sys, traceback
import bpy
_capture = io.StringIO()
_old_stdout = sys.stdout
sys.stdout = _capture
_error = None
_result = None
_globals = {"bpy": bpy, "context": bpy.context, "data": bpy.data, "ops": bpy.ops, "__name__": "__dasktoon_mcp__"}
_save_as = __MCP_SAVE_AS__
try:
    _code = __MCP_CODE__
    try:
        _result = eval(compile(_code, "<mcp>", "eval"), _globals)
    except SyntaxError:
        exec(compile(_code, "<mcp>", "exec"), _globals)
        _result = _globals.get("result")
except Exception:
    _error = traceback.format_exc()
finally:
    sys.stdout = _old_stdout
_saved_to = None
if _save_as and not _error:
    try:
        bpy.ops.wm.save_as_mainfile(filepath=_save_as)  # remaps relative image paths to the new place
        _saved_to = _save_as if os.path.isfile(_save_as) else None
    except Exception:
        _error = traceback.format_exc()
print("__DASKTOON_JSON_START__" + json.dumps({
    "status": "error" if _error else "ok",
    "stdout": _capture.getvalue(),
    "stderr": _error or "",
    "result": repr(_result) if _result is not None else None,
    "saved_to": _saved_to,
}) + "__DASKTOON_JSON_END__")
"""


def same_path(a, b):
    return os.path.normcase(os.path.abspath(a)) == os.path.normcase(os.path.abspath(b))


def run_headless_code(code_str, blend_file=None, save_as=None):
    """Run `code_str` in a background DaskToon on `blend_file` (a new empty scene when None); a single expression's
    value, or else the variable `result`, is returned. When the code ran without error and `save_as` is given, the
    scene is saved there; `save_as` must be a new path, never the opened file nor any file that already exists."""
    where = {"file": blend_file or "(new empty scene)", "saved_to": None}

    def error(message):
        return {"status": "error", "message": message, "stdout": "", "stderr": "", "result": None, **where}

    if not os.path.exists(DASKTOON_EXE):
        return error(f"DaskToon binary not found at {DASKTOON_EXE}")
    if blend_file and not os.path.isfile(blend_file):
        return error(f"no such .blend file: {blend_file}")
    if save_as:
        if blend_file and same_path(blend_file, save_as):
            return error("save_as must be a new path: the opened .blend is never overwritten")
        if os.path.exists(save_as):
            return error(f"save_as already exists: {save_as}; choose a new path")
        if not save_as.lower().endswith(".blend"):
            return error("save_as must end in .blend")

    # The code goes in last, so text in it is never taken for a placeholder.
    script = WRAPPER.replace("__MCP_SAVE_AS__", repr(save_as), 1).replace("__MCP_CODE__", repr(code_str), 1)
    fd, script_path = tempfile.mkstemp(prefix="dasktoon_mcp_", suffix=".py")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(script)
        command = [DASKTOON_EXE, "--background"] + ([blend_file] if blend_file else []) + ["--python", script_path]
        proc = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="replace",
                              timeout=TIMEOUT)
    except Exception as ex:
        return error(str(ex))
    finally:
        try:
            os.remove(script_path)
        except OSError:
            pass
    combined = proc.stdout + "\n" + proc.stderr
    if "__DASKTOON_JSON_START__" not in combined or "__DASKTOON_JSON_END__" not in combined:
        return error("DaskToon stopped before the code finished (exit code %d):\n%s" % (proc.returncode,
                                                                                         combined[-3000:]))
    reply = json.loads(combined.split("__DASKTOON_JSON_START__")[1].split("__DASKTOON_JSON_END__")[0])
    reply["file"] = where["file"]
    return reply


def tool_reply(raw, save_as):
    """One JSON answer for a tool: the dict the tool's code left in `result`, or the error, with the file read, where
    the change was saved, and a note when a change was not kept."""
    reply = {"status": raw.get("status", "error")}
    if raw.get("status") == "ok":
        try:
            value = ast.literal_eval(raw["result"]) if raw.get("result") else {}
        except (ValueError, SyntaxError):
            value = {"result": raw.get("result")}
        if isinstance(value, dict):
            reply.update(value)
        else:
            reply["result"] = value
    else:
        reply["message"] = raw.get("message") or raw.get("stderr") or "unknown error"
    reply["file"] = raw.get("file")
    reply["saved_to"] = raw.get("saved_to")
    if save_as is not False and not reply["saved_to"] and reply["status"] == "ok":
        reply["note"] = NOT_SAVED
    return [{"type": "text", "text": json.dumps(reply, indent=2, ensure_ascii=False)}]


# -----------------------------------------------------------------------------
# MCP Tool Handlers
# -----------------------------------------------------------------------------

def tool_execute_code(args):
    resp = run_headless_code(args.get("code", ""), args.get("blend_file"), args.get("save_as"))
    text = f"[Headless CLI] Status: {resp.get('status', 'error')}\n"
    text += f"File: {resp.get('file')}\nSaved to: {resp.get('saved_to') or '(' + NOT_SAVED + ')'}\n"
    if resp.get("message"):
        text += f"\n--- Error ---\n{resp['message']}\n"
    if resp.get("stdout"):
        text += f"\n--- Standard Output ---\n{resp['stdout']}\n"
    if resp.get("result") and resp["result"] != "None":
        text += f"\n--- Result ---\n{resp['result']}\n"
    if resp.get("stderr"):
        text += f"\n--- Errors ---\n{resp['stderr']}\n"
    return [{"type": "text", "text": text.strip()}]


def tool_get_scene_summary(args):
    py_code = """
scene = bpy.context.scene
objects = [{"name": ob.name, "type": ob.type, "location": list(ob.location),
            "materials": [m.name for m in ob.data.materials if m] if hasattr(ob.data, 'materials') else []}
           for ob in scene.objects]
result = {
    "scene_name": scene.name,
    "render_engine": scene.render.engine,
    "frame_current": scene.frame_current,
    "frame_start": scene.frame_start,
    "frame_end": scene.frame_end,
    "active_object": bpy.context.active_object.name if bpy.context.active_object else None,
    "objects_count": len(objects),
    "objects": objects[:50],
    "materials": [m.name for m in bpy.data.materials][:50],
}
"""
    return tool_reply(run_headless_code(py_code, args.get("blend_file")), save_as=False)


def tool_create_anime_material(args):
    payload = {
        "name": args.get("name", "Anime_Character_Mat"),
        "base_color": args.get("base_color", [0.6, 0.6, 0.6, 1.0]),
        "shadow_color": args.get("shadow_color", [0.35, 0.35, 0.35, 1.0]),
        "rim_color": args.get("rim_color", [1.0, 0.95, 0.85, 1.0]),
        "rim_factor": args.get("rim_intensity", 0.6),
        "target_object": args.get("target_object", None),
    }
    py_code = f"""
payload = {payload!r}
target = None
if payload["target_object"]:
    target = bpy.data.objects.get(payload["target_object"])
    if target is None or not hasattr(target.data, "materials"):
        raise ValueError("no object with materials named %r" % payload["target_object"])
mat = bpy.data.materials.new(payload["name"])
mat.use_nodes = True
nodes = mat.node_tree.nodes
nodes.clear()
out = nodes.new('ShaderNodeOutputMaterial')
out.location = (400, 0)
bsdf = nodes.new('ShaderNodeAnimeCharacter')
bsdf.location = (0, 0)
bsdf.use_rim = True  # the Rim inputs are unavailable (and not found by name) until the Rim module is on
bsdf.inputs["Base Color"].default_value = payload["base_color"]
bsdf.inputs["Shadow Color"].default_value = payload["shadow_color"]
bsdf.inputs["Rim Color"].default_value = payload["rim_color"]
bsdf.inputs["Rim Factor"].default_value = payload["rim_factor"]
mat.node_tree.links.new(bsdf.outputs['BSDF'], out.inputs['Surface'])
if target is not None:
    target.data.materials.append(mat)
result = {{"material_name": mat.name, "node_type": "ShaderNodeAnimeCharacter (Anime BSDF)",
          "assigned_to": target.name if target is not None else None}}
"""
    save_as = args.get("save_as")
    return tool_reply(run_headless_code(py_code, args.get("blend_file"), save_as), save_as)


def tool_setup_arkit_shapekeys(args):
    obj_name = args.get("target_object", None)
    py_code = f"""
from bl_ui.dasktoon_shape_key_manager import ARKIT_52_ALL_NAMES, synthesize_arkit52
target_name = {obj_name!r}
obj = bpy.data.objects.get(target_name) if target_name else bpy.context.active_object
if not obj or obj.type != 'MESH':
    raise ValueError("no mesh named %r" % target_name if target_name else "no active mesh; pass target_object")
if not obj.data.shape_keys:
    raise ValueError("%s has no shape keys: the 52 ARKit keys are built from its VRM / VRoid / MMD keys" % obj.name)
built = synthesize_arkit52(obj)
names = set(obj.data.shape_keys.key_blocks.keys())
result = {{
    "object": obj.name,
    "built_now": built,
    "arkit_keys_present": sum(1 for n in ARKIT_52_ALL_NAMES if n in names),
    "arkit_keys_missing": [n for n in ARKIT_52_ALL_NAMES if n not in names],
}}
"""
    save_as = args.get("save_as")
    return tool_reply(run_headless_code(py_code, args.get("blend_file"), save_as), save_as)


# -----------------------------------------------------------------------------
# MCP Server Capabilities & Tools Catalog
# -----------------------------------------------------------------------------

BLEND_FILE = {"type": "string", "description": "Absolute path of the .blend to open. Left out: a new EMPTY scene "
                                               "(a background DaskToon never sees a DaskToon window that is open)."}
SAVE_AS = {"type": "string", "description": "Absolute path of a NEW .blend to save the result to. Left out: the "
                                            "change is thrown away. Never the opened file, never an existing file."}

TOOLS = [
    {
        "name": "dasktoon_execute_code",
        "description": "Execute Python code in a background DaskToon process on blend_file (bpy, context, data and ops "
                       "are available). A single expression's value is returned, otherwise set a variable named "
                       "result. The answer names the file read and where the result was saved, if anywhere.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "code": {"type": "string", "description": "Python code to execute inside DaskToon"},
                "blend_file": BLEND_FILE,
                "save_as": SAVE_AS,
            },
            "required": ["code"]
        }
    },
    {
        "name": "dasktoon_get_scene_summary",
        "description": "Summary of the scene in blend_file: active object, objects, materials, frame range, render "
                       "engine. Without blend_file it describes a new empty scene, not a DaskToon window.",
        "inputSchema": {
            "type": "object",
            "properties": {"blend_file": BLEND_FILE}
        }
    },
    {
        "name": "dasktoon_create_anime_material",
        "description": "Create a DaskToon Anime BSDF (ShaderNodeAnimeCharacter) cel material in blend_file, optionally "
                       "on target_object, and save the result to save_as.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Name for the material"},
                "base_color": {"type": "array", "items": {"type": "number"}, "description": "RGBA base lit color [r, g, b, a]"},
                "shadow_color": {"type": "array", "items": {"type": "number"}, "description": "RGBA shadow color [r, g, b, a]"},
                "rim_color": {"type": "array", "items": {"type": "number"}, "description": "RGBA rim light color [r, g, b, a]"},
                "rim_intensity": {"type": "number", "description": "Rim light strength, the node's Rim Factor (0.0 to 1.0)"},
                "target_object": {"type": "string", "description": "Optional name of mesh object to assign the material to"},
                "blend_file": BLEND_FILE,
                "save_as": SAVE_AS,
            }
        }
    },
    {
        "name": "dasktoon_setup_vrm_arkit",
        "description": "Build the 52 ARKit face tracking shape keys of a mesh in blend_file from its VRM / VRoid / MMD "
                       "shape keys (DaskToon's Synthesize ARKit 52), and save the result to save_as. Reports how many "
                       "of the 52 exist and which are missing.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "target_object": {"type": "string", "description": "Name of the face mesh. Defaults to the active object."},
                "blend_file": BLEND_FILE,
                "save_as": SAVE_AS,
            }
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
