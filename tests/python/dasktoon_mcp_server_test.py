# SPDX-FileCopyrightText: 2026 DaskToon Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""The MCP server for AI assistants (tools/dasktoon_mcp_server.py) runs every tool in a background DaskToon and never
opens a socket: the AI Bridge it used to reach on port 9998 was removed."""

import importlib.util
import json
import os
import socket
import sys
import unittest
from unittest import mock

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


if __name__ == "__main__":
    tu.run_tests()
