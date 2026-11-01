"""Unified command-line interface for SemanticMemory."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from . import claims
from . import demo
from . import paths
from . import tasks
from .errors import WorkspaceError


def _json(value: Any) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True))


def _add_root(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--root", default=str(paths.default_root()), help="SemanticMemory workspace root")


def _add_json(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--json", action="store_true")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Evidence-first current facts and tasks")
    sub = parser.add_subparsers(dest="command", required=True)

    init = sub.add_parser("init", help="create an empty workspace")
    _add_root(init)
    _add_json(init)

    demo_parser = sub.add_parser("demo", help="run a self-contained temporary demo")
    _add_json(demo_parser)

    validate = sub.add_parser("validate", help="validate claims and source evidence")
    _add_root(validate)
    _add_json(validate)

    search = sub.add_parser("search", help="search current claims")
    _add_root(search)
    _add_json(search)
    search.add_argument("query")
    search.add_argument("--limit", type=int, default=5)
    search.add_argument("--kind")
    search.add_argument("--subject")
    search.add_argument("--status", action="append")
    search.add_argument("--include-history", action="store_true")

    get = sub.add_parser("get", help="read one claim")
    _add_root(get)
    _add_json(get)
    get.add_argument("claim_id")

    trace = sub.add_parser("trace", help="show evidence, history, and related tasks")
    _add_root(trace)
    _add_json(trace)
    trace.add_argument("claim_id")

    changes = sub.add_parser("changes", help="list claims changed since a date")
    _add_root(changes)
    _add_json(changes)
    changes.add_argument("--since", required=True)

    add = sub.add_parser("add", help="add or replace a claim candidate")
    _add_root(add)
    _add_json(add)
    add.add_argument("file")
    add.add_argument("--replace", action="store_true")

    transition = sub.add_parser("transition", help="change a claim lifecycle status")
    _add_root(transition)
    _add_json(transition)
    transition.add_argument("claim_id")
    transition.add_argument("--status", required=True)
    transition.add_argument("--superseded-by", default="")
    transition.add_argument("--note", default="")

    review = sub.add_parser("review", help="record a human review decision")
    _add_root(review)
    _add_json(review)
    review.add_argument("claim_id")
    review.add_argument("--status", required=True, choices=sorted(claims.VALID_REVIEW_STATUSES))
    review.add_argument("--note", default="")

    validity = sub.add_parser("set-validity", help="set a claim validity end date")
    _add_root(validity)
    _add_json(validity)
    validity.add_argument("claim_id")
    validity.add_argument("--valid-to", required=True)
    validity.add_argument("--note", default="")

    maintenance = sub.add_parser("maintenance", help="report review and validity attention")
    _add_root(maintenance)
    _add_json(maintenance)
    maintenance.add_argument("--within-days", type=int, default=14)
    maintenance.add_argument("--strict", action="store_true")

    task = sub.add_parser("task", help="manage Markdown tasks")
    task_sub = task.add_subparsers(dest="task_command", required=True)

    task_validate = task_sub.add_parser("validate")
    _add_root(task_validate)
    _add_json(task_validate)

    task_list = task_sub.add_parser("list")
    _add_root(task_list)
    _add_json(task_list)
    task_list.add_argument("--project", default="")
    task_list.add_argument("--include-done", action="store_true")
    task_list.add_argument("--include-blocked", action="store_true")

    task_add = task_sub.add_parser("add")
    _add_root(task_add)
    _add_json(task_add)
    task_add.add_argument("--project", required=True)
    task_add.add_argument("--title", required=True)
    task_add.add_argument("--priority", default="normal")
    task_add.add_argument("--source", default="")
    task_add.add_argument("--source-quote", default="")
    task_add.add_argument("--claim-ref", default="")

    task_complete = task_sub.add_parser("complete")
    _add_root(task_complete)
    _add_json(task_complete)
    task_complete.add_argument("task_id")
    task_complete.add_argument("--note", default="")

    task_cancel = task_sub.add_parser("cancel")
    _add_root(task_cancel)
    _add_json(task_cancel)
    task_cancel.add_argument("task_id")
    task_cancel.add_argument("--note", default="")

    return parser


def _print_validation(payload: dict[str, Any]) -> None:
    print(
        f"validated claims={payload['claims']} "
        f"errors={len(payload['errors'])} warnings={len(payload['warnings'])}"
    )
    for item in payload["errors"]:
        print(f"ERROR: {item}")
    for item in payload["warnings"]:
        print(f"WARN: {item}")


def _handle_claim_command(args: argparse.Namespace, root: Path) -> int:
    if args.command == "validate":
        code, payload = claims.render_validation(root)
        _json(payload) if args.json else _print_validation(payload)
        return code
    if args.command == "search":
        hits = claims.search_claims(
            root,
            args.query,
            limit=args.limit,
            statuses=claims.parse_statuses(args.status),
            kind=args.kind,
            subject=args.subject,
            include_history=args.include_history,
        )
        if args.json:
            _json(hits)
        else:
            for hit in hits:
                print(f"[{hit['score']:.3f}] {hit['id']}  {hit['title']}")
                print(f"  status={hit['status']} path={hit['path']}")
            if not hits:
                print("(no matches)")
        return 0
    if args.command == "get":
        claim = claims.claim_detail(claims.get_claim(root, args.claim_id))
        _json(claim) if args.json else print(claims.render_claim(claims.get_claim(root, args.claim_id)))
        return 0
    if args.command == "trace":
        payload = claims.trace_claim(root, args.claim_id)
        _json(payload)
        return 0
    if args.command == "changes":
        payload = claims.changes_since(root, args.since)
        if args.json:
            _json(payload)
        else:
            print(f"changed since {payload['since']}: {payload['count']}")
            for item in payload["claims"]:
                print(f"{item['updated']} {item['id']}  {item['title']}")
        return 0
    if args.command == "add":
        result = claims.add_claim(root, Path(args.file).expanduser().resolve(), replace=args.replace)
        _json(result) if args.json else print(f"saved {result['id']} -> {result['path']}")
        return 0
    if args.command == "transition":
        result = claims.transition_claim(
            root,
            args.claim_id,
            status=args.status,
            superseded_by=args.superseded_by,
            note=args.note,
        )
        _json(result) if args.json else print(f"transitioned {result['id']} -> {result['status']}")
        return 0
    if args.command == "review":
        result = claims.review_claim(root, args.claim_id, review_status=args.status, note=args.note)
        _json(result) if args.json else print(f"reviewed {result['id']} -> {result['human_review']}")
        return 0
    if args.command == "set-validity":
        result = claims.set_validity(root, args.claim_id, valid_to=args.valid_to, note=args.note)
        _json(result) if args.json else print(f"validity {result['id']} -> {result['valid_to']}")
        return 0
    if args.command == "maintenance":
        report = claims.maintenance_report(root, within_days=args.within_days)
        if args.json:
            _json(report)
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
        attention = bool(report["expiring"] or report["stale"] or report["human_review_pending"])
        return 1 if report["errors"] or (args.strict and attention) else 0
    raise WorkspaceError(f"unknown command: {args.command}")


def _handle_task_command(args: argparse.Namespace, root: Path) -> int:
    if args.task_command == "validate":
        errors, warnings = tasks.validate_tasks(root)
        payload = {"ok": not errors, "errors": errors, "warnings": warnings}
        if args.json:
            _json(payload)
        else:
            print(f"validated tasks errors={len(errors)} warnings={len(warnings)}")
            for item in errors:
                print(f"ERROR: {item}")
            for item in warnings:
                print(f"WARN: {item}")
        return 0 if not errors else 1
    if args.task_command == "list":
        items = tasks.list_tasks(
            root,
            project=args.project,
            include_done=args.include_done,
            include_blocked=args.include_blocked,
        )
        if args.json:
            _json(items)
        else:
            for item in items:
                print(f"{item['id']}  [{item['status']}/{item['priority']}]  {item['project']}: {item['title']}")
        return 0
    if args.task_command == "add":
        result = tasks.add_task(
            root,
            project=args.project,
            title=args.title,
            priority=args.priority,
            source=args.source,
            source_quote=args.source_quote,
            claim_ref=args.claim_ref,
        )
        _json(result) if args.json else print(f"added {result['id']}: {result['title']}")
        return 0
    if args.task_command == "complete":
        result = tasks.complete_task(root, args.task_id, note=args.note)
        _json(result) if args.json else print(f"completed {args.task_id}")
        return 0
    if args.task_command == "cancel":
        result = tasks.cancel_task(root, args.task_id, note=args.note)
        _json(result) if args.json else print(f"cancelled {args.task_id}")
        return 0
    raise WorkspaceError(f"unknown task command: {args.task_command}")


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "demo":
            payload = demo.run_demo()
            _json(payload) if args.json else demo.print_demo(payload)
            return 0
        if args.command == "init":
            root = paths.init_workspace(args.root)
            _json({"ok": True, "root": root.as_posix()}) if args.json else print(f"initialized {root}")
            return 0
        root = paths.resolve_workspace_root(args.root)
        if args.command == "task":
            return _handle_task_command(args, root)
        return _handle_claim_command(args, root)
    except (claims.ClaimError, tasks.TaskError, WorkspaceError, OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
