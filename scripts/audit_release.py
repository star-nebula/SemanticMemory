#!/usr/bin/env python3
"""Scan a SemanticMemory checkout for private paths, credentials, and PII."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

SKIP_DIRECTORIES = {
    ".git",
    ".semantic-memory",
    "__pycache__",
    ".pytest_cache",
    ".venv",
    "build",
    "dist",
}
SKIP_SUFFIXES = {".pyc", ".pyo", ".png", ".jpg", ".jpeg", ".gif", ".zip", ".whl"}
CHECKS = (
    (
        "absolute local path",
        re.compile(
            r"(?i)(?:[a-z]:[\\/](?:users|knowledge|projects)(?![a-z0-9_-])"
            r"|/(?:home|users)/[^/\s]+/)"
        ),
    ),
    ("private key marker", re.compile(r"-----BEGIN (?:RSA |OPENSSH |EC |DSA )?PRIVATE KEY-----")),
    (
        "credential assignment",
        re.compile(
            r"(?i)\b(?:api[_-]?key|client[_-]?secret|access[_-]?token|password)\b"
            r"\s*[:=]\s*['\"]?[A-Za-z0-9_./+=-]{12,}"
        ),
    ),
    (
        "session identifier URI",
        re.compile(
            r"(?i)\b[a-z][a-z0-9+.-]*://[^\s<>\"']*"
            r"(?:threads?|sessions?|conversations?)/"
            r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b"
        ),
    ),
    (
        "session identifier (UUIDv7)",
        re.compile(
            r"(?i)\b[0-9a-f]{8}-[0-9a-f]{4}-7[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}\b"
        ),
    ),
    (
        "session identifier (UUID in session context)",
        re.compile(
            r"(?i)(?=.*\b(?:thread|session|conversation)\b)"
            r".*\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b"
        ),
    ),
    (
        "email address",
        re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE),
    ),
)
EMAIL_ALLOWLIST = {
    "example.com",
    "example.org",
    "users.noreply.github.com",
}


def iter_files(roots: list[Path]):
    for root in roots:
        if root.is_file():
            yield root
            continue
        for path in sorted(root.rglob("*")):
            if not path.is_file():
                continue
            if any(part in SKIP_DIRECTORIES for part in path.parts):
                continue
            if path.suffix.lower() in SKIP_SUFFIXES:
                continue
            yield path


def audit_file(path: Path) -> list[dict[str, object]]:
    try:
        data = path.read_bytes()
    except OSError as exc:
        return [{"path": path.as_posix(), "line": 0, "reason": f"cannot read: {exc}"}]
    if b"\x00" in data:
        return []
    text = data.decode("utf-8", errors="replace")
    findings: list[dict[str, object]] = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        for reason, pattern in CHECKS:
            match = pattern.search(line)
            if not match:
                continue
            if reason == "email address":
                domain = match.group(0).rsplit("@", 1)[-1].casefold()
                if domain in EMAIL_ALLOWLIST:
                    continue
            findings.append(
                {
                    "path": path.as_posix(),
                    "line": line_number,
                    "reason": reason,
                }
            )
    return findings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Audit SemanticMemory release content")
    parser.add_argument("paths", nargs="*", default=["."])
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    roots = [Path(value).expanduser().resolve() for value in args.paths]
    files = list(iter_files(roots))
    findings = []
    for path in files:
        findings.extend(audit_file(path))
    payload = {"ok": not findings, "findings": findings, "files": len(files)}
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(f"audited files={payload['files']} findings={len(findings)}")
        for item in findings:
            print(f"ERROR: {item['path']}:{item['line']} {item['reason']}")
    return 0 if not findings else 1


if __name__ == "__main__":
    raise SystemExit(main())
