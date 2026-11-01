#!/usr/bin/env python3
"""Tests for the SemanticMemory task store."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from semantic_memory_reme import tasks as tm


class TaskMemoryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name) / "SemanticMemory"
        (self.root / "tasks" / "open").mkdir(parents=True)
        (self.root / "tasks" / "done").mkdir(parents=True)
        (self.root / "source.md").write_text("demo source\n", encoding="utf-8")

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_add_list_and_complete(self) -> None:
        task = tm.add_task(self.root, "demo", "Do the thing", source="source.md")
        self.assertEqual(task["status"], "open")
        self.assertEqual([item["id"] for item in tm.list_tasks(self.root)], [task["id"]])
        path = self.root / "tasks" / "open" / (task["id"] + ".md")
        text = path.read_text(encoding="utf-8")
        self.assertNotIn("_body", text)
        self.assertNotIn("_path", text)

        completed = tm.complete_task(self.root, task["id"], note="finished")
        self.assertEqual(completed["status"], "done")
        self.assertFalse(path.exists())
        done_path = self.root / "tasks" / "done" / (task["id"] + ".md")
        self.assertTrue(done_path.is_file())
        self.assertIn("## Completion", done_path.read_text(encoding="utf-8"))
        self.assertEqual(tm.list_tasks(self.root), [])
        self.assertEqual(len(tm.list_tasks(self.root, include_done=True)), 1)

    def test_blocked_task_is_hidden_by_default(self) -> None:
        task = tm.add_task(self.root, "demo", "Paused task")
        path = self.root / "tasks" / "open" / (task["id"] + ".md")
        text = path.read_text(encoding="utf-8").replace("status: open", "status: blocked")
        path.write_text(text, encoding="utf-8")
        self.assertEqual(tm.list_tasks(self.root), [])
        self.assertEqual(len(tm.list_tasks(self.root, include_blocked=True)), 1)

    def test_task_claim_ref_roundtrips(self) -> None:
        task = tm.add_task(self.root, "demo", "Linked task", claim_ref="pref-trace-demo")
        self.assertEqual(task["claim_ref"], "pref-trace-demo")
        self.assertEqual(tm.list_tasks(self.root)[0]["claim_ref"], "pref-trace-demo")
        tm.complete_task(self.root, task["id"], note="done")
        done = self.root / "tasks" / "done" / (task["id"] + ".md")
        self.assertIn("claim_ref: pref-trace-demo", done.read_text(encoding="utf-8"))

    def test_task_source_quote_roundtrips(self) -> None:
        task = tm.add_task(
            self.root,
            "demo",
            "Evidence-linked task",
            source="source.md",
            source_quote="demo source",
        )
        self.assertEqual(task["source_quote"], "demo source")
        errors, warnings = tm.validate_tasks(self.root)
        self.assertEqual(errors, [])
        self.assertEqual(warnings, [])

    def test_duplicate_task_is_rejected(self) -> None:
        tm.add_task(self.root, "demo", "Same task")
        with self.assertRaises(tm.TaskError):
            tm.add_task(self.root, "demo", "Same task")

    def test_rebuild_returns_counts(self) -> None:
        tm.add_task(self.root, "demo", "Visible task")
        summary = tm.rebuild(self.root)
        self.assertEqual(summary["open"], 1)
        self.assertEqual(summary["tasks"], 1)
        self.assertFalse((self.root / "tasks" / "tasks.jsonl").exists())
        self.assertFalse((self.root / "tasks" / "views" / "active.md").exists())

    def test_uri_source_is_valid_without_local_file(self) -> None:
        tm.add_task(self.root, "demo", "Follow up", source="codex://threads/example-thread")
        errors, warnings = tm.validate_tasks(self.root)
        self.assertEqual(errors, [])
        self.assertEqual(warnings, [])

    def test_missing_local_source_is_an_error(self) -> None:
        tm.add_task(self.root, "demo", "Follow up", source="missing/source.md")
        errors, warnings = tm.validate_tasks(self.root)
        self.assertEqual(warnings, [])
        self.assertEqual(len(errors), 1)
        self.assertIn("source does not exist", errors[0])

    def test_cancel_task_moves_it_out_of_active_list(self) -> None:
        task = tm.add_task(self.root, "demo", "No longer relevant")
        cancelled = tm.cancel_task(self.root, task["id"], note="old workflow retired")
        self.assertEqual(cancelled["status"], "cancelled")
        self.assertEqual(tm.list_tasks(self.root), [])
        path = self.root / "tasks" / "done" / (task["id"] + ".md")
        self.assertTrue(path.is_file())
        self.assertIn("## Cancellation", path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
