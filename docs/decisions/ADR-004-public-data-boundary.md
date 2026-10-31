# ADR-004: Public releases contain code and synthetic examples only

## Status

Accepted

## Date

2026-10-31

## Context

The originating SemanticMemory workspace contains private claims, tasks, source
quotes, integrations, and machine-specific configuration. Publishing that directory
directly would leak personal data.

## Decision

The public repository contains source code, schemas, templates, documentation, and
synthetic examples only. It excludes:

- real claims and tasks;
- inbox and archive contents;
- local agent instructions;
- backups and evidence stores;
- machine-specific MCP configuration.

## Enforcement

- `.semantic-memory/` is ignored by Git.
- Tests use temporary directories.
- `scripts/audit_release.py` scans for machine paths and credential-like content.
- Public examples use synthetic names and statements.

## Consequences

- Open-source and private use have separate data lifecycles.
- Users must initialize their own workspace.
- Release review still requires human judgment beyond pattern matching.
