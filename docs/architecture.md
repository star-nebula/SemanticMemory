# Architecture

## Layer Boundary

SemanticMemory stores current conclusions, not the full history that produced them.

```text
Original evidence          Current truth             Action
------------------         -----------------         -----------------
ReMe sessions      ---->   claims/*.md        ---->  tasks/*.md
daily notes               sources[].quote           claim_ref
resources                 reme_ref
```

ReMe is optional. Users can supply ordinary Markdown, issue descriptions, or local
documents as evidence instead.

## Source of Truth

- `claims/**/*.md` is authoritative.
- `tasks/open/*.md` and `tasks/done/*.md` are authoritative.
- No generated index or view is required for correctness.
- Search reads Markdown directly.

This keeps the store inspectable, portable, and recoverable without a database.

## Claim Lifecycle

```text
pending -> active
active -> superseded | contested | expired | archived
contested -> active | superseded | archived
superseded -> archived
expired -> archived
```

Normal transitions never delete a claim. Replacing a claim sets reciprocal
`supersedes` and `superseded_by` fields and appends a change record to the body.

## Write Path

1. Validate frontmatter and required fields.
2. Verify source paths and exact quotes.
3. Reject duplicate active single-cardinality slots.
4. Check supersede relationships.
5. Acquire a workspace lock.
6. Write files through atomic replacement.
7. Validate the resulting store.

## Search

The first release uses deterministic substring and field-weighted search. It avoids
an embedding dependency and network calls. A future index must remain rebuildable
from Markdown.

## MCP Boundary

The MCP server is a sidecar, not a daemon. It speaks newline-delimited JSON-RPC 2.0
over stdio:

- read-only mode exposes status, search, read, trace, validation, and task listing;
- write mode exposes claim promotion and task lifecycle operations;
- claim promotion accepts candidates only under the workspace inbox.

The server does not import ReMe.

## Root Resolution

All entry points share `semantic_memory.paths`:

1. explicit `--root`;
2. `SEMANTIC_MEMORY_ROOT`;
3. `./.semantic-memory`.

This prevents library behavior from depending on the machine that built it.

## Known Limits

- The store is single-user and filesystem-oriented.
- There is no encryption or multi-user authorization.
- Search is lexical, not semantic.
- Concurrent writers rely on a local file lock.
- Large-scale performance is not a v0.1 goal.

See [ADR-001](decisions/ADR-001-current-fact-layer.md) and
[ADR-002](decisions/ADR-002-reme-without-core-coupling.md).
