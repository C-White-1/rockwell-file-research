# Rockwell file-format research

> [!IMPORTANT]
> Vendor-supplied inputs and material derived from them remain local. See
> [Private fixtures and publication policy](PRIVATE_FIXTURES.md) before adding
> files to Git.

This project keeps exploratory Rockwell tooling separate from TwinForge.

## ACD database extraction

`acd-tools` is installed only in this project. Update the input and output paths
in `convert.py`, then run:

```powershell
uv run python convert.py
```

The extractor accepts Studio 5000 `.ACD` projects and writes their contained
database files to a directory. The installed `acd-tools` API does not convert
an ACD project into L5X. It also does not accept RSLogix 500 `.RSS` projects or
PanelView `.cha` applications.

## CCW report extraction

Connected Components Workbench can generate an Excel report for a PanelView
application. Extract its evidence with:

```powershell
uv run python ccw_report.py `
  "private-fixtures\ccw-report.xlsx" `
  --output "private-outputs\ccw-report"
```

The installed console command is equivalent:

```powershell
uv run ccw-report `
  "private-fixtures\ccw-report.xlsx" `
  --output "private-outputs\ccw-report"
```

Install the optional validator and require the generated report to conform to
the packaged JSON Schema:

```powershell
uv sync --extra validation
uv run ccw-report `
  "private-fixtures\ccw-report.xlsx" `
  --output "private-outputs\ccw-report" `
  --validate
```

For privacy, source provenance stores only the workbook filename, never its
absolute directory path. Replace even that filename with a neutral identifier
when sharing a report:

```powershell
uv run ccw-report INPUT.xlsx `
  --output OUTPUT `
  --source-label fixture-001
```

The source size and SHA-256 digest remain available for integrity comparison.

The command writes:

- `report.json`, containing normalized inventories and every non-empty source
  workbook cell under `raw_sheets`;
- `tags.csv`;
- `screens.csv`;
- `screen_objects.csv`; and
- `alarms.csv`.

`report.json` also contains diagnostics listing recognized and unrecognized
report sections. Unsupported top-level sections remain available under
`raw_sheets`; they are not silently discarded. Invalid XLSX packages and
workbooks missing the required CCW tag, screen, or communication reports fail
with a concise command-line error. Worksheets are located by their semantic
report headings rather than incidental names such as `Sheet1` or `Sheet7`.
Tables are likewise mapped from their visible header labels, including CCW's
two-level tag headings, rather than fixed row and column coordinates.
Declarative section contracts distinguish a genuinely empty table from an
unsupported table layout. Required tag, screen, and communication schema drift
is rejected; optional alarm drift is retained with an explicit warning.

The CCW workbook remains the authoritative source. Normalized fields are
convenience views and do not replace the retained raw evidence.

## RSLogix 500 RSS structural inventory

RSLogix 500 `.RSS` projects are OLE compound files rather than L5X documents.
Create a read-only structural inventory with:

```powershell
uv run rss-inventory `
  "private-fixtures\controller.rss" `
  --output "private-outputs\controller-inventory.json" `
  --source-label fixture-001
```

The inventory records source and stream SHA-256 digests, standard compound-file
timestamps, OLE storages, stream names and sizes, recognized RSS section
presence, and unknown streams. It deliberately does not export stream payloads,
ladder logic, data-table values, symbols, comments, controller addresses, or
other proprietary project content. Unknown streams are listed rather than
discarded so later research can extend the reader without losing coverage.

Vendor RSS projects and verbatim extracts remain private. Tests use only an
in-memory synthetic compound document.

The `PROCESSOR` section receives conservative additional treatment. Printable
regions are catalogued by classification, byte offset, length, and SHA-256,
but their text is redacted by default. For authorized local research only,
include the decoded text explicitly:

```powershell
uv run rss-inventory PRIVATE.rss `
  --output "private-outputs\rss\private-inventory.json" `
  --source-label private-fixture-001 `
  --include-private-text
```

Keep that output private: processor text may include project identifiers,
workstation names, communication drivers, routes, and controller addresses.
The classifications are observed evidence, not a claimed complete Rockwell
format specification.

The `DATA FILES` and `Extensional DATA FILES` sections use a verified 16-byte
length envelope followed by zlib-compressed data. The reader validates both
declared compressed and uncompressed lengths before cataloguing evidence.
Standard data-file labels and application text are recorded by offset, length,
classification, and SHA-256; text remains redacted unless
`--include-private-text` is supplied. Data-file numbers, element counts, values,
and PanelView address resolution are intentionally deferred until their binary
record boundaries are supported by repeatable evidence.

Data-file catalogue candidates use independently decoded standard and
extensional sections. A record is identified by its length-prefixed file number,
description, name, and nearby `03 80` marker. TwinForge reports whether both
sections produce the same ordered identities and count candidates. Names and
descriptions remain private-text fields; their hashes allow comparison in the
redacted inventory.

## PLC–HMI cross-reference

Correlate PanelView tag addresses from a CCW XLSX report with the data-file
catalogue recovered from an RSLogix 500 RSS project:

```powershell
uv run plc-hmi-cross-reference panelview-report.xlsx controller.RSS `
  --output private-outputs/plc-hmi-cross-reference.json `
  --markdown-output private-outputs/plc-hmi-cross-reference.md `
  --hmi-source-label hmi-001 `
  --plc-source-label plc-001
```

The output resolves explicit data files such as `N17:0` and standard implicit
files such as `O:0/1`. Tag names, addresses, and RSS record names are replaced
by SHA-256 evidence by default. Use `--include-private-text` only for output
that will remain private. Unsupported and unresolved addresses are retained
with an explicit status; resolution proves the shared data-file number, not
yet element-level use by ladder logic.

Element selectors are also normalized into element, bit, and member fields.
Cross-artifact evidence showed that a numeric field recovered near each RSS
record is not the data-file element count: valid HMI element references exceed
it. The field is therefore retained as `unknown_numeric_candidate`, with the
contradiction recorded rather than assigning unsupported semantics.

Exact tag-name references from screen objects and alarm triggers are attached
as consumers of each PLC binding. The summary distinguishes visualization and
alarm references and reports tags with no such consumer. CCW table labels such
as `Read Tag` and `Write Tag`, plus `-` placeholders, are excluded as report
structure rather than treated as unresolved project references.

The RSS `PROGRAM FILES` section is validated through its declared zlib
envelope and catalogued for length-delimited operand strings. Cross-reference
bindings distinguish exact equivalent addresses from weaker contained-bit
evidence, where an HMI whole-word address contains ladder bit operands. Each
match retains the PROGRAM FILES byte offset, zero-based rung index, rung byte
range, and integrity digest. This proves operand occurrence and rung scope in
the ladder payload, but does not yet claim instruction type, execution order,
or runtime behavior.

Observed ladder-file headers are recovered through their serialization marker,
byte-aligned name, optional header span, file number, and length-declared
description. Declared rung counts are corroborated against recurring
`CRung`/`CBranchLeg` class-reference markers across the PF4 and PF525 evidence;
the `MAIN` files additionally begin at their initial `CRung` class declaration.
Only corroborated boundaries are used to scope operands to a rung index and
byte range. Instruction opcodes and rung semantics remain uninterpreted.

RSS inventory schema `rss-inventory/v3` also emits one evidence-only record per
corroborated rung. Each record contains its program-file identity, zero-based
rung index, byte range and length, payload SHA-256, and direct/indirect operand
counts. Printable non-operand regions within the same byte range are attached
as untyped application-text candidates with their own offsets and hashes. They
may represent constants, expressions, labels, configuration strings, or
comments; TwinForge does not collapse those possibilities into a guessed
meaning. The record deliberately contains neither reconstructed ladder source
nor guessed instruction semantics.

Cross-reference schema `rockwell-file-research.plc-hmi-cross-reference.v3`
adds a rung index alongside rung-aware coverage metrics. It reports the number
of ladder program files
and distinct rungs referenced by exact HMI address matches, verifies how many
matched occurrences have rung scope, and provides a distinct-rung count for
each RSS data-file usage row. Each rung-index row groups exact bindings,
operand occurrences, direct/indirect counts, HMI consumer totals, and privacy-
aware tag identities. These are evidence-coverage measurements, not a claim
that every referenced rung controls an operator-facing function.

## Development

Install the project and development tools with:

```powershell
uv sync --locked
```

Run the same quality checks used by CI:

```powershell
uv run ruff check rockwell_file_research ccw_report.py convert.py main.py tests
uv run ruff format --check rockwell_file_research ccw_report.py convert.py `
  main.py tests
uv run pyright
uv run pytest
```

VS Code recommends the Python, Pylance, Ruff, and TOML extensions when this
folder is opened. Pylance provides editor diagnostics; Pyright performs the
equivalent reproducible command-line and CI type check.

Before committing or publishing, verify that Git is not tracking private
industrial artifacts:

```powershell
uv run publication-check
```

The guard inspects the Git index, including staged files. It does not inspect
or reject legitimate local files that remain ignored by Git.
