# Releasing

## One-Time PyPI Setup

The distribution name is `semantic-memory-reme`.

Before the first tagged release, configure a PyPI Trusted Publisher with:

| Field | Value |
|---|---|
| PyPI project | `semantic-memory-reme` |
| Owner | `star-nebula` |
| Repository | `SemanticMemory` |
| Workflow | `publish.yml` |
| Environment | `pypi` |

This avoids storing a PyPI token in GitHub.

## Release Sequence

1. Update the version in `pyproject.toml` and `semantic_memory_reme.__version__`.
2. Update `CHANGELOG.md`.
3. Run the full test suite and release audit.
4. Build and install the wheel in a clean environment.
5. Commit and push through a pull request.
6. Create a GitHub release with tag `vX.Y.Z`.
7. Publishing the release triggers `.github/workflows/publish.yml`.
8. Verify the PyPI project and install from PyPI.

## Pre-Release Checks

```bash
python -m unittest discover -s tests -v
python scripts/audit_release.py .
python -m build
```

## Rollback

PyPI files cannot be replaced. If a release is broken:

1. yank the broken files on PyPI;
2. publish a fixed patch version;
3. update the GitHub release notes with the replacement version.
