# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""The MCP server for AI assistants (tools/dasktoon_mcp_server.py) runs every tool in a background DaskToon and never
opens a socket: the AI Bridge it used to reach on port 9998 was removed."""

import hashlib
import importlib.util
import json
import os
import shutil
import socket
import sys
import tempfile
import unittest
from unittest import mock

import bpy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dasktoon_test_utils as tu  # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_spec = importlib.util.spec_from_file_location("dasktoon_mcp_server",
                                               os.path.join(REPO, "tools", "dasktoon_mcp_server.py"))
mcp = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(mcp)


def call(method, params=None):
    return mcp.handle_json_rpc(json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params or {}}))


class McpServerTest(unittest.TestCase):
    def test_no_tool_needs_the_removed_bridge(self):
        names = [tool["name"] for tool in call("tools/list")["result"]["tools"]]
        self.assertNotIn("dasktoon_capture_viewport", names)
        self.assertIn("dasktoon_execute_code", names)

    @unittest.skipUnless(os.path.exists(mcp.DASKTOON_EXE), "no DaskToon build at the MCP server's DASKTOON_EXE")
    def test_execute_code_runs_headless_without_opening_a_socket(self):
        with mock.patch.object(socket, "socket", side_effect=AssertionError("the MCP server opened a socket")) as opened:
            reply = call("tools/call", {"name": "dasktoon_execute_code", "arguments": {"code": "6 * 7"}})
        self.assertEqual(opened.call_count, 0)
        text = reply["result"]["content"][0]["text"]
        self.assertIn("[Headless CLI] Status: ok", text)
        self.assertIn("42", text)

    def test_every_tool_takes_the_file_to_work_on(self):
        for tool in call("tools/list")["result"]["tools"]:
            props = tool["inputSchema"]["properties"]
            self.assertIn("blend_file", props, tool["name"])
            if tool["name"] != "dasktoon_get_scene_summary":
                self.assertIn("save_as", props, tool["name"])


def md5(path):
    with open(path, "rb") as f:
        return hashlib.md5(f.read()).hexdigest()


def tool_json(tool, **arguments):
    return json.loads(call("tools/call", {"name": tool, "arguments": arguments})["result"]["content"][0]["text"])


@unittest.skipUnless(os.path.exists(mcp.DASKTOON_EXE), "no DaskToon build at the MCP server's DASKTOON_EXE")
class McpFileToolsTest(unittest.TestCase):
    """The tools work on the .blend they are given and keep a change only in a NEW file (save_as). They used to run on
    an empty scene that was thrown away and still answer "ok", so an assistant believed it had changed the user's
    scene; the test above skipped them all while DASKTOON_EXE pointed at the removed vc17 build."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="dasktoon_mcp_")
        bpy.ops.wm.read_factory_settings(use_empty=True)
        mesh = bpy.data.meshes.new("FaceMesh")
        mesh.from_pydata([(-1, 0, 0), (-1, 0, 1), (1, 0, 1), (1, 0, 0)], [], [(0, 1, 2, 3)])
        face = bpy.data.objects.new("Face", mesh)
        bpy.context.scene.collection.objects.link(face)
        face.shape_key_add(name="Basis")
        blink = face.shape_key_add(name="Fcl_EYE_Close")  # a VRoid key: both eyes close
        for point in blink.data:
            point.co.z -= 0.2
        cls.src = os.path.join(cls.tmp, "src.blend")
        bpy.ops.wm.save_as_mainfile(filepath=cls.src)
        cls.src_md5 = md5(cls.src)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def tearDown(self):
        self.assertEqual(md5(self.src), self.src_md5, "the opened file was changed")

    def open(self, path):
        bpy.ops.wm.open_mainfile(filepath=path)
        return bpy.data.objects["Face"]

    def test_summary_reads_the_given_file(self):
        reply = tool_json("dasktoon_get_scene_summary", blend_file=self.src)
        self.assertEqual(reply["status"], "ok", reply)
        self.assertEqual(reply["file"], self.src)
        self.assertIn("Face", [ob["name"] for ob in reply["objects"]])

    def test_execute_code_sees_the_given_file(self):
        reply = call("tools/call", {"name": "dasktoon_execute_code",
                                    "arguments": {"code": "sorted(o.name for o in bpy.data.objects)",
                                                  "blend_file": self.src}})
        self.assertIn("['Face']", reply["result"]["content"][0]["text"])

    def test_material_is_kept_in_the_new_file(self):
        out = os.path.join(self.tmp, "material.blend")
        reply = tool_json("dasktoon_create_anime_material", name="Skin", target_object="Face", rim_intensity=0.3,
                          blend_file=self.src, save_as=out)
        self.assertEqual(reply["status"], "ok", reply)
        self.assertEqual(reply["saved_to"], out)
        face = self.open(out)
        mat = face.data.materials[0]
        self.assertEqual(mat.name, "Skin")
        node = next(n for n in mat.node_tree.nodes if n.bl_idname == "ShaderNodeAnimeCharacter")
        self.assertAlmostEqual(node.inputs["Rim Factor"].default_value, 0.3, places=5)  # the rim strength arrives

    def test_a_change_without_save_as_says_it_was_not_kept(self):
        reply = tool_json("dasktoon_create_anime_material", name="Skin", blend_file=self.src)
        self.assertIsNone(reply["saved_to"])
        self.assertIn("not saved", reply["note"])

    def test_save_as_never_overwrites_the_opened_file(self):
        reply = tool_json("dasktoon_create_anime_material", name="Skin", blend_file=self.src, save_as=self.src)
        self.assertEqual(reply["status"], "error", reply)

    def test_a_missing_file_is_an_error(self):
        reply = tool_json("dasktoon_get_scene_summary", blend_file=os.path.join(self.tmp, "nope.blend"))
        self.assertEqual(reply["status"], "error", reply)

    def test_arkit_keys_are_built_from_the_face_keys(self):
        out = os.path.join(self.tmp, "arkit.blend")
        reply = tool_json("dasktoon_setup_vrm_arkit", target_object="Face", blend_file=self.src, save_as=out)
        self.assertEqual(reply["status"], "ok", reply)
        keys = self.open(out).data.shape_keys.key_blocks
        self.assertIn("eyeBlinkLeft", keys)
        basis = keys[0]
        moved = max((p.co - b.co).length for p, b in zip(keys["eyeBlinkLeft"].data, basis.data))
        self.assertGreater(moved, 0.01, "an empty placeholder key, not a blink")


if __name__ == "__main__":
    tu.run_tests()
