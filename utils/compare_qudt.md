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

### 1. Smart Local Storage
- Downloads `https://qudt.org/3.5.0/vocab/constant` and stores it directly in `utils/qudt_constants_constant.ttl`.
- Reuses local file for subsequent runs unless `--refresh` is supplied.

### 2. Dual-Key Crosswalk & Entity Matching
- Uses `rdflib` to parse `qudt:PhysicalConstant` entities.
- Extracts both the **Subject Local ID** (e.g., `ReducedPlanckConstant`) and the **`qudt:quantityValue` Value Node Local ID** (e.g., `PlanckConstantOver2Pi` from `constant:Value_PlanckConstantOver2Pi`).
- Crosswalks both key variants against `quantities` -> `constants` -> `ids['QUDT']` in `codata_constants.json`, ensuring aliases like `PlanckConstantOver2Pi` map correctly to `ReducedPlanckConstant`.

### 3. Historical Release Matching Engine
- Uses floating point precision comparison (`math.isclose`) to account for scientific notation differences.
- When a QUDT value differs from CODATA 2022, it iterates across historical releases (`2018`, `2014`, `2010`, `2006`, `2002`, `1998`) to tag the exact release source (e.g. "Matches CODATA 2006").

### 4. Dynamic Runtime Alias Detection Engine (Zero Hardcoding)
- **Layer 1 (Shared Value Node)**: Detects when multiple QUDT subjects share the same `qudt:quantityValue` RDF node (e.g. `Value_PlanckConstantOver2Pi` or `Value_MagneticConstant`).
- **Layer 2 (Normalized Pattern Matching)**: Normalizes subject IDs and labels (lowercased, alphanumeric, dot/kpa standardizations) and matches against all CODATA constant IDs and names at runtime.
- **Layer 3 (Cross-Release Numerical Matching)**: Dynamically checks literal QUDT values against all historical CODATA release values (2022, 2018, 2014, 2010, 2006, 1998) using floating point tolerance (`math.isclose`).
- **Audit Reports**: Generates dedicated **"QUDT Constants with Multiple Entries / Aliases"** sections across all output formats.

### 5. RDF Turtle & Companion Markdown Export Engine
- Produces and exports an updated version of the QUDT Turtle file (e.g. `qudt_constants_constant.2022.ttl`) with the latest CODATA constant values (`qudt:value`, `qudt:valueSN`) and standard uncertainties (`qudt:standardUncertainty`, `qudt:standardUncertaintySN`).
- **In-File Changelog Header**: Formats a human-readable changelog header directly at the top of the exported Turtle file with release statistics and list of updated constant IDs, old values, new values, and previous releases.
- **Machine-Readable Semantic Annotations**: Annotates every updated `qudt:PhysicalConstant` entity and `qudt:ConstantValue` node with `skos:changeNote` and `dcterms:modified`.
- **Ontology Metadata**: Updates ontology `<http://qudt.org/3.5.0/vocab/constant>` with `owl:versionInfo`, `skos:changeNote`, `rdfs:comment`, and `dcterms:modified`.
- **Companion Markdown Change Document**: Automatically generates an update log (e.g. `qudt_constants_constant.2022.md`) that documents every updated physical constant with relative percentage deltas, uncertainty comparisons, release origins, and SPARQL audit queries.

### 6. Multiple Output Formats
- **Terminal** (`--format terminal`): Formatted side-by-side table with summary metrics and alias table.
- **Markdown** (`--format markdown`): GitHub Flavored Markdown report with multi-entry table.
- **HTML** (`--format html`): Self-contained styled HTML document with interactive cards and tables.
- **CSV / JSON** (`--format csv|json`): Machine-readable tabular or structured output including `qudt_aliases` arrays and `multi_entry_groups`.

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
| `--cache-dir` | Directory for downloaded/exported Turtle files | `utils/` |
| `--refresh` | Force re-downloading QUDT Turtle file | `False` |
| `--format` | Output format (`terminal`, `markdown`, `html`, `csv`, `json`) | `terminal` |
| `--outdated-only` | Filter output to show only outdated/mismatched constants | `False` |
| `--version` | Target CODATA version to compare against | `2022` |
| `--output` | Write report output to specified file path | `stdout` |
| `--export-ttl` | Export updated QUDT Turtle file with documented changes (`qudt_constants_constant.<year>.ttl`) | `False` |
| `--update-qudt` | Alias for `--export-ttl`: produce updated QUDT Turtle file with documented changes | `False` |
| `--export-md` | Custom path for companion Markdown change documentation file | matches `.ttl` path with `.md` |

### Examples

```bash
# Display outdated constants in terminal table
uv run codata-compare-qudt --outdated-only

# Produce updated QUDT Turtle file and documented list of changes
uv run codata-compare-qudt --update-qudt

# Export updated Turtle file to custom location
uv run codata-compare-qudt --export-ttl custom_constants.ttl --export-md custom_changes.md

# Generate Markdown comparison report artifact
uv run codata-compare-qudt --format markdown --output qudt_report.md

# Generate HTML report
uv run codata-compare-qudt --format html --output qudt_report.html

# Force re-fetching Turtle file from qudt.org
uv run codata-compare-qudt --refresh
```
