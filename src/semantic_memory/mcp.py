#!/usr/bin/env python3
"""MCP stdio sidecar for the SemanticMemory claim and task stores.

This speaks newline-delimited JSON-RPC 2.0 over stdio and depends only on the
Python standard library plus PyYAML. It does not import ReMe.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

from . import claims as sm
from . import paths
from . import tasks as tm

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

SERVER_NAME = "SemanticMemory"
SERVER_VERSION = "0.1.0"


def dumps(value):
    return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True)


def status_payload(root):
    claims, _ = sm.load_claims(root)
    return {
        "root": root.as_posix(),
        "claims": len(claims),
        "status": dict(Counter(claim["status"] for claim in claims.values())),
        "human_review": dict(Counter(claim["human_review"] for claim in claims.values())),
        "review_policy": dict(Counter(claim["review_policy"] for claim in claims.values())),
        "kinds": dict(Counter(claim["kind"] for claim in claims.values())),
    }


def candidate_path(root, raw_path):
    candidate = Path(raw_path).expanduser().resolve()
    inbox = (root / "inbox").resolve()
    try:
        candidate.relative_to(inbox)
    except ValueError as exc:
        raise ValueError("candidate path must be inside SemanticMemory/inbox") from exc
    if not candidate.is_file():
        raise FileNotFoundError(candidate)
    return candidate


def tool_definitions(read_only):
    read_tools = [
        {
            "name": "semantic_status",
            "description": "Count SemanticMemory claims by status, kind, and human review state.",
            "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
        },
        {
            "name": "semantic_search",
            "description": "Search current SemanticMemory claims. Results include human_review and sources.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "minLength": 1},
                    "limit": {"type": "integer", "minimum": 1, "maximum": 50, "default": 5},
                    "include_history": {"type": "boolean", "default": False},
                    "status": {"type": "array", "items": {"type": "string"}},
                    "kind": {"type": "string"},
                    "subject": {"type": "string"},
                },
                "required": ["query"],
                "additionalProperties": False,
            },
        },
        {
            "name": "semantic_get",
            "description": "Read one SemanticMemory claim by stable ID, including its full body.",
            "inputSchema": {
                "type": "object",
                "properties": {"claim_id": {"type": "string"}},
                "required": ["claim_id"],
                "additionalProperties": False,
            },
        },
        {
            "name": "semantic_trace",
            "description": "Show one claim's evidence, supersede chain, contradictions, ReMe pointer, and related tasks.",
            "inputSchema": {
                "type": "object",
                "properties": {"claim_id": {"type": "string"}},
                "required": ["claim_id"],
                "additionalProperties": False,
            },
        },
        {
            "name": "semantic_changes",
            "description": "List claims changed since a date (YYYY-MM-DD).",
            "inputSchema": {
                "type": "object",
                "properties": {"since": {"type": "string"}},
                "required": ["since"],
                "additionalProperties": False,
            },
        },
        {
            "name": "semantic_validate",
            "description": "Validate claim schema, source paths, quotes, and supersede relationships.",
            "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
        },
        {
            "name": "semantic_maintenance",
            "description": "Report expiring, stale, human-review, and validation issues without modifying claims.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "within_days": {"type": "integer", "minimum": 0, "maximum": 365, "default": 14},
                },
                "additionalProperties": False,
            },
        },
        {
            "name": "task_list",
            "description": "List active SemanticMemory tasks, optionally filtered by project.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "project": {"type": "string", "default": ""},
                    "include_done": {"type": "boolean", "default": False},
                    "include_blocked": {"type": "boolean", "default": False},
                },
                "additionalProperties": False,
            },
        },
        {
            "name": "task_validate",
            "description": "Validate task files and their recorded source evidence.",
            "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
        },
    ]
    if read_only:
        return read_tools
    return read_tools + [
        {
            "name": "semantic_add",
            "description": "Promote one candidate Markdown file from inbox into claims after validation.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "candidate_path": {"type": "string"},
                    "replace": {"type": "boolean", "default": False},
                },
                "required": ["candidate_path"],
                "additionalProperties": False,
            },
        },
        {
            "name": "semantic_transition",
            "description": "Move a claim through active, contested, expired, archived, or superseded.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "claim_id": {"type": "string"},
                    "status": {"type": "string"},
                    "superseded_by": {"type": "string", "default": ""},
                    "note": {"type": "string", "default": ""},
                },
                "required": ["claim_id", "status"],
                "additionalProperties": False,
            },
        },
        {
            "name": "semantic_review",
            "description": "Record a human review decision for one claim without changing its lifecycle status.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "claim_id": {"type": "string"},
                    "status": {"type": "string", "enum": ["pending", "accepted", "disputed", "not_required"]},
                    "note": {"type": "string", "default": ""},
                },
                "required": ["claim_id", "status"],
                "additionalProperties": False,
            },
        },
        {
            "name": "semantic_set_validity",
            "description": "Set or refresh the valid_to date for one claim.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "claim_id": {"type": "string"},
                    "valid_to": {"type": "string"},
                    "note": {"type": "string", "default": ""},
                },
                "required": ["claim_id", "valid_to"],
                "additionalProperties": False,
            },
        },
        {
            "name": "task_add",
            "description": "Add one Markdown task to the SemanticMemory task store.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "project": {"type": "string"},
                    "title": {"type": "string"},
                    "priority": {"type": "string", "default": "normal"},
                    "source": {"type": "string", "default": ""},
                    "source_quote": {"type": "string", "default": ""},
                    "claim_ref": {"type": "string", "default": ""},
                },
                "required": ["project", "title"],
                "additionalProperties": False,
            },
        },
        {
            "name": "task_complete",
            "description": "Mark one SemanticMemory task as done.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "task_id": {"type": "string"},
                    "note": {"type": "string", "default": ""},
                },
                "required": ["task_id"],
                "additionalProperties": False,
            },
        },
        {
            "name": "task_cancel",
            "description": "Mark one obsolete SemanticMemory task as cancelled.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "task_id": {"type": "string"},
                    "note": {"type": "string", "default": ""},
                },
                "required": ["task_id"],
                "additionalProperties": False,
            },
        },
    ]


def call_tool(root, read_only, name, arguments):
    if name == "semantic_status":
        return dumps(status_payload(root))
    if name == "semantic_search":
        query = str(arguments.get("query", "")).strip()
        hits = sm.search_claims(
            root,
            query,
            limit=int(arguments.get("limit", 5)),
            statuses=set(arguments["status"]) if arguments.get("status") else None,
            kind=arguments.get("kind"),
            subject=arguments.get("subject"),
            include_history=bool(arguments.get("include_history", False)),
        )
        return dumps(hits)
    if name == "semantic_get":
        return dumps(sm.claim_detail(sm.get_claim(root, str(arguments["claim_id"]))))
    if name == "semantic_trace":
        return dumps(sm.trace_claim(root, str(arguments["claim_id"])))
    if name == "semantic_changes":
        return dumps(sm.changes_since(root, str(arguments["since"])))
    if name == "semantic_validate":
        code, payload = sm.render_validation(root)
        payload["ok"] = code == 0
        return dumps(payload)
    if name == "semantic_maintenance":
        return dumps(sm.maintenance_report(root, within_days=int(arguments.get("within_days", 14))))
    if name == "task_list":
        return dumps(
            tm.list_tasks(
                root,
                project=str(arguments.get("project", "")),
                include_done=bool(arguments.get("include_done", False)),
                include_blocked=bool(arguments.get("include_blocked", False)),
            )
        )
    if name == "task_validate":
        errors, warnings = tm.validate_tasks(root)
        return dumps({"ok": not errors, "errors": errors, "warnings": warnings})
    if read_only:
        raise ValueError("tool is unavailable in read-only mode: " + name)
    if name == "semantic_add":
        candidate = candidate_path(root, str(arguments["candidate_path"]))
        return dumps(sm.add_claim(root, candidate, replace=bool(arguments.get("replace", False))))
    if name == "semantic_transition":
        return dumps(
            sm.transition_claim(
                root,
                str(arguments["claim_id"]),
                status=str(arguments["status"]),
                superseded_by=str(arguments.get("superseded_by", "")),
                note=str(arguments.get("note", "")),
            )
        )
    if name == "semantic_review":
        return dumps(
            sm.review_claim(
                root,
                str(arguments["claim_id"]),
                review_status=str(arguments["status"]),
                note=str(arguments.get("note", "")),
            )
        )
    if name == "semantic_set_validity":
        return dumps(
            sm.set_validity(
                root,
                str(arguments["claim_id"]),
                valid_to=str(arguments["valid_to"]),
                note=str(arguments.get("note", "")),
            )
        )
    if name == "task_add":
        return dumps(
            tm.add_task(
                root,
                project=str(arguments["project"]),
                title=str(arguments["title"]),
                priority=str(arguments.get("priority", "normal")),
                source=str(arguments.get("source", "")),
                source_quote=str(arguments.get("source_quote", "")),
                claim_ref=str(arguments.get("claim_ref", "")),
            )
        )
    if name == "task_complete":
        return dumps(
            tm.complete_task(
                root,
                str(arguments["task_id"]),
                note=str(arguments.get("note", "")),
            )
        )
    if name == "task_cancel":
        return dumps(
            tm.cancel_task(
                root,
                str(arguments["task_id"]),
                note=str(arguments.get("note", "")),
            )
        )
    raise ValueError("unknown tool: " + name)


def response(message_id, result):
    return {"jsonrpc": "2.0", "id": message_id, "result": result}


def error(message_id, code, message):
    return {"jsonrpc": "2.0", "id": message_id, "error": {"code": code, "message": message}}


def handle_message(root, read_only, message):
    method = message.get("method")
    message_id = message.get("id")
    params = message.get("params") or {}
    if method == "initialize":
        return response(message_id, {
            "protocolVersion": params.get("protocolVersion") or "2024-11-05",
            "capabilities": {"tools": {"listChanged": False}},
            "serverInfo": {"name": SERVER_NAME, "version": SERVER_VERSION},
            "instructions": (
                "SemanticMemory is the current-fact layer. Use semantic_search for current facts, "
                "then use ReMe separately for original evidence. human_review pending is not accepted truth."
            ),
        })
    if method in {"notifications/initialized", "notifications/cancelled"}:
        return None
    if method == "ping":
        return response(message_id, {})
    if method == "tools/list":
        return response(message_id, {"tools": tool_definitions(read_only)})
    if method == "tools/call":
        name = str(params.get("name", ""))
        arguments = params.get("arguments") or {}
        if not isinstance(arguments, dict):
            return error(message_id, -32602, "tool arguments must be an object")
        try:
            text = call_tool(root, read_only, name, arguments)
            return response(message_id, {
                "content": [{"type": "text", "text": text}],
                "isError": False,
            })
        except Exception as exc:
            return response(message_id, {
                "content": [{"type": "text", "text": type(exc).__name__ + ": " + str(exc)}],
                "isError": True,
            })
    if method == "shutdown":
        return response(message_id, {})
    if message_id is not None:
        return error(message_id, -32601, "method not found: " + str(method))
    return None


def run_stdio(root, read_only=False):
    for line in sys.stdin:
        if not line.strip():
            continue
        try:
            message = json.loads(line)
        except json.JSONDecodeError as exc:
            sys.stdout.write(json.dumps(error(None, -32700, "parse error: " + str(exc))) + "\n")
            sys.stdout.flush()
            continue
        payload = handle_message(root, read_only, message)
        if payload is not None:
            sys.stdout.write(json.dumps(payload, ensure_ascii=False) + "\n")
            sys.stdout.flush()
        if message.get("method") == "shutdown":
            break


def main():
    parser = argparse.ArgumentParser(description="SemanticMemory MCP stdio sidecar")
    parser.add_argument("--root", default=str(paths.default_root()))
    parser.add_argument("--read-only", action="store_true", help="Expose read tools only")
    parser.add_argument("--self-test", action="store_true", help="Run a local JSON-RPC self-test and exit")
    args = parser.parse_args()
    root = paths.resolve_workspace_root(args.root)
    if not (root / "claims").is_dir():
        raise RuntimeError(f"SemanticMemory root not found: {root}")
    if args.self_test:
        tests = [
            {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2024-11-05"}},
            {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
            {"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {"name": "semantic_status", "arguments": {}}},
            {"jsonrpc": "2.0", "id": 4, "method": "tools/call", "params": {"name": "semantic_search", "arguments": {"query": "concise", "limit": 1}}},
            {"jsonrpc": "2.0", "id": 5, "method": "tools/call", "params": {"name": "semantic_validate", "arguments": {}}},
            {"jsonrpc": "2.0", "id": 6, "method": "tools/call", "params": {"name": "task_list", "arguments": {"project": "demo"}}},
            {"jsonrpc": "2.0", "id": 7, "method": "tools/call", "params": {"name": "task_validate", "arguments": {}}},
        ]
        for message in tests:
            payload = handle_message(root, args.read_only, message)
            if payload is not None:
                print(dumps(payload))
        return
    run_stdio(root, read_only=args.read_only)


if __name__ == "__main__":
    main()
