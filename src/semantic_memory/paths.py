"""Workspace path resolution shared by the CLI, stores, and MCP sidecar."""

from __future__ import annotations

import os
from pathlib import Path

from .errors import WorkspaceError

ENV_ROOT = "SEMANTIC_MEMORY_ROOT"
DEFAULT_DIRECTORY = ".semantic-memory"
WORKSPACE_DIRECTORIES = (
    "claims",
    "tasks/open",
    "tasks/done",
    "inbox",
    "archive",
)


def default_root() -> Path:
    raw = os.environ.get(ENV_ROOT) or DEFAULT_DIRECTORY
    return Path(raw).expanduser().resolve()


def resolve_workspace_root(value: str | Path | None = None, *, must_exist: bool = True) -> Path:
    root = Path(value).expanduser().resolve() if value else default_root()
    if must_exist and not root.is_dir():
        raise WorkspaceError(
            f"workspace does not exist: {root}. Run `semantic-memory init --root {root}` first."
        )
    return root


def init_workspace(value: str | Path | None = None) -> Path:
    root = resolve_workspace_root(value, must_exist=False)
    if root.exists() and not root.is_dir():
        raise WorkspaceError(f"workspace path is not a directory: {root}")
    for relative in WORKSPACE_DIRECTORIES:
        (root / relative).mkdir(parents=True, exist_ok=True)
    readme = root / "README.md"
    if not readme.exists():
        readme.write_text(
            "# SemanticMemory workspace\n\n"
            "This directory stores claims, tasks, review candidates, and processed candidates.\n"
            "Treat it as private application data.\n",
            encoding="utf-8",
            newline="\n",
        )
    gitignore = root / ".gitignore"
    if not gitignore.exists():
        gitignore.write_text(
            "# Keep private SemanticMemory data out of a parent repository.\n"
            "*\n"
            "!.gitignore\n",
            encoding="utf-8",
            newline="\n",
        )
    return root
