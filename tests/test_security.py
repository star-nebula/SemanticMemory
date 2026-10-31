#!/usr/bin/env python3
"""Security and release-audit tests."""

from __future__ import annotations

import json
import secrets
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

from semantic_memory import claims
from semantic_memory import mcp
from semantic_memory.errors import WorkspaceError
from semantic_memory import paths


REPO_ROOT = Path(__file__).resolve().parents[1]
AUDIT = REPO_ROOT / "scripts" / "audit_release.py"


class SecurityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_workspace_path_must_be_a_directory(self) -> None:
        file_path = self.root / "not-a-directory"
        file_path.write_text("x", encoding="utf-8")
        with self.assertRaises(WorkspaceError):
            paths.init_workspace(file_path)

    def test_candidate_outside_inbox_is_rejected(self) -> None:
        workspace = paths.init_workspace(self.root / "workspace")
        outside = workspace / "claims" / "bad.md"
        outside.write_text("bad", encoding="utf-8")
        with self.assertRaises(ValueError):
            mcp.candidate_path(workspace, str(outside))

    def test_absolute_source_paths_are_supported_locally(self) -> None:
        workspace = paths.init_workspace(self.root / "workspace")
        source = self.root / "private-source.md"
        source.write_text("A private fact.\n", encoding="utf-8")
        self.assertEqual(claims.resolve_source_path(workspace, str(source)), source.resolve())

    def test_release_audit_accepts_clean_content(self) -> None:
        fixture = self.root / "clean"
        fixture.mkdir()
        (fixture / "README.md").write_text("No private data here.\n", encoding="utf-8")

        result = subprocess.run(
            [sys.executable, str(AUDIT), str(fixture), "--json"],
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertTrue(json.loads(result.stdout)["ok"])

    def test_release_audit_rejects_machine_path_without_echoing_it(self) -> None:
        fixture = self.root / "dirty"
        fixture.mkdir()
        drive = "C:"
        separator = "\\"
        private_path = drive + separator + "Users" + separator + "someone" + separator + "notes.md"
        (fixture / "README.md").write_text(f"Local path: {private_path}\n", encoding="utf-8")

        result = subprocess.run(
            [sys.executable, str(AUDIT), str(fixture), "--json"],
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )

        self.assertEqual(result.returncode, 1)
        payload = json.loads(result.stdout)
        self.assertFalse(payload["ok"])
        self.assertEqual(payload["findings"][0]["reason"], "absolute local path")
        self.assertNotIn(private_path, result.stdout)

    @staticmethod
    def _synthetic_uuid7() -> str:
        """Build a UUIDv7 at runtime so no real-looking ID lives in this file."""
        timestamp = f"{int(time.time() * 1000):012x}"
        return (
            f"{timestamp[:8]}-{timestamp[8:12]}-"
            f"7{secrets.token_hex(2)[:3]}-"
            f"{secrets.choice('89ab')}{secrets.token_hex(2)[:3]}-"
            f"{secrets.token_hex(6)}"
        )

    def test_release_audit_rejects_session_identifier_without_echoing_it(self) -> None:
        fixture = self.root / "session"
        fixture.mkdir()
        session_id = self._synthetic_uuid7()
        (fixture / "README.md").write_text(
            f"thread: codex://threads/{session_id}\nid: {session_id}\n",
            encoding="utf-8",
        )

        result = subprocess.run(
            [sys.executable, str(AUDIT), str(fixture), "--json"],
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )

        self.assertEqual(result.returncode, 1)
        payload = json.loads(result.stdout)
        self.assertFalse(payload["ok"])
        reasons = {finding["reason"] for finding in payload["findings"]}
        self.assertIn("session identifier URI", reasons)
        self.assertIn("session identifier (UUIDv7)", reasons)
        self.assertNotIn(session_id, result.stdout)


if __name__ == "__main__":
    unittest.main(verbosity=2)
