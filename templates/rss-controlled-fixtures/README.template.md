# Controlled RSS fixture delivery

## Fixture-set identity

- Set identifier: `TODO`
- Creator: `TODO`
- Created: `TODO: ISO 8601 date with timezone`
- Organization: `TODO or not applicable`
- Contact: `TODO or intentionally omitted`

## Toolchain

- Rockwell product: `TODO`
- Exact software version: `TODO`
- Controller catalogue: `TODO`
- Controller series: `TODO`
- Controller firmware or OS revision: `TODO`
- Host operating system: `TODO`

## Creation conditions

- All primary fixtures were created offline: `TODO: true or false`
- No physical controller was connected: `TODO: true or false`
- Every project was verified before delivery: `TODO: true or false`
- Save, close, reopen, confirm, and final-save procedure used:
  `TODO: true or false`
- Deviations from the fixture specification: `TODO or none`

## Contents

List the phases and fixture files supplied:

- Phase 0 save-stability controls: `TODO`
- Phase 1 bit instructions: `TODO`
- Phase 2 order and branches: `TODO`
- Phase 3 data handling and constants: `TODO`
- Phase 4 timers and counters: `TODO`
- Phase 5 comparisons and program control: `TODO`
- Source-intent reports or screenshots: `TODO`

`manifest.csv` is the authoritative file inventory. Its SHA-256 values were
calculated only after RSLogix had closed.

## Provenance

Describe how the fixtures were created and confirm that they contain no
customer logic, vendor sample logic, production addresses, plant identifiers,
credentials, or other confidential information.

`TODO`

## Licence and publication

- Fixture-set copyright owner: `TODO`
- Licence: `TODO`
- Public redistribution permitted: `TODO: yes or no`
- Restrictions: `TODO or none`

Do not infer permission from possession of the files. If publication authority
is uncertain, mark the set private until reviewed.

## Known issues

Record verification warnings, unsupported instructions, substituted I/O
addresses, unexpected save changes, or missing evidence.

`TODO or none`

## Author confirmation

Before handoff, run:

```powershell
uv run rss-fixture-check manifest.csv
```

- [ ] Every RSS file opens without repair or conversion prompts.
- [ ] Every child was created from its declared parent.
- [ ] Every child contains only its declared intentional ladder edit.
- [ ] Every file has matching source-intent evidence.
- [ ] Every SHA-256 value has been rechecked.
- [ ] The manifest contains no blank required fields.
- [ ] No customer, production, or vendor sample content is present.
- [ ] Publication permission is recorded explicitly.
