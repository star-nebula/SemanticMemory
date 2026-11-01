#!/usr/bin/env python3
"""Lightweight Markdown claim store for current facts and decisions."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import sys
import tempfile
import time
from contextlib import contextmanager
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import yaml

from . import paths

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

SCHEMA = "semantic-memory/v1"
CLAIM_TYPE = "semantic-claim"
VALID_KINDS = {"fact", "preference", "decision", "procedure", "constraint", "rule"}
VALID_STATUSES = {"active", "superseded", "contested", "expired", "archived", "pending"}
VALID_REVIEW_STATUSES = {"pending", "accepted", "disputed", "not_required"}
VALID_REVIEW_POLICIES = {"auto", "agent", "human"}
INACTIVE_STATUSES = {"superseded", "expired", "archived", "pending"}
VALID_TRANSITIONS = {
    "pending": {"active", "archived"},
    "active": {"superseded", "contested", "expired", "archived"},
    "contested": {"active", "superseded", "archived"},
    "superseded": {"archived"},
    "expired": {"archived"},
    "archived": set(),
}
DEFAULT_CARDINALITY = {
    "fact": "multi",
    "preference": "single",
    "decision": "single",
    "procedure": "single",
    "constraint": "single",
    "rule": "single",
}
TEXT_SUFFIXES = {
    ".md", ".txt", ".json", ".jsonl", ".yaml", ".yml", ".csv", ".py", ".ts", ".js", ".toml", ".ini", ".cfg",
}
FRONTMATTER_ORDER = [
    "schema", "type", "id", "title", "kind", "subject", "predicate", "object", "scope",
    "cardinality", "status", "confidence", "human_review", "review_policy", "checked_at", "check_scope",
    "valid_from", "valid_to", "observed_at", "updated", "supersedes", "superseded_by",
    "contradicts", "tags", "sources",
]
ID_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{2,127}$")


class ClaimError(ValueError):
    """Raised for malformed or inconsistent semantic-memory data."""


def today_iso() -> str:
    return date.today().isoformat()


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def default_root() -> Path:
    return paths.default_root()


def normalize_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    return str(value).strip()


def normalize_list(value: Any) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise ClaimError("expected a YAML list")
    return [normalize_text(item) for item in value if normalize_text(item)]


def split_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    if not text.startswith("---\n"):
        raise ClaimError("claim must start with YAML frontmatter delimited by ---")
    end = text.find("\n---\n", 4)
    if end < 0:
        raise ClaimError("claim frontmatter is missing its closing --- delimiter")
    raw_front = text[4:end]
    body = text[end + 5 :].lstrip("\n")
    try:
        data = yaml.safe_load(raw_front) or {}
    except yaml.YAMLError as exc:
        raise ClaimError(f"invalid YAML frontmatter: {exc}") from exc
    if not isinstance(data, dict):
        raise ClaimError("claim frontmatter must be a YAML mapping")
    return data, body.rstrip() + "\n"


def normalize_source(raw: Any, index: int) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise ClaimError(f"sources[{index}] must be a mapping")
    path = normalize_text(raw.get("path"))
    quote = normalize_text(raw.get("quote"))
    if not path:
        raise ClaimError(f"sources[{index}].path is required")
    if not quote:
        raise ClaimError(f"sources[{index}].quote is required")
    out = {"path": path, "quote": quote}
    content_hash = normalize_text(raw.get("content_hash"))
    if content_hash:
        out["content_hash"] = content_hash
    return out


def normalize_claim_data(raw: dict[str, Any]) -> dict[str, Any]:
    data = dict(raw)
    if data.get("schema") != SCHEMA:
        raise ClaimError(f"schema must be {SCHEMA!r}")
    if data.get("type") != CLAIM_TYPE:
        raise ClaimError(f"type must be {CLAIM_TYPE!r}")
    claim_id = normalize_text(data.get("id")).lower()
    if not ID_RE.fullmatch(claim_id):
        raise ClaimError("id must match [a-z0-9][a-z0-9._-]{2,127}")
    kind = normalize_text(data.get("kind")).lower()
    if kind not in VALID_KINDS:
        raise ClaimError(f"kind must be one of {sorted(VALID_KINDS)}")
    status = normalize_text(data.get("status")).lower() or "pending"
    if status not in VALID_STATUSES:
        raise ClaimError(f"status must be one of {sorted(VALID_STATUSES)}")
    review_status = normalize_text(data.get("human_review")).lower() or "pending"
    if review_status not in VALID_REVIEW_STATUSES:
        raise ClaimError(f"human_review must be one of {sorted(VALID_REVIEW_STATUSES)}")
    review_policy = normalize_text(data.get("review_policy")).lower() or "agent"
    if review_policy not in VALID_REVIEW_POLICIES:
        raise ClaimError(f"review_policy must be one of {sorted(VALID_REVIEW_POLICIES)}")
    confidence_raw = data.get("confidence", 0.5)
    try:
        confidence = float(confidence_raw)
    except (TypeError, ValueError) as exc:
        raise ClaimError("confidence must be a number between 0 and 1") from exc
    if not 0.0 <= confidence <= 1.0:
        raise ClaimError("confidence must be between 0 and 1")
    sources = data.get("sources") or []
    if not isinstance(sources, list) or not sources:
        raise ClaimError("at least one source is required")
    normalized = {
        "schema": SCHEMA,
        "type": CLAIM_TYPE,
        "id": claim_id,
        "title": normalize_text(data.get("title")) or claim_id,
        "kind": kind,
        "subject": normalize_text(data.get("subject")),
        "predicate": normalize_text(data.get("predicate")),
        "object": normalize_text(data.get("object")),
        "scope": normalize_text(data.get("scope")) or "global",
        "cardinality": normalize_text(data.get("cardinality")).lower() or DEFAULT_CARDINALITY[kind],
        "status": status,
        "confidence": confidence,
        "human_review": review_status,
        "review_policy": review_policy,
        "checked_at": normalize_text(data.get("checked_at")),
        "check_scope": normalize_text(data.get("check_scope")),
        "valid_from": normalize_text(data.get("valid_from")),
        "valid_to": normalize_text(data.get("valid_to")),
        "observed_at": normalize_text(data.get("observed_at")),
        "updated": normalize_text(data.get("updated")) or today_iso(),
        "supersedes": normalize_list(data.get("supersedes")),
        "superseded_by": normalize_text(data.get("superseded_by")),
        "contradicts": normalize_list(data.get("contradicts")),
        "tags": normalize_list(data.get("tags")),
        "sources": [normalize_source(item, i) for i, item in enumerate(sources)],
    }
    if normalize_text(data.get("reme_ref")):
        normalized["reme_ref"] = normalize_text(data.get("reme_ref"))
    for required in ("subject", "predicate"):
        if not normalized[required]:
            raise ClaimError(f"{required} is required")
    if normalized["cardinality"] not in {"single", "multi"}:
        raise ClaimError("cardinality must be single or multi")
    return normalized


def parse_date(value: str, field: str) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ClaimError(f"{field} must use YYYY-MM-DD: {value!r}") from exc


def read_claim(path: Path) -> tuple[dict[str, Any], str]:
    try:
        text = path.read_text(encoding="utf-8-sig")
    except OSError as exc:
        raise ClaimError(f"cannot read {path}: {exc}") from exc
    raw, body = split_frontmatter(text)
    return normalize_claim_data(raw), body


def iter_claim_files(root: Path) -> Iterable[Path]:
    claim_root = root / "claims"
    if not claim_root.exists():
        return []
    return sorted(
        path
        for path in claim_root.rglob("*.md")
        if path.is_file() and not path.name.startswith("_") and path.name != "README.md"
    )


def load_claims(root: Path) -> tuple[dict[str, dict[str, Any]], dict[str, Path]]:
    claims: dict[str, dict[str, Any]] = {}
    paths: dict[str, Path] = {}
    for path in iter_claim_files(root):
        data, body = read_claim(path)
        claim_id = data["id"]
        if claim_id in claims:
            raise ClaimError(f"duplicate claim id {claim_id!r}: {paths[claim_id]} and {path}")
        data["_body"] = body
        data["_path"] = path
        claims[claim_id] = data
        paths[claim_id] = path
    return claims, paths


def resolve_source_path(root: Path, raw_path: str) -> Path:
    path = Path(raw_path)
    if path.is_absolute():
        return path
    return (root / path).resolve()


def verify_sources(root: Path, claim: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for index, source in enumerate(claim["sources"]):
        source_path = resolve_source_path(root, source["path"])
        if not source_path.exists():
            errors.append(f"sources[{index}] does not exist: {source_path}")
            continue
        if not source_path.is_file():
            errors.append(f"sources[{index}] is not a file: {source_path}")
            continue
        content_hash = source.get("content_hash", "")
        if content_hash:
            actual = "sha256:" + hashlib.sha256(source_path.read_bytes()).hexdigest()
            if content_hash != actual:
                errors.append(f"sources[{index}] content_hash mismatch: expected {content_hash}, got {actual}")
        if source_path.suffix.lower() in TEXT_SUFFIXES:
            try:
                text = source_path.read_text(encoding="utf-8-sig", errors="replace")
            except OSError as exc:
                errors.append(f"sources[{index}] cannot be read: {exc}")
                continue
            quote = source["quote"].strip()
            text_norm = re.sub(r"\s+", " ", text).strip()
            quote_norm = re.sub(r"\s+", " ", quote).strip()
            if quote not in text and quote_norm not in text_norm:
                errors.append(f"sources[{index}] quote not found in {source_path}")
    return errors


def expected_claim_path(root: Path, claim: dict[str, Any]) -> Path:
    return root / "claims" / claim["kind"] / f"{claim['id']}.md"


def validate_claims(root: Path, claims: dict[str, dict[str, Any]], *, check_sources: bool = True) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    active_slots: dict[tuple[str, str, str, str], list[str]] = {}
    for claim_id, claim in claims.items():
        path = Path(claim["_path"])
        expected = expected_claim_path(root, claim)
        if path.resolve() != expected.resolve():
            errors.append(f"{claim_id}: canonical path must be {expected.relative_to(root).as_posix()}")
        valid_from = parse_date(claim["valid_from"], "valid_from")
        valid_to = parse_date(claim["valid_to"], "valid_to")
        if valid_from and valid_to and valid_from > valid_to:
            errors.append(f"{claim_id}: valid_from is after valid_to")
        if claim["status"] == "active" and valid_to and valid_to < date.today():
            errors.append(f"{claim_id}: active claim has expired valid_to; transition it to expired")
        if claim["status"] == "superseded":
            if not claim["superseded_by"]:
                errors.append(f"{claim_id}: superseded claim requires superseded_by")
            elif claim["superseded_by"] not in claims:
                errors.append(f"{claim_id}: superseded_by points to missing claim {claim['superseded_by']!r}")
        elif claim["superseded_by"]:
            errors.append(f"{claim_id}: superseded_by is only valid for superseded claims")
        for old_id in claim["supersedes"]:
            if old_id not in claims:
                errors.append(f"{claim_id}: supersedes points to missing claim {old_id!r}")
                continue
            old = claims[old_id]
            if old["status"] != "superseded" or old["superseded_by"] != claim_id:
                errors.append(f"{claim_id}: supersedes/{old_id} must have reciprocal superseded_by={claim_id}")
        for other_id in claim["contradicts"]:
            if other_id not in claims:
                errors.append(f"{claim_id}: contradicts points to missing claim {other_id!r}")
            if other_id == claim_id:
                errors.append(f"{claim_id}: claim cannot contradict itself")
        if claim_id in claim["supersedes"]:
            errors.append(f"{claim_id}: claim cannot supersede itself")
        if claim["status"] == "active":
            key = (claim["subject"], claim["predicate"], claim["scope"], claim["cardinality"])
            if claim["cardinality"] == "single":
                active_slots.setdefault(key, []).append(claim_id)
            if claim["predicate"] == "current_state":
                warnings.append(f"{claim_id}: current_state is deprecated; read project state from repo/task_list")
            if claim["kind"] == "fact" and claim["predicate"] == "overview":
                warnings.append(f"{claim_id}: project overview is deprecated; read repo/AGENTS.md or task_list")
        if check_sources:
            errors.extend(f"{claim_id}: {item}" for item in verify_sources(root, claim))
            ref = str(claim.get("reme_ref", "")).strip()
            if ref and "://" not in ref and "/" in ref:
                ref_path = Path(ref) if Path(ref).is_absolute() else root / ref
                if not ref_path.exists() and not Path(ref).is_absolute():
                    fallback = root.parent / ref
                    if fallback.exists():
                        ref_path = fallback
                if not ref_path.exists():
                    warnings.append(f"{claim_id}: reme_ref does not exist: {ref_path}")
            if claim["status"] in {"active", "pending", "contested"} and claim["kind"] in {"fact", "rule", "procedure"}:
                inbox_root = (root / "inbox").resolve()
                source_paths = [
                    resolve_source_path(root, str(source.get("path", ""))).resolve()
                    for source in claim.get("sources", [])
                ]
                if source_paths and all(path.is_relative_to(inbox_root) for path in source_paths):
                    warnings.append(
                        f"{claim_id}: all sources point to SemanticMemory/inbox logs; use original evidence for factual claims"
                    )
    for key, ids in active_slots.items():
        if len(ids) > 1:
            subject, predicate, scope, _ = key
            errors.append(f"multiple active single-cardinality claims for {subject}/{predicate}/{scope}: {sorted(ids)}")
    if not claims:
        warnings.append("no claims found")
    return errors, warnings


def canonical_frontmatter(claim: dict[str, Any]) -> dict[str, Any]:
    out = {key: claim.get(key) for key in FRONTMATTER_ORDER}
    for key in ("valid_to", "superseded_by"):
        if out.get(key) == "":
            out[key] = None
    extras = sorted(
        key for key in claim
        if key not in FRONTMATTER_ORDER and not key.startswith("_")
    )
    for key in extras:
        out[key] = claim[key]
    return out


def render_claim(claim: dict[str, Any], body: str | None = None) -> str:
    front = yaml.safe_dump(
        canonical_frontmatter(claim),
        allow_unicode=True,
        sort_keys=False,
        default_flow_style=False,
        width=120,
    ).rstrip()
    body_text = (body if body is not None else claim.get("_body", "")).strip()
    if not body_text:
        body_text = f"# {claim['title']}"
    return f"---\n{front}\n---\n\n{body_text}\n"


def atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    temp_path = Path(temp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_path, path)
    finally:
        temp_path.unlink(missing_ok=True)


@contextmanager
def exclusive_lock(root: Path):
    lock_path = root / ".lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("a+b") as handle:
        handle.seek(0, os.SEEK_END)
        if handle.tell() == 0:
            handle.write(b"0")
            handle.flush()
        if os.name == "nt":
            import msvcrt
            deadline = time.monotonic() + 30
            handle.seek(0)
            while True:
                try:
                    msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
                    break
                except OSError:
                    if time.monotonic() >= deadline:
                        raise ClaimError("timed out waiting for semantic-memory lock")
                    time.sleep(0.1)
            try:
                yield
            finally:
                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def append_history(body: str, line: str) -> str:
    body = body.rstrip()
    if "## 变更记录" not in body:
        return f"{body}\n\n## 变更记录\n\n- {line}\n"
    return f"{body}\n- {line}\n"


def claim_summary(claim: dict[str, Any]) -> dict[str, Any]:
    raw_path = claim.get("_rel_path", claim.get("_path", ""))
    path = raw_path.as_posix() if isinstance(raw_path, Path) else str(raw_path)
    return {
        "id": claim["id"],
        "title": claim["title"],
        "kind": claim["kind"],
        "subject": claim["subject"],
        "predicate": claim["predicate"],
        "object": claim["object"],
        "scope": claim["scope"],
        "status": claim["status"],
        "confidence": claim["confidence"],
        "human_review": claim["human_review"],
        "review_policy": claim["review_policy"],
        "checked_at": claim["checked_at"],
        "check_scope": claim["check_scope"],
        "valid_from": claim["valid_from"],
        "valid_to": claim["valid_to"],
        "updated": claim["updated"],
        "path": path,
        "sources": claim["sources"],
        "reme_ref": claim.get("reme_ref", ""),
    }


def claim_detail(claim: dict[str, Any]) -> dict[str, Any]:
    detail = claim_summary(claim)
    detail["body"] = claim.get("_body", "").strip()
    return detail


def maintenance_report(root: Path, *, within_days: int = 14) -> dict[str, Any]:
    claims, paths = load_claims(root)
    errors, warnings = validate_claims(root, claims)
    today = date.today()
    expiring: list[dict[str, Any]] = []
    stale: list[dict[str, Any]] = []
    human_pending: list[dict[str, Any]] = []

    max_age = {
        ("fact", "overview"): 90,
        ("fact", ""): 180,
        ("rule", ""): 90,
        ("procedure", ""): 180,
        ("decision", ""): 180,
    }

    for claim_id, claim in sorted(claims.items()):
        if claim["status"] not in {"active", "pending", "contested"}:
            continue
        valid_to = parse_date(claim["valid_to"], "valid_to")
        if valid_to:
            remaining = (valid_to - today).days
            if -1 <= remaining <= within_days:
                expiring.append({
                    "id": claim_id,
                    "title": claim["title"],
                    "valid_to": claim["valid_to"],
                    "days_remaining": remaining,
                    "path": paths[claim_id].relative_to(root).as_posix(),
                })

        if claim["human_review"] == "pending" and claim["review_policy"] == "human":
            human_pending.append({
                "id": claim_id,
                "title": claim["title"],
                "path": paths[claim_id].relative_to(root).as_posix(),
            })

        age_limit = max_age.get((claim["kind"], claim["predicate"]))
        if age_limit is None and claim["kind"] == "rule":
            age_limit = 90
        if age_limit is None or not claim["checked_at"]:
            continue
        checked_at = parse_date(claim["checked_at"], "checked_at")
        if checked_at and (today - checked_at).days > age_limit:
            stale.append({
                "id": claim_id,
                "title": claim["title"],
                "checked_at": claim["checked_at"],
                "age_days": (today - checked_at).days,
                "max_age_days": age_limit,
                "path": paths[claim_id].relative_to(root).as_posix(),
            })

    return {
        "root": root.as_posix(),
        "claims": len(claims),
        "errors": errors,
        "warnings": warnings,
        "expiring": expiring,
        "stale": stale,
        "human_review_pending": human_pending,
    }


def rebuild(root: Path) -> dict[str, Any]:
    claims, _ = load_claims(root)
    errors, warnings = validate_claims(root, claims)
    if errors:
        raise ClaimError("validation failed:\n" + "\n".join(errors))
    return {"claims": len(claims), "errors": errors, "warnings": warnings}


def normalize_search_text(text: str) -> str:
    return re.sub(r"\s+", " ", text.casefold()).strip()


def search_claims(
    root: Path,
    query: str,
    *,
    limit: int = 5,
    statuses: set[str] | None = None,
    kind: str | None = None,
    subject: str | None = None,
    include_history: bool = False,
) -> list[dict[str, Any]]:
    claims, paths = load_claims(root)
    query_norm = normalize_search_text(query)
    if not query_norm:
        raise ClaimError("query cannot be empty")
    terms = [term for term in re.split(r"\s+", query_norm) if term]
    allowed_statuses = None if include_history and statuses is None else (statuses or {"active"})
    hits: list[tuple[float, str, dict[str, Any]]] = []
    for claim_id, claim in claims.items():
        if allowed_statuses and claim["status"] not in allowed_statuses:
            continue
        if claim["status"] == "active" and claim["valid_to"] and parse_date(claim["valid_to"], "valid_to") < date.today():
            continue
        if kind and claim["kind"] != kind:
            continue
        if subject and claim["subject"].casefold() != subject.casefold():
            continue
        title = normalize_search_text(claim["title"])
        subject_text = normalize_search_text(claim["subject"])
        predicate = normalize_search_text(claim["predicate"])
        object_text = normalize_search_text(claim["object"])
        body = normalize_search_text(claim.get("_body", ""))
        tags = " ".join(claim["tags"]).casefold()
        haystack = " ".join([title, subject_text, predicate, object_text, body, tags])
        score = 0.0
        if query_norm in haystack:
            score += 12.0
        for term in terms:
            if not term:
                continue
            if term in title:
                score += 5.0
            if term in subject_text:
                score += 4.0
            if term in predicate:
                score += 4.0
            if term in object_text:
                score += 4.0
            if term in body:
                score += min(4.0, 0.5 * body.count(term))
            if term in tags:
                score += 1.0
        if score <= 0:
            continue
        score += claim["confidence"] * 0.1
        item = dict(claim)
        item["_rel_path"] = paths[claim_id].relative_to(root).as_posix()
        hits.append((score, claim["updated"], item))
    hits.sort(key=lambda entry: (-entry[0], entry[1], entry[2]["id"]), reverse=False)
    out = []
    for score, _, claim in hits[:limit]:
        item = claim_summary(claim)
        item["score"] = round(score, 3)
        out.append(item)
    return out


def get_claim(root: Path, claim_id: str) -> dict[str, Any]:
    claims, paths = load_claims(root)
    claim = claims.get(claim_id)
    if claim is None:
        raise ClaimError(f"claim not found: {claim_id}")
    item = dict(claim)
    item["_rel_path"] = paths[claim_id].relative_to(root).as_posix()
    return item


def trace_claim(root: Path, claim_id: str) -> dict[str, Any]:
    claims, _ = load_claims(root)
    claim = claims.get(claim_id)
    if claim is None:
        raise ClaimError(f"claim not found: {claim_id}")
    chain: list[dict[str, Any]] = []
    seen: set[str] = set()
    current = claim
    while current is not None:
        chain.append(claim_summary(current))
        next_id = current.get("superseded_by") or ""
        if not next_id or next_id in seen:
            break
        seen.add(next_id)
        current = claims.get(next_id)
    supersedes = [claim_summary(claims[old_id]) for old_id in claim.get("supersedes", []) if old_id in claims]
    contradicts = [claim_summary(claims[other_id]) for other_id in claim.get("contradicts", []) if other_id in claims]
    from . import tasks as task_memory

    tasks, _ = task_memory.load_tasks(root)
    related_tasks = [
        {
            "id": task["id"],
            "title": task["title"],
            "project": task["project"],
            "status": task["status"],
            "priority": task["priority"],
        }
        for task in tasks.values()
        if task.get("claim_ref") == claim_id
    ]
    return {
        "claim": claim_detail(claim),
        "supersede_chain": chain,
        "supersedes": supersedes,
        "contradicts": contradicts,
        "tasks": related_tasks,
        "reme_ref": claim.get("reme_ref", ""),
    }


def changes_since(root: Path, since: str) -> dict[str, Any]:
    since_date = parse_date(since, "since")
    if since_date is None:
        raise ClaimError("since is required")
    claims, _ = load_claims(root)
    changed = []
    for claim in claims.values():
        updated = parse_date(claim["updated"], "updated")
        valid_from = parse_date(claim["valid_from"], "valid_from")
        if (updated is not None and updated >= since_date) or (valid_from is not None and valid_from >= since_date):
            changed.append(claim_summary(claim))
    changed.sort(key=lambda item: (item.get("updated", ""), item["id"]), reverse=True)
    return {"since": since, "count": len(changed), "claims": changed}


def stage_supersedes(claims: dict[str, dict[str, Any]], incoming: dict[str, Any], stamp: str) -> dict[str, str]:
    staged: dict[str, str] = {}
    for old_id in incoming["supersedes"]:
        old = claims.get(old_id)
        if old is None:
            raise ClaimError(f"supersedes points to missing claim {old_id!r}")
        if old["status"] != "active":
            raise ClaimError(f"cannot supersede non-active claim {old_id!r} (status={old['status']})")
        old["status"] = "superseded"
        old["superseded_by"] = incoming["id"]
        old["valid_to"] = old["valid_to"] or stamp
        old["updated"] = stamp
        old["_body"] = append_history(
            old.get("_body", ""),
            f"{stamp}：被 `{incoming['id']}` 取代。",
        )
        staged[old_id] = render_claim(old)
    return staged


def add_claim(root: Path, source_file: Path, *, replace: bool = False) -> dict[str, Any]:
    incoming_raw, incoming_body = split_frontmatter(source_file.read_text(encoding="utf-8-sig"))
    incoming = normalize_claim_data(incoming_raw)
    incoming["_body"] = incoming_body
    incoming["_path"] = expected_claim_path(root, incoming)
    with exclusive_lock(root):
        claims, paths = load_claims(root)
        existing = claims.get(incoming["id"])
        if existing and not replace:
            raise ClaimError(f"claim already exists: {incoming['id']} at {paths[incoming['id']]}")
        if existing and existing["kind"] != incoming["kind"]:
            raise ClaimError("replace cannot change a claim's kind")
        if replace and not existing:
            raise ClaimError(f"replace target does not exist: {incoming['id']}")
        if not replace:
            claims[incoming["id"]] = incoming
        stamp = today_iso()
        stage = stage_supersedes(claims, incoming, stamp)
        if replace:
            claims[incoming["id"]] = incoming
            claims[incoming["id"]]["_path"] = existing["_path"]
        errors, _ = validate_claims(root, claims)
        if errors:
            raise ClaimError("claim rejected:\n" + "\n".join(errors))
        target = expected_claim_path(root, incoming)
        for old_id, text in stage.items():
            atomic_write(paths[old_id], text)
        atomic_write(target, render_claim(incoming, incoming_body))
    rebuild(root)
    result = claim_summary(get_claim(root, incoming["id"]))
    try:
        archived_to = archive_candidate(root, source_file)
        if archived_to:
            result["candidate_archived_to"] = archived_to
    except OSError as exc:
        result["candidate_archive_error"] = str(exc)
    return result


def archive_candidate(root: Path, source_file: Path) -> str:
    inbox = (root / "inbox").resolve()
    candidate = source_file.expanduser().resolve()
    try:
        relative = candidate.relative_to(inbox)
    except ValueError:
        return ""
    if relative.parts and relative.parts[0] == "processed":
        return ""
    target_dir = root / "archive" / "processed-candidates" / today_iso()
    target = target_dir / candidate.name
    target_dir.mkdir(parents=True, exist_ok=True)
    counter = 2
    while target.exists():
        target = target_dir / f"{candidate.stem}-{counter}{candidate.suffix}"
        counter += 1
    shutil.move(str(candidate), str(target))
    return target.relative_to(root).as_posix()


def transition_claim(
    root: Path,
    claim_id: str,
    *,
    status: str,
    superseded_by: str = "",
    note: str = "",
) -> dict[str, Any]:
    status = status.lower()
    if status not in VALID_STATUSES:
        raise ClaimError(f"status must be one of {sorted(VALID_STATUSES)}")
    with exclusive_lock(root):
        claims, paths = load_claims(root)
        claim = claims.get(claim_id)
        if claim is None:
            raise ClaimError(f"claim not found: {claim_id}")
        old_status = claim["status"]
        if status not in VALID_TRANSITIONS[old_status]:
            raise ClaimError(f"invalid transition: {old_status} -> {status}")
        if status == "superseded" and not superseded_by:
            raise ClaimError("superseded status requires --superseded-by")
        if superseded_by and superseded_by not in claims:
            raise ClaimError(f"superseded_by points to missing claim {superseded_by!r}")
        stamp = today_iso()
        claim["status"] = status
        claim["superseded_by"] = superseded_by
        claim["updated"] = stamp
        if status in {"superseded", "expired", "archived"}:
            claim["valid_to"] = claim["valid_to"] or stamp
        if superseded_by:
            target = claims[superseded_by]
            if claim_id not in target["supersedes"]:
                target["supersedes"].append(claim_id)
        line = f"{stamp}：状态 `{old_status}` → `{status}`"
        if superseded_by:
            line += f"，由 `{superseded_by}` 接替"
        if note.strip():
            line += f"。{note.strip()}"
        claim["_body"] = append_history(claim.get("_body", ""), line)
        errors, _ = validate_claims(root, claims)
        if errors:
            raise ClaimError("transition rejected:\n" + "\n".join(errors))
        atomic_write(paths[claim_id], render_claim(claim))
    rebuild(root)
    return claim_summary(claim)


def review_claim(
    root: Path,
    claim_id: str,
    *,
    review_status: str,
    note: str = "",
) -> dict[str, Any]:
    review_status = review_status.lower()
    if review_status not in VALID_REVIEW_STATUSES:
        raise ClaimError(f"human_review must be one of {sorted(VALID_REVIEW_STATUSES)}")
    with exclusive_lock(root):
        claims, paths = load_claims(root)
        claim = claims.get(claim_id)
        if claim is None:
            raise ClaimError(f"claim not found: {claim_id}")
        old_status = claim["human_review"]
        stamp = today_iso()
        claim["human_review"] = review_status
        claim["updated"] = stamp
        line = f"{stamp}：人工评审 `{old_status}` → `{review_status}`"
        if note.strip():
            line += f"。{note.strip()}"
        claim["_body"] = append_history(claim.get("_body", ""), line)
        errors, _ = validate_claims(root, claims)
        if errors:
            raise ClaimError("review rejected:\n" + "\n".join(errors))
        atomic_write(paths[claim_id], render_claim(claim))
    rebuild(root)
    return claim_detail(get_claim(root, claim_id))


def review_claims(
    root: Path,
    claim_ids: list[str],
    *,
    review_status: str,
    note: str = "",
) -> dict[str, Any]:
    review_status = review_status.lower()
    if review_status not in VALID_REVIEW_STATUSES:
        raise ClaimError(f"human_review must be one of {sorted(VALID_REVIEW_STATUSES)}")
    unique_ids = list(dict.fromkeys(claim_ids))
    if not unique_ids:
        raise ClaimError("at least one claim id is required")
    stamp = today_iso()
    with exclusive_lock(root):
        claims, paths = load_claims(root)
        missing = [claim_id for claim_id in unique_ids if claim_id not in claims]
        if missing:
            raise ClaimError(f"claims not found: {missing}")
        changed: list[dict[str, str]] = []
        for claim_id in unique_ids:
            claim = claims[claim_id]
            old_status = claim["human_review"]
            claim["human_review"] = review_status
            claim["updated"] = stamp
            line = f"{stamp}：人工评审 `{old_status}` → `{review_status}`"
            if note.strip():
                line += f"。{note.strip()}"
            claim["_body"] = append_history(claim.get("_body", ""), line)
            changed.append({"id": claim_id, "from": old_status, "to": review_status})
        errors, _ = validate_claims(root, claims)
        if errors:
            raise ClaimError("batch review rejected:\n" + "\n".join(errors))
        for claim_id in unique_ids:
            atomic_write(paths[claim_id], render_claim(claims[claim_id]))
    rebuild(root)
    return {"updated": len(changed), "changes": changed}


def set_validity(
    root: Path,
    claim_id: str,
    *,
    valid_to: str,
    note: str = "",
) -> dict[str, Any]:
    target_date = parse_date(valid_to, "valid_to")
    if target_date is None:
        raise ClaimError("valid_to is required")
    with exclusive_lock(root):
        claims, paths = load_claims(root)
        claim = claims.get(claim_id)
        if claim is None:
            raise ClaimError(f"claim not found: {claim_id}")
        if claim["status"] == "active" and target_date < date.today():
            raise ClaimError("active claim cannot have a valid_to before today")
        old_valid_to = claim["valid_to"]
        stamp = today_iso()
        claim["valid_to"] = valid_to
        claim["updated"] = stamp
        line = f"{stamp}：有效期 `{old_valid_to or '无'}` → `{valid_to}`"
        if note.strip():
            line += f"。{note.strip()}"
        claim["_body"] = append_history(claim.get("_body", ""), line)
        errors, _ = validate_claims(root, claims)
        if errors:
            raise ClaimError("validity update rejected:\n" + "\n".join(errors))
        atomic_write(paths[claim_id], render_claim(claim))
    rebuild(root)
    return claim_detail(get_claim(root, claim_id))


def render_validation(root: Path) -> tuple[int, dict[str, Any]]:
    claims, _ = load_claims(root)
    errors, warnings = validate_claims(root, claims)
    payload = {"root": root.as_posix(), "claims": len(claims), "errors": errors, "warnings": warnings}
    return (1 if errors else 0), payload


def print_json(payload: Any) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Markdown semantic-memory claim store")
    parser.add_argument("--root", default=str(default_root()), help="SemanticMemory root")
    sub = parser.add_subparsers(dest="command", required=True)

    validate = sub.add_parser("validate", help="validate all claims and source evidence")
    validate.add_argument("--json", action="store_true")

    search = sub.add_parser("search", help="search claims")
    search.add_argument("query")
    search.add_argument("--limit", type=int, default=5)
    search.add_argument("--kind")
    search.add_argument("--subject")
    search.add_argument("--status", action="append", help="allowed status; repeat or use comma-separated values")
    search.add_argument("--include-history", action="store_true")
    search.add_argument("--json", action="store_true")

    get = sub.add_parser("get", help="read one claim")
    get.add_argument("claim_id")
    get.add_argument("--json", action="store_true")

    trace = sub.add_parser("trace", help="show a claim, its evidence, supersede chain, and related tasks")
    trace.add_argument("claim_id")
    trace.add_argument("--json", action="store_true")

    changes = sub.add_parser("changes", help="list claims changed since a date")
    changes.add_argument("--since", required=True)
    changes.add_argument("--json", action="store_true")

    add = sub.add_parser("add", help="add or replace a claim from a Markdown file")
    add.add_argument("file")
    add.add_argument("--replace", action="store_true")
    add.add_argument("--json", action="store_true")

    transition = sub.add_parser("transition", help="change a claim lifecycle status")
    transition.add_argument("claim_id")
    transition.add_argument("--status", required=True)
    transition.add_argument("--superseded-by", default="")
    transition.add_argument("--note", default="")
    transition.add_argument("--json", action="store_true")

    review = sub.add_parser("review", help="record a human review decision for one claim")
    review.add_argument("claim_id")
    review.add_argument("--status", required=True, choices=sorted(VALID_REVIEW_STATUSES))
    review.add_argument("--note", default="")
    review.add_argument("--json", action="store_true")

    validity = sub.add_parser("set-validity", help="set a claim validity end date")
    validity.add_argument("claim_id")
    validity.add_argument("--valid-to", required=True)
    validity.add_argument("--note", default="")
    validity.add_argument("--json", action="store_true")

    maintenance = sub.add_parser("maintenance", help="report expiring, stale, and human-review claims")
    maintenance.add_argument("--within-days", type=int, default=14)
    maintenance.add_argument("--strict", action="store_true")
    maintenance.add_argument("--json", action="store_true")
    return parser


def parse_statuses(values: list[str] | None) -> set[str] | None:
    if not values:
        return None
    result: set[str] = set()
    for value in values:
        result.update(item.strip().lower() for item in value.split(",") if item.strip())
    invalid = result - VALID_STATUSES
    if invalid:
        raise ClaimError(f"invalid statuses: {sorted(invalid)}")
    return result


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    root = paths.resolve_workspace_root(args.root)
    try:
        if args.command == "validate":
            code, payload = render_validation(root)
            if args.json:
                print_json(payload)
            else:
                print(f"validated claims={payload['claims']} errors={len(payload['errors'])} warnings={len(payload['warnings'])}")
                for item in payload["errors"]:
                    print(f"ERROR: {item}")
                for item in payload["warnings"]:
                    print(f"WARN: {item}")
            return code
        if args.command == "search":
            hits = search_claims(
                root,
                args.query,
                limit=args.limit,
                statuses=parse_statuses(args.status),
                kind=args.kind,
                subject=args.subject,
                include_history=args.include_history,
            )
            if args.json:
                print_json(hits)
            else:
                for hit in hits:
                    print(f"[{hit['score']:.3f}] {hit['id']}  {hit['title']}")
                    print(f"  status={hit['status']} subject={hit['subject']} predicate={hit['predicate']}")
                    print(f"  path={hit['path']}")
                if not hits:
                    print("(no matches)")
            return 0
        if args.command == "get":
            claim = get_claim(root, args.claim_id)
            if args.json:
                print_json(claim_detail(claim))
            else:
                print(render_claim(claim))
            return 0
        if args.command == "trace":
            payload = trace_claim(root, args.claim_id)
            if args.json:
                print_json(payload)
            else:
                claim = payload["claim"]
                print(f"{claim['id']}  {claim['title']}")
                print(f"status={claim['status']} kind={claim['kind']} scope={claim['scope']}")
                if payload["reme_ref"]:
                    print(f"reme_ref={payload['reme_ref']}")
                for source in claim.get("sources", []):
                    print(f"source={source.get('path')}")
                for item in payload["supersede_chain"]:
                    print(f"chain={item['id']} ({item['status']})")
                for item in payload["tasks"]:
                    print(f"task={item['id']} {item['title']}")
            return 0
        if args.command == "changes":
            payload = changes_since(root, args.since)
            if args.json:
                print_json(payload)
            else:
                print(f"changed since {payload['since']}: {payload['count']}")
                for item in payload["claims"]:
                    print(f"{item['updated']} {item['status']:9} {item['id']}  {item['title']}")
            return 0
        if args.command == "add":
            result = add_claim(root, Path(args.file).expanduser().resolve(), replace=args.replace)
            if args.json:
                print_json(result)
            else:
                print(f"saved {result['id']} -> {result['path']}")
            return 0
        if args.command == "transition":
            result = transition_claim(
                root,
                args.claim_id,
                status=args.status,
                superseded_by=args.superseded_by,
                note=args.note,
            )
            if args.json:
                print_json(result)
            else:
                print(f"transitioned {result['id']} -> {result['status']}")
            return 0
        if args.command == "review":
            result = review_claim(
                root,
                args.claim_id,
                review_status=args.status,
                note=args.note,
            )
            if args.json:
                print_json(result)
            else:
                print(f"reviewed {result['id']} -> {result['human_review']}")
            return 0
        if args.command == "set-validity":
            result = set_validity(
                root,
                args.claim_id,
                valid_to=args.valid_to,
                note=args.note,
            )
            if args.json:
                print_json(result)
            else:
                print(f"validity {result['id']} -> {result['valid_to']}")
            return 0
        if args.command == "maintenance":
            report = maintenance_report(root, within_days=args.within_days)
            if args.json:
                print_json(report)
            else:
                print(
                    "maintenance claims=%d expiring=%d stale=%d human_pending=%d errors=%d"
                    % (
                        report["claims"],
                        len(report["expiring"]),
                        len(report["stale"]),
                        len(report["human_review_pending"]),
                        len(report["errors"]),
                    )
                )
                for section in ("errors", "expiring", "stale", "human_review_pending"):
                    for item in report[section]:
                        print(f"{section}: {item}")
            has_attention = bool(report["expiring"] or report["stale"] or report["human_review_pending"])
            return 1 if report["errors"] or (args.strict and has_attention) else 0
    except ClaimError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
