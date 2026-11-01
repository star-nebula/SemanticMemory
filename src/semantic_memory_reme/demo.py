"""Self-contained first-run demonstration for SemanticMemory."""

from __future__ import annotations

import tempfile
from datetime import date
from pathlib import Path
from typing import Any

import yaml

from . import claims
from . import paths
from . import tasks

SOURCE_TEXT = "I prefer concise explanations in English.\n"


def run_demo() -> dict[str, Any]:
    today = date.today().isoformat()
    with tempfile.TemporaryDirectory(prefix="semantic-memory-demo-") as temp:
        root = paths.init_workspace(Path(temp) / ".semantic-memory")
        source = root / "sources" / "profile.md"
        source.parent.mkdir(parents=True, exist_ok=True)
        source.write_text(SOURCE_TEXT, encoding="utf-8", newline="\n")

        claim_data = {
            "schema": claims.SCHEMA,
            "type": claims.CLAIM_TYPE,
            "id": "pref-demo-concise",
            "title": "Prefer concise explanations",
            "kind": "preference",
            "subject": "person:demo-user",
            "predicate": "preferred_explanation_style",
            "object": "concise",
            "scope": "global",
            "cardinality": "single",
            "status": "active",
            "confidence": 0.9,
            "human_review": "not_required",
            "review_policy": "agent",
            "checked_at": today,
            "check_scope": "Synthetic demo source checked",
            "valid_from": today,
            "valid_to": None,
            "observed_at": f"{today}T12:00:00+08:00",
            "updated": today,
            "supersedes": [],
            "superseded_by": None,
            "contradicts": [],
            "tags": ["preference", "demo"],
            "sources": [
                {
                    "path": "sources/profile.md",
                    "quote": "I prefer concise explanations in English.",
                }
            ],
            "reme_ref": None,
        }
        frontmatter = yaml.safe_dump(
            claim_data,
            allow_unicode=True,
            sort_keys=False,
            default_flow_style=False,
            width=120,
        ).rstrip()
        candidate = root / "inbox" / "pref-demo-concise.md"
        candidate.write_text(
            f"---\n{frontmatter}\n---\n\n# Prefer concise explanations\n",
            encoding="utf-8",
            newline="\n",
        )

        claim = claims.add_claim(root, candidate)
        task = tasks.add_task(
            root,
            project="demo",
            title="Use the current preference",
            source="sources/profile.md",
            source_quote="I prefer concise explanations in English.",
            claim_ref=claim["id"],
        )
        search = claims.search_claims(root, "concise", limit=1)

    if not search:
        raise claims.ClaimError("demo claim was not searchable")

    return {
        "temporary": True,
        "claim": claim,
        "task": task,
        "search": search,
        "next": "Run `semantic-memory init --root .semantic-memory` to create a private workspace.",
    }


def print_demo(payload: dict[str, Any]) -> None:
    claim = payload["claim"]
    task = payload["task"]
    hit = payload["search"][0]
    print("SemanticMemory demo (temporary workspace)")
    print(f"Current claim: {claim['id']}  {claim['title']}")
    print(f"Source quote: {hit['sources'][0]['quote']}")
    print(f"Related task: {task['id']}  {task['title']}")
    print(f"Search hit: {hit['id']}  score={hit['score']}")
    print(payload["next"])
