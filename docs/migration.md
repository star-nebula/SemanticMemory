# Migration from Standalone Scripts

## 0.1.1 Package Rename

The PyPI distribution moved from the unavailable `semantic-memory` name to
`semantic-memory-reme`. To avoid colliding with an unrelated existing Python
package, the import namespace moved from `semantic_memory` to
`semantic_memory_reme`.

The CLI names remain unchanged:

- `semantic-memory`
- `semantic-memory-mcp`

## Mapping

The initial open-source package extracts existing standalone scripts:

| Previous file | Package module |
|---|---|
| `semantic_memory.py` | `semantic_memory_reme.claims` |
| `task_memory.py` | `semantic_memory_reme.tasks` |
| `semantic_memory_mcp.py` | `semantic_memory_reme.mcp` |

The public schema names remain unchanged:

- `semantic-memory/v1`
- `semantic-memory-task/v1`

## Command Migration

Standalone:

```text
python semantic_memory.py search "query" --json
python task_memory.py list
python semantic_memory_mcp.py --read-only
```

Installed package:

```text
semantic-memory search "query" --json
semantic-memory task list
semantic-memory-mcp --read-only
```

## Root Migration

The open-source package does not contain a machine-specific default root. Set one
explicitly:

```text
semantic-memory validate --root .semantic-memory --json
```

or:

```text
SEMANTIC_MEMORY_ROOT=.semantic-memory
semantic-memory validate --json
```

## Source Path Migration

Relative claim source paths resolve from the workspace root. A source stored inside
the workspace uses:

```yaml
sources:
  - path: sources/source.md
    quote: Exact quote
```

A source elsewhere on the same machine can use an absolute path during local
private use. Public examples must not include absolute local paths.

## Processed Candidates

Promoted inbox candidates move to:

```text
<workspace>/archive/processed-candidates/YYYY-MM-DD/
```

This keeps review state inside the private workspace and avoids a second hidden
archive root.

## Compatibility Check

Before switching an existing workflow:

1. copy a small test workspace;
2. run claim and task validation;
3. search representative queries;
4. compare review and lifecycle output;
5. only then change agent instructions or MCP configuration.
