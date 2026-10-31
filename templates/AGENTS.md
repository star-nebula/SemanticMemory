# SemanticMemory Agent Instructions

SemanticMemory is the current-fact layer. ReMe is the optional evidence layer.

## Read

- Use `semantic_search` for current claims.
- Use `semantic_get` when the full claim body matters.
- Use `task_list` for actionable work.
- Use ReMe or original files when conversation history or evidence is required.

## Write

- Create claim candidates under `inbox/`, then run
  `semantic-memory add <candidate>`.
- Add tasks with `semantic-memory task add`.
- Never treat `human_review: pending` as accepted truth.
- Never store tokens, cookies, passwords, private keys, or unrelated PII.

## Boundaries

- Do not overwrite user-edited files without explicit permission.
- Do not promote an accepted review decision automatically.
- Keep ReMe integration optional through `reme_ref`; do not import ReMe core.
