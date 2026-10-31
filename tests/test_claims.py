#!/usr/bin/env python3
"""Tests for the Markdown semantic-memory claim store."""

from __future__ import annotations

import json
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path

import yaml

from semantic_memory import claims as sm


class SemanticMemoryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.knowledge = Path(self.temp_dir.name) / "knowledge"
        self.root = self.knowledge / ".semantic-memory"
        for path in ("claims", "inbox", "sources"):
            (self.root / path).mkdir(parents=True, exist_ok=True)
        self.source = self.root / "sources" / "source.md"
        self.source.write_text("用户明确表示：以后默认用中文回复。\n", encoding="utf-8")

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def _candidate(self, **overrides):
        data = {
            "schema": sm.SCHEMA,
            "type": sm.CLAIM_TYPE,
            "id": "pref-language-zh",
            "title": "默认使用中文",
            "kind": "preference",
            "subject": "person:alice",
            "predicate": "preferred_language",
            "object": "zh-CN",
            "scope": "global",
            "cardinality": "single",
            "status": "active",
            "confidence": 0.95,
            "human_review": "pending",
            "review_policy": "human",
            "checked_at": "2026-10-29",
            "check_scope": "来源文本与路径核对；未复测运行环境",
            "valid_from": "2026-01-01",
            "valid_to": None,
            "observed_at": "2026-10-29T10:00:00+08:00",
            "updated": "2026-10-29",
            "supersedes": [],
            "superseded_by": None,
            "contradicts": [],
            "tags": ["preference", "language"],
            "sources": [
                {
                    "path": "sources/source.md",
                    "quote": "以后默认用中文回复",
                },
            ],
        }
        data.update(overrides)
        path = Path(self.temp_dir.name) / f"candidate-{data['id']}.md"
        path.write_text(
            "---\n"
            + yaml.safe_dump(data, allow_unicode=True, sort_keys=False)
            + "---\n\n# "
            + data["title"]
            + "\n",
            encoding="utf-8",
        )
        return path

    def test_add_search_and_rebuild(self) -> None:
        result = sm.add_claim(self.root, self._candidate())
        self.assertEqual(result["id"], "pref-language-zh")
        self.assertEqual(result["human_review"], "pending")
        self.assertTrue((self.root / "claims" / "preference" / "pref-language-zh.md").is_file())
        hits = sm.search_claims(self.root, "中文")
        self.assertEqual([hit["id"] for hit in hits], ["pref-language-zh"])
        self.assertFalse((self.root / "views" / "current.md").exists())
        self.assertFalse((self.root / "views" / "review-queue.md").exists())

    def test_supersede_updates_both_sides(self) -> None:
        sm.add_claim(self.root, self._candidate())
        new_path = self._candidate(
            id="pref-language-en",
            title="默认使用英文",
            object="en-US",
            supersedes=["pref-language-zh"],
            updated="2026-10-30",
        )
        sm.add_claim(self.root, new_path)
        old = sm.get_claim(self.root, "pref-language-zh")
        new = sm.get_claim(self.root, "pref-language-en")
        self.assertEqual(old["status"], "superseded")
        self.assertEqual(old["superseded_by"], "pref-language-en")
        self.assertIn("`pref-language-en`", old["_body"])
        self.assertEqual(new["status"], "active")
        self.assertEqual([hit["id"] for hit in sm.search_claims(self.root, "默认")], ["pref-language-en"])
        history = sm.search_claims(self.root, "默认", include_history=True)
        self.assertEqual({hit["id"] for hit in history}, {"pref-language-zh", "pref-language-en"})

    def test_duplicate_active_single_slot_is_rejected(self) -> None:
        sm.add_claim(self.root, self._candidate())
        duplicate = self._candidate(id="pref-language-other", object="ja-JP")
        with self.assertRaises(sm.ClaimError):
            sm.add_claim(self.root, duplicate)

    def test_source_quote_mismatch_is_rejected(self) -> None:
        bad = self._candidate(
            sources=[{"path": "sources/source.md", "quote": "这句话不存在"}],
        )
        with self.assertRaises(sm.ClaimError):
            sm.add_claim(self.root, bad)

    def test_validate_and_transition_expired(self) -> None:
        sm.add_claim(self.root, self._candidate())
        sm.transition_claim(self.root, "pref-language-zh", status="expired", note="测试过期")
        claim = sm.get_claim(self.root, "pref-language-zh")
        self.assertEqual(claim["status"], "expired")
        self.assertTrue(claim["valid_to"])
        self.assertEqual(sm.search_claims(self.root, "中文"), [])

    def test_invalid_lifecycle_transition_is_rejected(self) -> None:
        sm.add_claim(self.root, self._candidate(status="pending"))
        with self.assertRaises(sm.ClaimError):
            sm.transition_claim(self.root, "pref-language-zh", status="expired")

    def test_add_archives_inbox_candidate_and_json_is_serializable(self) -> None:
        candidate = self._candidate()
        inbox_candidate = self.root / "inbox" / candidate.name
        inbox_candidate.write_bytes(candidate.read_bytes())

        result = sm.add_claim(self.root, inbox_candidate)

        self.assertEqual(result["path"], "claims/preference/pref-language-zh.md")
        self.assertFalse(inbox_candidate.exists())
        processed = self.root / result["candidate_archived_to"]
        self.assertTrue(processed.is_file())
        self.assertFalse((self.root / "inbox" / "processed").exists())
        json.dumps(result, ensure_ascii=False)

    def test_claim_detail_contains_body(self) -> None:
        sm.add_claim(self.root, self._candidate())
        detail = sm.claim_detail(sm.get_claim(self.root, "pref-language-zh"))
        self.assertIn("# 默认使用中文", detail["body"])

    def test_review_updates_human_review_without_accepting_automatically(self) -> None:
        sm.add_claim(self.root, self._candidate())
        self.assertEqual(sm.get_claim(self.root, "pref-language-zh")["human_review"], "pending")

        result = sm.review_claim(
            self.root,
            "pref-language-zh",
            review_status="accepted",
            note="用户确认",
        )

        self.assertEqual(result["human_review"], "accepted")
        claim = sm.get_claim(self.root, "pref-language-zh")
        self.assertIn("人工评审", claim["_body"])

    def test_review_many_updates_all_claims_atomically(self) -> None:
        sm.add_claim(self.root, self._candidate())
        sm.add_claim(
            self.root,
            self._candidate(
                id="pref-editor-vim",
                title="使用 Vim",
                predicate="preferred_editor",
                object="vim",
            ),
        )
        result = sm.review_claims(
            self.root,
            ["pref-language-zh", "pref-editor-vim"],
            review_status="accepted",
            note="批量确认",
        )
        self.assertEqual(result["updated"], 2)
        for claim_id in ("pref-language-zh", "pref-editor-vim"):
            claim = sm.get_claim(self.root, claim_id)
            self.assertEqual(claim["human_review"], "accepted")
            self.assertIn("批量确认", claim["_body"])

    def test_set_validity_updates_expiry(self) -> None:
        sm.add_claim(
            self.root,
            self._candidate(
                id="project-demo-current-state",
                kind="fact",
                subject="project:demo",
                predicate="status_snapshot",
                object="running",
            ),
        )
        errors, warnings = sm.validate_claims(self.root, sm.load_claims(self.root)[0])
        self.assertEqual(errors, [])
        self.assertEqual(warnings, [])

        result = sm.set_validity(
            self.root,
            "project-demo-current-state",
            valid_to="2099-12-31",
            note="测试有效期更新",
        )

        self.assertEqual(result["valid_to"], "2099-12-31")

    def test_inbox_source_warning_is_scoped(self) -> None:
        inbox = self.root / "inbox" / "2026-10-31.md"
        inbox.write_text("周六日不发消息\n", encoding="utf-8")
        inbox_source = [{"path": str(inbox), "quote": "周六日不发消息"}]

        sm.add_claim(self.root, self._candidate(id="pref-weekend", predicate="weekend_contact", sources=inbox_source))
        errors, warnings = sm.validate_claims(self.root, sm.load_claims(self.root)[0])
        self.assertEqual(errors, [])
        self.assertEqual(warnings, [])

        sm.add_claim(
            self.root,
            self._candidate(
                id="rule-inbox-only",
                kind="rule",
                subject="knowledge:rules",
                predicate="inbox_only_rule",
                sources=inbox_source,
            ),
        )
        errors, warnings = sm.validate_claims(self.root, sm.load_claims(self.root)[0])
        self.assertEqual(errors, [])
        self.assertTrue(any("inbox" in warning for warning in warnings))

        sm.add_claim(
            self.root,
            self._candidate(
                id="rule-with-original",
                kind="rule",
                subject="knowledge:rules",
                predicate="with_original",
                sources=inbox_source + [{"path": "sources/source.md", "quote": "以后默认用中文回复"}],
            ),
        )
        errors, warnings = sm.validate_claims(self.root, sm.load_claims(self.root)[0])
        self.assertEqual(errors, [])
        self.assertFalse(any("rule-with-original" in warning and "inbox" in warning for warning in warnings))

    def test_trace_and_changes_include_reme_ref(self) -> None:
        sm.add_claim(
            self.root,
            self._candidate(
                id="pref-trace-demo",
                predicate="trace_demo",
                reme_ref="reme/session/demo.jsonl",
            ),
        )
        claim = sm.get_claim(self.root, "pref-trace-demo")
        self.assertEqual(claim.get("reme_ref"), "reme/session/demo.jsonl")

        traced = sm.trace_claim(self.root, "pref-trace-demo")
        self.assertEqual(traced["claim"]["id"], "pref-trace-demo")
        self.assertEqual(traced["reme_ref"], "reme/session/demo.jsonl")
        self.assertEqual(traced["supersede_chain"][0]["id"], "pref-trace-demo")

        changed = sm.changes_since(self.root, "2026-01-01")
        self.assertIn("pref-trace-demo", {item["id"] for item in changed["claims"]})

    def test_maintenance_reports_expiring_and_stale_claims(self) -> None:
        future = (date.today() + timedelta(days=2)).isoformat()
        sm.add_claim(
            self.root,
            self._candidate(
                id="project-demo-current-state",
                kind="fact",
                subject="project:demo",
                predicate="status_snapshot",
                object="running",
                review_policy="agent",
                valid_to=future,
            ),
        )
        sm.add_claim(
            self.root,
            self._candidate(
                id="project-demo-overview",
                kind="fact",
                subject="project:demo",
                predicate="overview",
                object="stable project overview",
                review_policy="auto",
                checked_at="2025-01-01",
                valid_to="2099-12-31",
            ),
        )

        report = sm.maintenance_report(self.root, within_days=7)

        self.assertEqual(report["expiring"][0]["id"], "project-demo-current-state")
        self.assertIn("project-demo-overview", {item["id"] for item in report["stale"]})
        self.assertEqual(report["human_review_pending"], [])

    def test_review_queue_is_not_generated(self) -> None:
        sm.add_claim(self.root, self._candidate())
        sm.add_claim(
            self.root,
            self._candidate(
                id="project-demo-overview",
                kind="fact",
                subject="project:demo",
                predicate="overview",
                object="stable project overview",
                review_policy="auto",
            ),
        )
        self.assertFalse((self.root / "views" / "review-queue.md").exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)
