# ADR-002: Integrate with ReMe without core coupling

## Status

Accepted

## Date

2026-10-31

## Context

SemanticMemory is intended as a ReMe companion project. A direct Python dependency
would couple release cycles, increase installation weight, and make SemanticMemory
harder to use with other evidence systems.

## Decision

SemanticMemory does not import ReMe core code. Integration consists of:

- `reme_ref` as an opaque evidence pointer;
- documentation for the evidence/current-fact workflow;
- independent MCP configuration.

## Alternatives Considered

### Build as a ReMe plugin only

Rejected: it would prevent standalone use and make the current-fact layer dependent
on ReMe internals.

### Add ReMe as an optional Python dependency

Rejected for v0.1: no runtime behavior requires it.

## Consequences

- Each project can release independently.
- Users install ReMe only when they need episodic evidence and search.
- Integration quality depends on stable file references and documented workflow.
