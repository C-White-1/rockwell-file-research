# Contributing

Thank you for helping improve industrial file-format interoperability.

This project welcomes parser improvements, documentation, controlled synthetic
fixtures, and privacy-preserving evidence. It does not accept customer
projects, production controller backups, login-gated vendor examples, or files
whose redistribution rights are uncertain.

## Before contributing

- Read [Private fixtures and publication policy](PRIVATE_FIXTURES.md).
- Use only systems, software, and files you are authorized to inspect.
- Do not include credentials, network addresses, serial numbers, personal
  information, customer names, plant names, or proprietary logic.
- Do not describe a probable decoding result as confirmed.
- Preserve unknown bytes and fields rather than discarding or guessing them.

## Ways to contribute

### Code and documentation

Open an issue or pull request with a focused change. Parser changes should be
specification-driven or supported by repeatable fixture evidence. Add tests for
accepted and rejected framing, including privacy behavior where relevant.

### Controlled synthetic RSS fixtures

Contributor-created RSS projects are especially valuable. Follow the
[controlled RSS fixture specification](RSS_CONTROLLED_INSTRUCTION_FIXTURES.md)
and use the supplied manifest template.

Before uploading any binary fixture, open an issue containing only:

- the processor family and editor version;
- the instruction or structure being isolated;
- confirmation that the project was created from scratch;
- confirmation that it contains no vendor, customer, or production material;
  and
- the proposed fixture names and parent/child relationships.

Wait for a maintainer to confirm the fixture scope. RSS files are ignored by
default and must not be force-added without documented provenance review.
Accepted fixtures should be minimal, offline-created, unprotected, and paired
with a manifest containing SHA-256 digests and exact edit descriptions.

### Evidence without sharing the source file

If an RSS file cannot legally or safely be redistributed, do not upload it.
Run the inventory tools locally and contribute a redacted report, selector
summary, or minimal reproduction created independently. Review every derived
file before sharing it; hashes do not make sensitive surrounding metadata safe.

## Development setup

Install the locked development environment:

```powershell
uv sync --all-extras --dev
```

Run the complete local quality gate:

```powershell
uv run ruff format --check .
uv run ruff check .
uv run pyright
uv run pytest -q
npx.cmd markdownlint-cli2 "**/*.md"
uv run publication-check
git diff --check
```

## Pull-request expectations

A pull request should:

- explain the evidence and confidence boundary;
- identify any processor-specific assumptions;
- preserve unsupported and unknown content;
- include focused tests;
- update relevant research or coverage documentation;
- pass the quality workflow; and
- contain no private or redistribution-restricted artifacts.

Small, reviewable pull requests are preferred. A contributor must have the
right to submit their work under the repository license.

## Safety and scope

This repository is for read-only interoperability research and offline file
analysis. Contributions that add unauthorized access, credential collection,
control-system modification, or unsafe active scanning are out of scope.
