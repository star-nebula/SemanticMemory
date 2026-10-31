# ADR-001: Separate the current-fact layer from episodic evidence

## Status

Accepted

## Date

2026-10-31

## Context

ReMe already stores sessions, daily notes, digests, resources, and searchable
evidence. Agents also need a small deterministic set of current facts, decisions,
constraints, and open tasks. Storing those conclusions as more episodic notes leads
to stale duplicates and ambiguous precedence.

## Decision

SemanticMemory is a separate current-fact layer. Claims and tasks live in Markdown
with lifecycle and review metadata. Every claim keeps source evidence and may point
to ReMe with `reme_ref`.

## Alternatives Considered

### Store current facts only inside ReMe

Rejected: the current conclusion would be indistinguishable from historical
discussion and summaries.

### Use a database as the source of truth

Rejected for v0.1: it adds operations and migration cost without improving the core
review workflow.

## Consequences

- Users can inspect and version current facts as plain files.
- ReMe remains the evidence workspace instead of duplicating its role.
- Agents must follow an explicit two-step evidence/current-fact workflow.
