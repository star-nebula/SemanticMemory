#!/usr/bin/env python3
"""Markdown task store for SemanticMemory."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import tempfile
from datetime import date
from pathlib import Path

import yaml

from . import paths

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

SCHEMA = "semantic-memory-task/v1"
VALID_STATUSES = {"open", "done", "blocked", "cancelled"}
TASK_FIELDS = (
    "schema",
    "type",
    "id",
    "title",
    "project",
    "status",
    "priority",
    "created",
    "updated",
    "source",
    "source_quote",
    "claim_ref",
)


class TaskError(ValueError):
    """Raised for malformed or inconsistent task data."""


def today_iso() -> str:
    return date.today().isoformat()


def split_frontmatter(text: str) -> tuple[dict, str]:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    if not text.startswith("---\n"):
        raise TaskError("task must start with YAML frontmatter")
    end = text.find("\n---\n", 4)
    if end < 0:
        raise TaskError("task frontmatter is missing its closing delimiter")
    data = yaml.safe_load(text[4:end]) or {}
    if not isinstance(data, dict):
        raise TaskError("task frontmatter must be a mapping")
    return data, text[end + 5 :].lstrip("\n").rstrip() + "\n"


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


def task_id(project: str, title: str) -> str:
    digest = hashlib.sha1((project + "\n" + title).encode("utf-8")).hexdigest()[:10]
    return "task-" + digest


def normalize_task(raw: dict) -> dict:
    task = dict(raw)
    if task.get("schema") != SCHEMA:
        raise TaskError(f"schema must be {SCHEMA!r}")
    if task.get("type") != "task":
        raise TaskError("type must be 'task'")
    task_id_value = str(task.get("id") or "").strip()
    if not re.fullmatch(r"task-[a-z0-9]{10}", task_id_value):
        raise TaskError("task id must match task-<10 lowercase alphanumeric chars>")
    title = str(task.get("title") or "").strip()
    project = str(task.get("project") or "").strip()
    if not title or not project:
        raise TaskError("title and project are required")
    status = str(task.get("status") or "open").strip().lower()
    if status not in VALID_STATUSES:
        raise TaskError(f"status must be one of {sorted(VALID_STATUSES)}")
    return {
        "schema": SCHEMA,
        "type": "task",
        "id": task_id_value,
        "title": title,
        "project": project,
        "status": status,
        "priority": str(task.get("priority") or "normal").strip().lower(),
        "created": str(task.get("created") or today_iso()),
        "updated": str(task.get("updated") or today_iso()),
        "source": str(task.get("source") or "").strip(),
        "source_quote": str(task.get("source_quote") or "").strip(),
        "claim_ref": str(task.get("claim_ref") or "").strip(),
    }


def render_task(task: dict) -> str:
    front_data = {key: task[key] for key in TASK_FIELDS}
    front = yaml.safe_dump(front_data, allow_unicode=True, sort_keys=False, default_flow_style=False, width=120)
    body = f"# {task['title']}\n"
    if task.get("source_quote"):
        body += "\n" + task["source_quote"] + "\n"
    return "---\n" + front.rstrip() + "\n---\n\n" + body


def task_files(root: Path) -> list[tuple[str, Path]]:
    files: list[tuple[str, Path]] = []
    for state in ("open", "done"):
        directory = root / "tasks" / state
        if directory.is_dir():
            files.extend(
                (state, path)
                for path in sorted(directory.glob("task-*.md"))
                if path.is_file()
            )
    return files


def load_tasks(root: Path) -> tuple[dict[str, dict], dict[str, Path]]:
    tasks: dict[str, dict] = {}
    paths: dict[str, Path] = {}
    for state, path in task_files(root):
        raw, body = split_frontmatter(path.read_text(encoding="utf-8-sig"))
        task = normalize_task(raw)
        expected_state = "done" if task["status"] in {"done", "cancelled"} else "open"
        if state != expected_state:
            raise TaskError(f"{task['id']}: status {task['status']} must live under tasks/{expected_state}")
        if task["id"] in tasks:
            raise TaskError(f"duplicate task id: {task['id']}")
        task["_body"] = body
        task["_path"] = path
        tasks[task["id"]] = task
        paths[task["id"]] = path
    return tasks, paths


def rebuild(root: Path) -> dict:
    tasks, _ = load_tasks(root)
    active = [task for task in tasks.values() if task["status"] in {"open", "blocked"}]
    return {"tasks": len(tasks), "open": len(active)}


def add_task(
    root: Path,
    project: str,
    title: str,
    priority: str = "normal",
    source: str = "",
    source_quote: str = "",
    claim_ref: str = "",
) -> dict:
    tasks, _ = load_tasks(root)
    key = task_id(project, title)
    if key in tasks:
        raise TaskError(f"task already exists: {key}")
    task = normalize_task(
        {
            "schema": SCHEMA,
            "type": "task",
            "id": key,
            "title": title,
            "project": project,
            "status": "open",
            "priority": priority,
            "created": today_iso(),
            "updated": today_iso(),
            "source": source,
            "source_quote": source_quote,
            "claim_ref": claim_ref,
        }
    )
    atomic_write(root / "tasks" / "open" / f"{key}.md", render_task(task))
    rebuild(root)
    return task


def close_task(root: Path, key: str, *, status: str, note: str = "") -> dict:
    if status not in {"done", "cancelled"}:
        raise TaskError("close status must be done or cancelled")
    tasks, paths = load_tasks(root)
    task = tasks.get(key)
    if task is None:
        raise TaskError(f"task not found: {key}")
    if task["status"] in {"done", "cancelled"}:
        raise TaskError(f"task is already closed: {key}")
    old_path = paths[key]
    task["status"] = status
    task["updated"] = today_iso()
    if note.strip():
        heading = "Completion" if status == "done" else "Cancellation"
        task["_body"] = task["_body"].rstrip() + f"\n\n## {heading}\n\n- {today_iso()}: {note.strip()}\n"
    target = root / "tasks" / "done" / f"{key}.md"
    front_data = {key: task[key] for key in TASK_FIELDS}
    front = yaml.safe_dump(front_data, allow_unicode=True, sort_keys=False, default_flow_style=False, width=120)
    atomic_write(target, "---\n" + front.rstrip() + "\n---\n\n" + task["_body"].lstrip())
    old_path.unlink()
    rebuild(root)
    return {key: task[key] for key in TASK_FIELDS}


def complete_task(root: Path, key: str, note: str = "") -> dict:
    return close_task(root, key, status="done", note=note)


def cancel_task(root: Path, key: str, note: str = "") -> dict:
    return close_task(root, key, status="cancelled", note=note)


def list_tasks(root: Path, project: str = "", include_done: bool = False, include_blocked: bool = False) -> list[dict]:
    tasks, paths = load_tasks(root)
    out = []
    for key, task in sorted(tasks.items(), key=lambda item: (item[1]["project"], item[0])):
        if project and task["project"].casefold() != project.casefold():
            continue
        if not include_done and task["status"] in {"done", "cancelled"}:
            continue
        if not include_blocked and task["status"] == "blocked":
            continue
        out.append(
            {
                "id": task["id"],
                "title": task["title"],
                "project": task["project"],
                "status": task["status"],
                "priority": task["priority"],
                "updated": task["updated"],
                "path": paths[key].relative_to(root).as_posix(),
                "claim_ref": task.get("claim_ref", ""),
            }
        )
    return out


def is_uri_source(source: str) -> bool:
    """Return True for explicit URI sources that are not local file paths."""
    return re.match(r"^[A-Za-z][A-Za-z0-9+.-]*://", source) is not None


def validate_tasks(root: Path) -> tuple[list[str], list[str]]:
    tasks, _ = load_tasks(root)
    errors: list[str] = []
    warnings: list[str] = []
    for key, task in tasks.items():
        claim_ref = task.get("claim_ref", "")
        if claim_ref and not any((root / "claims").glob(f"*/{claim_ref}.md")):
            warnings.append(f"{key}: claim_ref does not exist: {claim_ref}")
        if not task["source"]:
            warnings.append(f"{key}: no source recorded")
            continue
        if is_uri_source(task["source"]):
            if task["source_quote"]:
                warnings.append(f"{key}: source_quote cannot be verified for URI source")
            continue
        source = Path(task["source"])
        source_path = source if source.is_absolute() else root / source
        if not source_path.is_file():
            errors.append(f"{key}: source does not exist: {source_path}")
            continue
        if task["source_quote"] and source_path.suffix.lower() in {".md", ".txt"}:
            text = re.sub(r"\s+", " ", source_path.read_text(encoding="utf-8-sig", errors="replace"))
            quote = re.sub(r"\s+", " ", task["source_quote"]).strip()
            if quote not in text:
                errors.append(f"{key}: source_quote not found in {source_path}")
    return errors, warnings


def main() -> int:
    parser = argparse.ArgumentParser(description="Manage SemanticMemory tasks")
    parser.add_argument("--root", default=str(paths.default_root()))
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("validate")
    listing = sub.add_parser("list")
    listing.add_argument("--project", default="")
    listing.add_argument("--include-done", action="store_true")
    listing.add_argument("--include-blocked", action="store_true")
    listing.add_argument("--json", action="store_true")
    add = sub.add_parser("add")
    add.add_argument("--project", required=True)
    add.add_argument("--title", required=True)
    add.add_argument("--priority", default="normal")
    add.add_argument("--source", default="")
    add.add_argument("--source-quote", default="")
    add.add_argument("--claim-ref", default="")
    done = sub.add_parser("complete")
    done.add_argument("task_id")
    done.add_argument("--note", default="")
    cancel = sub.add_parser("cancel")
    cancel.add_argument("task_id")
    cancel.add_argument("--note", default="")
    args = parser.parse_args()
    root = paths.resolve_workspace_root(args.root)
    try:
        if args.command == "validate":
            errors, warnings = validate_tasks(root)
            print(
                json.dumps(
                    {"ok": not errors, "errors": errors, "warnings": warnings},
                    ensure_ascii=False,
                    indent=2,
                )
            )
            return 0 if not errors else 1
        elif args.command == "list":
            items = list_tasks(root, args.project, args.include_done, args.include_blocked)
            if args.json:
                print(json.dumps(items, ensure_ascii=False, indent=2))
            else:
                for item in items:
                    print(f"{item['id']}  [{item['status']}/{item['priority']}]  {item['project']}: {item['title']}")
        elif args.command == "add":
            print(
                json.dumps(
                    add_task(
                        root,
                        args.project,
                        args.title,
                        args.priority,
                        args.source,
                        args.source_quote,
                        args.claim_ref,
                    ),
                    ensure_ascii=False,
                )
            )
        elif args.command == "complete":
            print(json.dumps(complete_task(root, args.task_id, args.note), ensure_ascii=False))
        elif args.command == "cancel":
            print(json.dumps(cancel_task(root, args.task_id, args.note), ensure_ascii=False))
        return 0
    except TaskError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
