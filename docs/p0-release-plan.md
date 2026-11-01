# P0 Release Plan: SemanticMemory for ReMe

## Goal

Make the public release installable without colliding with the existing
`semantic-memory` PyPI package, while keeping the product positioned as a ReMe
community companion.

## Release Decisions

- Repository and product name remain `SemanticMemory`.
- PyPI distribution name becomes `semantic-memory-reme`.
- Python import namespace becomes `semantic_memory_reme`.
- CLI commands remain `semantic-memory` and `semantic-memory-mcp`.
- Release version becomes `0.1.1`.
- The project is explicitly described as a community companion, not an official
  ReMe package.

## Tasks

### 1. Package Identity

- [x] Rename the distribution and Python package namespace.
- [x] Update all imports, tests, package data, and documentation.
- [x] Bump the release version to `0.1.1`.

### 2. First-Run Experience

- [x] Add a self-contained `semantic-memory demo` command.
- [x] Show a claim, source evidence, related task, and filtered search result.
- [x] Verify the demo creates no persistent workspace by default.

### 3. Release Automation

- [x] Add a PyPI Trusted Publishing workflow.
- [x] Document the one-time PyPI pending-publisher setup.
- [x] Build a wheel and source distribution from the final commit.

### 4. Public Presentation

- [x] Update English and Chinese READMEs with the ReMe companion positioning.
- [x] Add community-not-official language.
- [x] Update changelog and migration notes.
- [ ] Set GitHub description and topics after merge.

### 5. Verification

- [x] All tests pass.
- [x] `scripts/audit_release.py` reports no findings.
- [x] The wheel installs in a clean environment.
- [x] `semantic-memory demo` works from the installed wheel.
- [ ] Pull request CI passes before merge.

### 6. Publication

- [ ] Merge the release branch.
- [ ] Configure PyPI Trusted Publishing if credentials are available.
- [ ] Create the `v0.1.1` GitHub release after PyPI succeeds.
- [ ] Announce the release in ReMe community channels only after install succeeds.

## Stop Conditions

- A namespace or PyPI conflict is found.
- The release audit reports private content.
- Tests, build, or wheel installation fail.
- PyPI Trusted Publishing is not configured.

## Success Criteria

- A user can install `semantic-memory-reme` from PyPI.
- `semantic-memory demo` gives a complete, inspectable example in under one minute.
- The repository clearly explains the ReMe relationship without implying official
  endorsement.
- The release has reproducible artifacts and a clean audit trail.
