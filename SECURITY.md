# Security Policy

## Supported Versions

Security fixes target the latest `0.1.x` release until a newer minor line replaces
it.

## Reporting a Vulnerability

Do not open a public issue for a vulnerability or a report containing private data.
Use GitHub's private vulnerability reporting or the repository's private maintainer
channel.

Please include:

- affected version;
- reproduction steps using synthetic data;
- expected and actual behavior;
- security impact;
- a suggested fix if available.

## Data Warning

SemanticMemory stores user-authored Markdown. It does not encrypt the workspace or
provide access control beyond the host filesystem. Keep private workspaces out of
public repositories and shared backups.

## Release Audit

```bash
python scripts/audit_release.py .
```

The audit is a guardrail, not a replacement for code review.
