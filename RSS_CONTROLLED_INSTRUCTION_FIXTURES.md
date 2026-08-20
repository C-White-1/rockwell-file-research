# Controlled RSS instruction-fixture specification

## Purpose

This specification defines a minimal, reproducible collection of independently
created RSLogix 500 `.RSS` projects for identifying instruction and operand
fields in the RSS `PROGRAM FILES` payload.

The fixtures are intended for format interoperability research. They must not
contain customer programs, vendor sample logic, production addresses, personal
information, or confidential plant data.

## Required outcome

Deliver a set of valid RSS projects in which each variant differs from its
declared parent by one intentional ladder edit. The set must allow an analyst
to separate:

- instruction identity from operand encoding;
- data-file, element, bit, and member addressing;
- fixed record data from variable-length data;
- serial instruction order from parallel branch structure;
- application changes from editor and online-image changes.

The author is not expected to inspect or interpret binary data. The author must
create the fixtures exactly, record the requested metadata, and verify the
displayed ladder source.

## Tooling

Use one of the following legitimate Rockwell products:

- RSLogix 500;
- RSLogix Micro Starter or Developer;
- another Rockwell product explicitly documented to create ordinary RSLogix
  500-compatible `.RSS` projects.

Do not use a third-party converter to create the primary fixture set. A
converted set may be supplied separately for comparison, with its source and
conversion path identified.

No physical controller or emulator is required. Create the primary set
entirely offline.

## Fixed project configuration

Use one processor target for the entire first set. Preferred order is:

1. MicroLogix 1400 matching the available private evidence;
2. MicroLogix 1100 if the licensed editor does not support the 1400;
3. another supported MicroLogix or SLC 500 target, clearly identified.

Record the exact controller catalogue, series, firmware or OS revision, and
RSLogix product version. Do not change them between variants.

Use these project conventions where the selected target permits them:

| Setting | Required value |
| --- | --- |
| Project name | `TwinForgeRSSFixture` |
| Main ladder file | Default main file, normally `LAD 2` |
| Test rung | First user-editable rung, normally rung `0` |
| Rung comment | Empty |
| Symbols/descriptions | None |
| Password/source protection | None |
| Forces | None |
| Online state | Never connected for the primary set |
| Base data files | Default files created by RSLogix |

If RSLogix prevents any convention, retain its default and document the
deviation rather than working around it.

## Save discipline

Editor bookkeeping and duplicate online/offline images can obscure a small
logical change. Apply the same procedure to every file:

1. Start from the declared parent fixture using **Save As**.
2. Make only the change specified for the child fixture.
3. Verify the project.
4. Save the project.
5. Close RSLogix completely.
6. Reopen the saved fixture.
7. Confirm the intended rung visually.
8. Save without further edits.
9. Close RSLogix completely.
10. Calculate SHA-256 after the application has closed.

Do not open and resave a completed file after its digest has been recorded. If
a correction is required, regenerate the affected child from its declared
parent and replace its metadata record.

## Address conventions

Use addresses that make each component distinguishable:

| Purpose | Preferred address |
| --- | --- |
| Input bit A | `I:0/0` |
| Input bit B | `I:0/1` |
| Binary bit A | `B3:0/0` |
| Binary bit B | `B3:0/1` |
| Binary bit in next word | `B3:1/0` |
| Output bit A | `O:0/0` |
| Integer source A | `N7:0` |
| Integer source B | `N7:1` |
| Integer destination | `N7:2` |
| Timer | `T4:0` |
| Counter | `C5:0` |

Some controllers use target-specific I/O syntax. If the preferred I/O address
is rejected, use the editor's valid default I/O address and record the exact
displayed form. Do not silently substitute another address.

## Phase 0: save-stability controls

These controls reveal differences caused merely by Save As or repeated saves.

<!-- markdownlint-disable MD013 -->

| File | Parent | Intended ladder content or action |
| --- | --- | --- |
| `p00-empty-a.rss` | New project | Empty main ladder except required `END` |
| `p00-empty-b.rss` | `p00-empty-a.rss` | Save As only; no project edit |
| `p00-empty-c.rss` | `p00-empty-b.rss` | Reopen and save only; no project edit |

The software may update timestamps, identifiers, transaction metadata, or
online/offline images. These controls allow such noise to be isolated before
instruction differences are interpreted.

## Phase 1: minimum bit-instruction set

Phase 1 is the minimum useful delivery. Every file contains exactly one test
rung followed by the normal end-of-program structure.

| File | Parent | Exact test rung |
| --- | --- | --- |
| `p01-xic-b3-0-0.rss` | `p00-empty-a.rss` | `XIC B3:0/0` followed by `OTE O:0/0` |
| `p01-xic-b3-0-1.rss` | `p01-xic-b3-0-0.rss` | Change only XIC operand to `B3:0/1` |
| `p01-xic-b3-1-0.rss` | `p01-xic-b3-0-0.rss` | Change only XIC operand to `B3:1/0` |
| `p01-xio-b3-0-0.rss` | `p01-xic-b3-0-0.rss` | Change only `XIC` to `XIO` |
| `p01-ote-b3-0-0.rss` | `p01-xic-b3-0-0.rss` | Change only output operand to `B3:0/0` |
| `p01-otl-b3-0-0.rss` | `p01-ote-b3-0-0.rss` | Change only `OTE` to `OTL` |
| `p01-otu-b3-0-0.rss` | `p01-ote-b3-0-0.rss` | Change only `OTE` to `OTU` |

The first rung is a two-instruction rung because RSLogix normally requires an
output-side instruction. Identity conclusions must therefore be based on
localized differences between parent and child, not on the entire rung.

## Phase 2: order and branch structure

| File | Parent | Exact test rung |
| --- | --- | --- |
| `p02-series-a.rss` | `p01-xic-b3-0-0.rss` | `XIC B3:0/0`, `XIC B3:0/1`, `OTE O:0/0` in series |
| `p02-series-reversed.rss` | `p02-series-a.rss` | Swap only the two XIC positions |
| `p02-parallel-a.rss` | `p02-series-a.rss` | Put the two XIC instructions on parallel legs feeding one OTE |
| `p02-parallel-xio.rss` | `p02-parallel-a.rss` | Change only the second branch-leg XIC to XIO |
| `p02-nested-branch.rss` | `p02-parallel-a.rss` | Add one nested branch containing `XIC B3:1/0` |

Include a screenshot or report for each branch fixture. Text alone can be
ambiguous about branch topology.

## Phase 3: data handling and constants

Place an enabling `XIC B3:0/0` before each instruction unless RSLogix permits
and preserves an unconditional rung. Use the same choice throughout the phase.

| File | Parent | Instruction under test |
| --- | --- | --- |
| `p03-mov-a.rss` | Phase 0 baseline | `MOV N7:0 N7:2` |
| `p03-mov-source.rss` | `p03-mov-a.rss` | Change only source to `N7:1` |
| `p03-mov-destination.rss` | `p03-mov-a.rss` | Change only destination to `N7:1` |
| `p03-mov-constant-1.rss` | `p03-mov-a.rss` | Change only source to constant `1` |
| `p03-mov-constant-2.rss` | `p03-mov-constant-1.rss` | Change only constant to `2` |
| `p03-add-a.rss` | Phase 0 baseline | `ADD N7:0 N7:1 N7:2` |
| `p03-add-source-b.rss` | `p03-add-a.rss` | Change only second source to constant `1` |
| `p03-sub-a.rss` | `p03-add-a.rss` | Change only `ADD` to `SUB` |

Record the operand order exactly as displayed by RSLogix. Do not normalize it
to another PLC language.

## Phase 4: timer and counter structures

| File | Parent | Instruction under test |
| --- | --- | --- |
| `p04-ton-5s.rss` | Phase 0 baseline | Enabled `TON T4:0`, time base `1.0`, preset `5`, accumulator `0` |
| `p04-ton-6s.rss` | `p04-ton-5s.rss` | Change only preset from `5` to `6` |
| `p04-tof-5s.rss` | `p04-ton-5s.rss` | Change only `TON` to `TOF` where accepted |
| `p04-rto-5s.rss` | `p04-ton-5s.rss` | Change only `TON` to `RTO` where accepted |
| `p04-ctu-3.rss` | Phase 0 baseline | Enabled `CTU C5:0`, preset `3`, accumulator `0` |
| `p04-ctu-4.rss` | `p04-ctu-3.rss` | Change only preset from `3` to `4` |
| `p04-ctd-3.rss` | `p04-ctu-3.rss` | Change only `CTU` to `CTD` where accepted |
| `p04-res-t4-0.rss` | Phase 0 baseline | Enabled `RES T4:0` |
| `p04-res-c5-0.rss` | `p04-res-t4-0.rss` | Change only operand to `C5:0` |

If RSLogix derives or displays timer values differently for the selected
processor, record every displayed field in the manifest and report.

## Phase 5: comparison and program control

This phase is optional until Phases 0 through 4 have been validated.

| File | Parent | Instruction under test |
| --- | --- | --- |
| `p05-equ-a.rss` | Phase 0 baseline | `EQU N7:0 N7:1` controlling `OTE O:0/0` |
| `p05-equ-constant.rss` | `p05-equ-a.rss` | Change only second operand to `1` |
| `p05-neq-a.rss` | `p05-equ-a.rss` | Change only `EQU` to `NEQ` |
| `p05-les-a.rss` | `p05-equ-a.rss` | Change only `EQU` to `LES` |
| `p05-gtr-a.rss` | `p05-equ-a.rss` | Change only `EQU` to `GRT` |
| `p05-jsr-a.rss` | Phase 0 baseline | `JSR` to an otherwise empty ladder file 3 |

<!-- markdownlint-enable MD013 -->

Program-control fixtures may change headers and file catalogues as well as the
test rung. Their parent relationship and extra program file must therefore be
described explicitly.

## Source-intent evidence

For every fixture, provide at least one of:

- a Rockwell-generated project or ladder report;
- a screenshot showing the complete test rung and project tree;
- a print-to-PDF ladder view.

Reports are preferred. The evidence filename should share the RSS stem, for
example:

```text
p01-xio-b3-0-0.rss
p01-xio-b3-0-0.pdf
```

Screenshots must include the program-file number and rung number. Do not crop
away operand text or branch rails.

## Manifest

Provide `manifest.csv` with one row per RSS file and these columns:

```text
fixture_id,parent_fixture,filename,sha256,project_name,rslogix_product,
rslogix_version,controller_catalog,controller_series,controller_revision,
program_file,displayed_rung_number,intended_change,displayed_source,
verified,created_at,creator,online_state,publishable,notes
```

Requirements:

- `fixture_id` is the filename without `.rss`.
- `parent_fixture` is blank only for the initial new project.
- `sha256` is lowercase hexadecimal calculated after RSLogix closes.
- `displayed_source` is a faithful transcription, not translated syntax.
- `verified` is `true` only after RSLogix project verification succeeds.
- `created_at` uses ISO 8601 with timezone.
- `online_state` is `offline` for the primary set.
- `publishable` records explicit permission; use `false` when uncertain.
- Deviations and editor-generated changes belong in `notes`.

Also provide `README.md` identifying the fixture-set licence and any
redistribution restriction. Do not assign a public licence unless the creator
owns all fixture content and is authorized to do so.

Copy the ready-to-fill files from
[`templates/rss-controlled-fixtures`](templates/rss-controlled-fixtures):

- `manifest.csv` contains the required column header;
- `README.template.md` contains the provenance, tooling, licence, and author
  confirmation sections. Rename it to `README.md` in the delivered set.

## Delivery layout

```text
rss-controlled-fixtures/
├── README.md
├── manifest.csv
├── phase-00-controls/
├── phase-01-bit/
├── phase-02-branches/
├── phase-03-data/
├── phase-04-timer-counter/
├── phase-05-comparison-control/
└── source-intent-evidence/
```

Do not include temporary files, automatic backups, activation data, crash
dumps, workstation configuration, or unrelated project exports.

## Author validation checklist

Before delivery, confirm:

- Every RSS file opens without repair or conversion prompts.
- Project verification succeeds, or the exact expected diagnostic is recorded.
- Each child was created from its declared parent.
- Each child has only its declared intentional ladder change.
- Project target and RSLogix version remain constant.
- Every file has source-intent evidence.
- Every SHA-256 matches the delivered file.
- The manifest contains no blank required fields.
- No project was connected to a physical controller.
- No customer, production, or vendor sample content is present.
- Publication permission is explicit rather than assumed.

## Analyst acceptance checklist

Run the package-level contract check before inspecting any RSS internals:

```powershell
uv run rss-fixture-check path\to\delivery\manifest.csv
```

The command checks required columns and values, safe relative RSS paths,
filenames, file presence, SHA-256 digests, timestamps, booleans, offline state,
unique identifiers, parent existence, a single root, and parent cycles. It does
not parse or expose RSS contents.

The receiving analyst should:

1. Recalculate every file digest and validate the manifest.
2. Inventory the OLE streams without modifying the files.
3. Validate and decompress each `PROGRAM FILES` payload.
4. Confirm program-file and rung boundaries independently.
5. Measure save-only noise using Phase 0.
6. Compare each child only with its declared parent first.
7. Separate mnemonic changes from operand changes.
8. Preserve all unknown bytes and records.
9. Record processor and RSLogix-version applicability with every mapping.
10. Promote mappings according to the confidence and acceptance rules in
    [RSS instruction-decoding research](RSS_INSTRUCTION_DECODING_RESEARCH.md).

## Minimum engagement

If access to RSLogix is brief or paid by the hour, request these files first:

1. `p00-empty-a.rss`
2. `p00-empty-b.rss`
3. `p01-xic-b3-0-0.rss`
4. `p01-xic-b3-0-1.rss`
5. `p01-xio-b3-0-0.rss`
6. `p01-ote-b3-0-0.rss`
7. `p02-series-a.rss`
8. `p02-parallel-a.rss`
9. `p03-mov-a.rss`
10. `p03-mov-source.rss`
11. `p04-ton-5s.rss`
12. `p04-ton-6s.rss`

This twelve-file subset provides save controls, instruction identity changes,
operand changes, serial/parallel topology, a multi-operand instruction, and a
structured timer instruction.
