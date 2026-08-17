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

The command writes:

- `report.json`, containing normalized inventories and every non-empty source
  workbook cell under `raw_sheets`;
- `tags.csv`;
- `screens.csv`;
- `screen_objects.csv`; and
- `alarms.csv`.

The CCW workbook remains the authoritative source. Normalized fields are
convenience views and do not replace the retained raw evidence.

## Development

Install the project and development tools with:

```powershell
uv sync --locked
```

Run the same quality checks used by CI:

```powershell
uv run ruff check ccw_report.py convert.py main.py tests
uv run ruff format --check ccw_report.py convert.py main.py tests
uv run pyright
uv run pytest
```

VS Code recommends the Python, Pylance, Ruff, and TOML extensions when this
folder is opened. Pylance provides editor diagnostics; Pyright performs the
equivalent reproducible command-line and CI type check.
