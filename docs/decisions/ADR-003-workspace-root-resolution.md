# ADR-003: Resolve workspaces independently of machine layout

## Status

Accepted

## Date

2026-10-31

## Context

The original standalone scripts lived inside a specific private knowledge vault and
some entry points contained machine-specific defaults. That behavior is unsuitable
for a public package.

## Decision

All public entry points resolve the workspace in this order:

1. `--root`
2. `SEMANTIC_MEMORY_ROOT`
3. `./.semantic-memory`

A missing workspace produces an actionable error that points to
`semantic-memory init`.

## Alternatives Considered

### Require `--root` on every command

Rejected: it makes agent configuration noisy and ignores a useful environment
variable.

### Derive the root from the Python package location

Rejected: installed packages and source trees have no trustworthy relationship to
user data.

## Consequences

- Tests and examples are isolated.
- MCP configuration can be portable across machines.
- Users must initialize or configure a workspace before the first command.
