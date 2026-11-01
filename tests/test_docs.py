#!/usr/bin/env python3
"""Documentation and release metadata consistency tests."""

from __future__ import annotations

import json
import re
import tomllib
import unittest
from pathlib import Path

from semantic_memory_reme import __version__
from semantic_memory_reme import mcp


REPO_ROOT = Path(__file__).resolve().parents[1]
MARKDOWN_FILES = [
    REPO_ROOT / "README.md",
    REPO_ROOT / "README_ZH.md",
    REPO_ROOT / "CONTRIBUTING.md",
    REPO_ROOT / "SECURITY.md",
    REPO_ROOT / "CHANGELOG.md",
    *sorted((REPO_ROOT / "docs").rglob("*.md")),
    *sorted((REPO_ROOT / "schema").glob("*.md")),
]
RELATIVE_LINK = re.compile(r"\[[^\]]+\]\(([^)]+)\)")


class DocumentationTests(unittest.TestCase):
    def test_relative_markdown_links_exist(self) -> None:
        missing: list[str] = []
        for document in MARKDOWN_FILES:
            text = document.read_text(encoding="utf-8")
            for raw_target in RELATIVE_LINK.findall(text):
                target = raw_target.strip().split("#", 1)[0]
                if not target or "://" in target or target.startswith(("mailto:", "#")):
                    continue
                candidate = (document.parent / target).resolve()
                if not candidate.exists():
                    missing.append(f"{document.relative_to(REPO_ROOT)} -> {raw_target}")
        self.assertEqual(missing, [])

    def test_json_schema_files_are_valid_json(self) -> None:
        for schema in sorted((REPO_ROOT / "schema").glob("*.schema.json")):
            with self.subTest(schema=schema.name):
                payload = json.loads(schema.read_text(encoding="utf-8"))
                self.assertEqual(payload["type"], "object")

    def test_release_versions_match(self) -> None:
        project = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
        self.assertEqual(project["project"]["version"], __version__)
        self.assertEqual(mcp.SERVER_VERSION, __version__)


if __name__ == "__main__":
    unittest.main(verbosity=2)
