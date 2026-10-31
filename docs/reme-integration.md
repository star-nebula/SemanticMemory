# Using SemanticMemory with ReMe

## Responsibility Split

Use ReMe when you need to know what happened:

- original conversation;
- timeline and discussion context;
- daily and digest notes;
- resources and linked evidence.

Use SemanticMemory when you need to know what the agent should currently believe or
do:

- an accepted decision;
- a stable preference;
- a current constraint;
- an open task.

## Recommended Workflow

1. Search ReMe for evidence.
2. Read the original passage instead of relying only on a summary.
3. Search SemanticMemory for an existing active claim.
4. Create a candidate claim under `inbox/`.
5. Include an exact source quote and optional `reme_ref`.
6. Promote the candidate with `semantic-memory add`.
7. Record human review only after an explicit decision.

## Evidence Pointer

`reme_ref` is opaque to SemanticMemory:

```yaml
reme_ref: reme/daily/2026-10-31/example.md
sources:
  - path: sources/transcript.md
    quote: The exact supporting sentence.
```

The source quote is still required. `reme_ref` helps a human or agent find context;
it is not a substitute for local verifiable evidence.

## Workspace Placement

You can keep SemanticMemory beside a ReMe workspace:

```text
project/
  .reme/
  .semantic-memory/
  reme/
```

Set `SEMANTIC_MEMORY_ROOT=.semantic-memory` in the agent environment if the MCP
client does not run from the project root.

## MCP Configuration

```json
{
  "mcpServers": {
    "semantic-memory": {
      "command": "semantic-memory-mcp",
      "args": ["--root", ".semantic-memory", "--read-only"]
    }
  }
}
```

Install and operate ReMe separately. SemanticMemory does not start, configure, or
modify ReMe.

## Failure Modes

- Treating a ReMe digest as an accepted fact without checking its source.
- Writing a claim without an exact quote.
- Storing a conversation transcript as the claim body.
- Importing ReMe core code into SemanticMemory.
- Letting an agent mark `human_review: pending` as accepted without a user decision.
