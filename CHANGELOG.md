# Changelog

All notable changes to this project are documented here.

## [Unreleased]

## [0.1.1] - 2026-11-01

### Changed

- Renamed the PyPI distribution to `semantic-memory-reme` to avoid the existing
  `semantic-memory` package.
- Renamed the Python import namespace to `semantic_memory_reme`.
- Clarified that SemanticMemory is a community ReMe companion, not an official
  ReMe package.

## [0.1.0] - 2026-10-31

### Added

- Evidence-first Markdown claim store.
- Markdown task store.
- Unified `semantic-memory` CLI with workspace initialization.
- Read-only and write-enabled MCP stdio sidecar.
- Claim and task JSON Schema files.
- Synthetic minimal workspace.
- ReMe evidence-pointer integration guide.
- Release audit, security policy, contribution guide, and CI.

### Security

- Candidate claim promotion is limited to the workspace inbox in MCP write mode.
- Release audit blocks machine-specific paths, private key markers, credential
  assignments, and non-example email addresses.
