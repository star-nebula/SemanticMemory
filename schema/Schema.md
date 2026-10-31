# SemanticMemory Schema

SemanticMemory stores current facts and tasks as ordinary Markdown files with YAML
frontmatter.

## Claim location

```text
claims/<kind>/<id>.md
```

`kind` is one of `fact`, `preference`, `decision`, `procedure`, `constraint`, or
`rule`. The Markdown body contains a short independently understandable statement.

## Claim frontmatter

```yaml
---
schema: semantic-memory/v1
type: semantic-claim
id: pref-concise-explanations
title: Prefer concise explanations
kind: preference
subject: person:example-user
predicate: preferred_explanation_style
object: concise
scope: global
cardinality: single
status: active
confidence: 0.9
human_review: accepted
review_policy: agent
checked_at: 2026-10-31
check_scope: Source text verified
valid_from: 2026-10-31
valid_to: null
observed_at: 2026-10-31T12:00:00+00:00
updated: 2026-10-31
supersedes: []
superseded_by: null
contradicts: []
tags: [preference]
sources:
  - path: sources/profile.md
    quote: I prefer concise explanations in English.
reme_ref: null
---
```

Every claim requires at least one source with a non-empty `path` and `quote`.
Relative source paths resolve from the workspace root. Absolute paths are allowed
for local private workspaces but should not appear in examples or public issues.

## Lifecycle

```text
pending -> active
active -> superseded | contested | expired | archived
contested -> active | superseded | archived
superseded -> archived
expired -> archived
```

- `superseded` claims require `superseded_by`.
- Supersede relationships must be reciprocal.
- A `single` claim slot can have only one active claim for the same
  `subject + predicate + scope`.
- Claims are never deleted during a normal transition.
- `human_review: pending` is not accepted truth.

## Tasks

Tasks live under `tasks/open/` while active and move to `tasks/done/` when
completed or cancelled. A task contains `project`, `status`, `priority`,
`source`, optional `source_quote`, and optional `claim_ref` fields.

## Workspace root

Commands resolve the root in this order:

1. `--root`
2. `SEMANTIC_MEMORY_ROOT`
3. `./.semantic-memory`

Run `semantic-memory init --root <path>` to create a new workspace.
