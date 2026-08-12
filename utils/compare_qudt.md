# QUDT vs CODATA Constants Comparison Utility (`compare_qudt.py`)

The `compare_qudt.py` utility is a dedicated tool for fetching, caching, comparing, and auditing physical constant values published in RDF/Turtle format by [QUDT](https://qudt.org/) (e.g. `https://qudt.org/3.5.0/vocab/constant`) against the official values digitized in `codata_constants.json`.

## Purpose

While QUDT provides extensive ontologies for quantities, units, and constants, many physical constant values in QUDT release vocabularies remain pinned to older CODATA releases (such as CODATA 2006 or 2018).

This utility:
1. Performs a side-by-side comparison of QUDT values vs official CODATA 2022 values.
2. Identifies whether QUDT values are up to date or outdated.
3. Automatically searches historical CODATA releases (1998–2022) to determine which specific CODATA release QUDT is using.
4. Caches remote Turtle files locally for high performance.
5. Exports reports in terminal ASCII, Markdown, HTML, CSV, and JSON formats.

## Features

### 1. Smart Local Caching
- Downloads `https://qudt.org/3.5.0/vocab/constant` and caches it in `utils/cache/qudt_constants_constant.ttl`.
- Reuses local cache for subsequent runs unless `--refresh` is supplied.

### 2. RDF & JSON Entity Matching
- Uses `rdflib` to parse `qudt:PhysicalConstant` entities.
- Maps `qudt:quantityValue` literal values, standard uncertainties, and units.
- Matches entities against `quantities` -> `constants` -> `ids['QUDT']` in `codata_constants.json`.

### 3. Historical Release Matching Engine
- Uses floating point precision comparison (`math.isclose`) to account for scientific notation differences.
- When a QUDT value differs from CODATA 2022, it iterates across historical releases (`2018`, `2014`, `2010`, `2006`, `2002`, `1998`) to tag the exact release source (e.g. "Matches CODATA 2006").

### 4. Multiple Output Formats
- **Terminal** (`--format terminal`): Formatted side-by-side table with summary metrics.
- **Markdown** (`--format markdown`): GitHub Flavored Markdown report.
- **HTML** (`--format html`): Self-contained styled HTML document.
- **CSV / JSON** (`--format csv|json`): Machine-readable tabular or structured output.

## Command Line Usage

Run via `uv` or directly via Python:

```bash
# Via uv CLI entrypoint
uv run codata-compare-qudt [options]

# Directly via Python
python3 utils/compare_qudt.py [options]
```

### CLI Arguments

| Argument | Description | Default |
|---|---|---|
| `--codata-json` | Path to `codata_constants.json` | `utils/codata_constants.json` |
| `--qudt-url` | QUDT Turtle vocabulary URL | `https://qudt.org/3.5.0/vocab/constant` |
| `--cache-dir` | Directory for cached Turtle files | `utils/cache` |
| `--refresh` | Force re-downloading QUDT Turtle file | `False` |
| `--format` | Output format (`terminal`, `markdown`, `html`, `csv`, `json`) | `terminal` |
| `--outdated-only` | Filter output to show only outdated/mismatched constants | `False` |
| `--version` | Target CODATA version to compare against | `2022` |
| `--output` | Write report output to specified file path | `stdout` |

### Examples

```bash
# Display outdated constants in terminal table
uv run codata-compare-qudt --outdated-only

# Generate Markdown report artifact
uv run codata-compare-qudt --format markdown --output qudt_report.md

# Generate HTML report
uv run codata-compare-qudt --format html --output qudt_report.html

# Force re-fetching Turtle file from qudt.org
uv run codata-compare-qudt --refresh
```
