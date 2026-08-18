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

## Development

Install the project and development tools with:

```powershell
uv sync --locked
```

Run the same quality checks used by CI:

```powershell
uv run ruff check rockwell_file_research ccw_report.py convert.py main.py tests
uv run ruff format --check rockwell_file_research ccw_report.py convert.py main.py tests
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
