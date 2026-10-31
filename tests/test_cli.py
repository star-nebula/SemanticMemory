#!/usr/bin/env python3
"""Integration tests for the unified SemanticMemory CLI."""

from __future__ import annotations

import contextlib
import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from semantic_memory import cli
from semantic_memory import paths


class CliTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name)
        self.root = self.base / ".semantic-memory"

    def tearDown(self) -> None:
        self.temp.cleanup()

    def run_cli(self, arguments: list[str]) -> tuple[int, str, str]:
        stdout = io.StringIO()
        stderr = io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            code = cli.main(arguments)
        return code, stdout.getvalue(), stderr.getvalue()

    def test_init_creates_expected_directories(self) -> None:
        code, output, error = self.run_cli(["init", "--root", str(self.root), "--json"])

        self.assertEqual(code, 0)
        self.assertEqual(error, "")
        self.assertTrue(json.loads(output)["ok"])
        for relative in paths.WORKSPACE_DIRECTORIES:
            self.assertTrue((self.root / relative).is_dir())
        self.assertTrue((self.root / "README.md").is_file())
        self.assertIn("*\n!.gitignore\n", (self.root / ".gitignore").read_text(encoding="utf-8"))

    def test_root_environment_variable_is_supported(self) -> None:
        self.run_cli(["init", "--root", str(self.root)])

        with mock.patch.dict(os.environ, {paths.ENV_ROOT: str(self.root)}):
            code, output, error = self.run_cli(["validate", "--json"])

        self.assertEqual(code, 0)
        self.assertEqual(error, "")
        self.assertEqual(json.loads(output)["claims"], 0)

    def test_missing_workspace_returns_actionable_error(self) -> None:
        code, _, error = self.run_cli(["validate", "--root", str(self.root)])

        self.assertEqual(code, 2)
        self.assertIn("semantic-memory init", error)

    def test_task_add_and_list_work_end_to_end(self) -> None:
        self.run_cli(["init", "--root", str(self.root)])

        code, output, error = self.run_cli(
            [
                "task",
                "add",
                "--root",
                str(self.root),
                "--project",
                "demo",
                "--title",
                "Ship the prototype",
                "--source-quote",
                "Ship it",
                "--json",
            ]
        )

        self.assertEqual(code, 0)
        self.assertEqual(error, "")
        added = json.loads(output)
        self.assertEqual(added["source_quote"], "Ship it")

        code, output, error = self.run_cli(
            ["task", "list", "--root", str(self.root), "--json"]
        )
        self.assertEqual(code, 0)
        self.assertEqual(error, "")
        self.assertEqual([item["id"] for item in json.loads(output)], [added["id"]])


if __name__ == "__main__":
    unittest.main(verbosity=2)
