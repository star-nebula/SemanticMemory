# Privacy

## Data Classification

A SemanticMemory workspace can contain:

- personal preferences and constraints;
- business decisions;
- source quotes from private documents;
- open tasks;
- review notes.

Treat the entire workspace as private application data.

## Storage

- Data is plain Markdown and YAML.
- There is no built-in encryption.
- Access control comes from the host filesystem.
- Backups inherit the sensitivity of the source workspace.

## Repository Hygiene

- Keep the default `.semantic-memory/` directory out of Git.
- Keep real source documents out of public repositories.
- Use `examples/minimal` for screenshots, issues, and tests.
- Run `python scripts/audit_release.py .` before publishing.
- Review the audit output manually; pattern matching cannot prove absence of
  sensitive content.

## Agent Instructions

Agent-facing instructions should state:

- search current claims before assuming a fact;
- read original evidence when the claim is disputed or outdated;
- never auto-accept human review;
- never write credentials or unrelated PII.

## Incident Response

If private data is committed:

1. stop pushing or publishing;
2. rotate any exposed credentials;
3. remove the data from the current branch;
4. assess whether history rewriting is needed;
5. notify affected parties when required.

Deleting a file in a later commit does not remove it from Git history.
