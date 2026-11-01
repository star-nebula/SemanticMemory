#!/usr/bin/env python3
"""Tests for the dependency-free SemanticMemory MCP sidecar."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from semantic_memory_reme import claims as sm
from semantic_memory_reme import mcp


class SemanticMemoryMCPTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name) / ".semantic-memory"
        (self.root / "claims").mkdir(parents=True)
        (self.root / "inbox").mkdir(parents=True)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_initialize_tools_and_read_only_contract(self) -> None:
        init = mcp.handle_message(self.root, True, {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2024-11-05"}})
        self.assertEqual(init["result"]["serverInfo"]["name"], "SemanticMemory")
        listed = mcp.handle_message(self.root, True, {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}})
        names = {item["name"] for item in listed["result"]["tools"]}
        self.assertEqual(
            names,
            {
                "semantic_status",
                "semantic_search",
                "semantic_get",
                "semantic_trace",
                "semantic_changes",
                "semantic_validate",
                "semantic_maintenance",
                "task_list",
                "task_validate",
            },
        )
        status = mcp.handle_message(self.root, True, {"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {"name": "semantic_status", "arguments": {}}})
        self.assertFalse(status["result"]["isError"])

    def test_write_tools_are_opt_in(self) -> None:
        listed = mcp.handle_message(self.root, False, {"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}})
        names = {item["name"] for item in listed["result"]["tools"]}
        self.assertIn("semantic_add", names)
        self.assertIn("semantic_transition", names)
        self.assertIn("semantic_review", names)
        self.assertIn("semantic_set_validity", names)
        self.assertIn("task_add", names)
        self.assertIn("task_complete", names)
        self.assertIn("task_cancel", names)

    def test_add_rejects_paths_outside_inbox(self) -> None:
        outside = self.root / "claims" / "bad.md"
        outside.write_text("bad", encoding="utf-8")
        with self.assertRaises(ValueError):
            mcp.candidate_path(self.root, str(outside))

    def test_search_and_validate_do_not_write(self) -> None:
        before = {p: p.read_bytes() for p in self.root.rglob("*") if p.is_file()}
        search = mcp.handle_message(self.root, True, {"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": "semantic_search", "arguments": {"query": "x"}}})
        self.assertFalse(search["result"]["isError"])
        validate = mcp.handle_message(self.root, True, {"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {"name": "semantic_validate", "arguments": {}}})
        self.assertFalse(validate["result"]["isError"])
        maintenance = mcp.handle_message(self.root, True, {"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {"name": "semantic_maintenance", "arguments": {}}})
        self.assertFalse(maintenance["result"]["isError"])
        after = {p: p.read_bytes() for p in self.root.rglob("*") if p.is_file()}
        self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main(verbosity=2)
