# Contributing

Thanks for improving SemanticMemory.

## Development Setup

```bash
python -m pip install -e ".[dev]"
python -m unittest discover -s tests -v
```

## Pull Requests

- Keep each pull request focused on one behavior or documentation change.
- Add or update tests for behavior changes.
- Update `CHANGELOG.md` when user-visible behavior changes.
- Run the full test suite and release audit before submitting.
- Explain why the change is needed in the pull request description.

```bash
python -m unittest discover -s tests -v
python -m build
python scripts/audit_release.py .
```

## Data Safety

Never submit real personal memory, claims, tasks, sessions, credentials, customer
data, private repository names, or machine-specific paths. Use synthetic fixtures
under `examples/minimal` or `tests/`.

## Schema Changes

Schema changes require:

1. an ADR under `docs/decisions/`;
2. a migration note;
3. updated JSON Schema files;
4. backward-compatibility tests;
5. an update to both README files when user-facing behavior changes.

## Commit Style

Use focused commit messages:

```text
feat: add claim validity maintenance
fix: reject candidate paths outside inbox
docs: explain ReMe evidence pointers
test: cover read-only MCP behavior
```

## Code Style

- Python 3.11+ with type annotations.
- Prefer `pathlib.Path`.
- Keep public functions small and explicit.
- Use atomic writes for data changes.
- Do not add a runtime dependency without an ADR and maintainer approval.
