# CODATA DRUM: Fundamental Physical Constants

[![License: CC BY 4.0](https://img.shields.io/badge/License-CC%20BY%204.0-lightgrey.svg)](http://creativecommons.org/licenses/by/4.0/)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

A comprehensive digitization and knowledge-engineering project that transforms CODATA fundamental physical constants into machine-actionable semantic formats (JSON, RDF/Turtle, JSON-LD), enabling seamless integration with modern data science workflows, AI systems, and metrological applications.

## 🎯 Project Objectives

**Digital Transformation**: Convert fundamental physical constants from human-readable documents into robust, machine-readable formats (JSON, RDF/Turtle, JSON-LD) aligned with [FAIR data principles](https://www.go-fair.org/fair-principles/).

**API-First Approach**: Provide industry-standard REST and SPARQL APIs (via the companion [`drum-api`](https://github.com/codata/drum-api) service) for programmatic access to constant definitions, values, and metadata across all CODATA releases (1998–2022).

**AI & Data Science Ready**: Enable seamless integration with large language models (LLMs), AI agents, and data science pipelines through structured semantic data and comprehensive query capabilities.

**Robust Semantic Infrastructure**: Establish a formal OWL/RDFS ontology ([`docs/codata.ttl`](docs/codata.ttl)), associated domain taxonomy, and SPARQL query support for reasoning over fundamental constants data.

**Interoperability**: Harmonize with existing standards (QUDT, UCUM, SI Digital Framework, Wikidata) and provide bidirectional cross-references to enhance discoverability and integration.

## 🏗️ Architecture & Data Pipeline

### Curation & ETL Workflow

The dataset is produced through a two-stage pipeline combining official NIST ASCII tables with editorial semantic curation:

1. **NIST ASCII Extraction (`nist/repackage.py`)**: Raw NIST ASCII release tables (`nist/<year>/allascii_<year>.txt` and `corrcoef<year>.txt` from 1998 to 2022) are parsed and cleaned into normalized CSV and JSON files (`nist/<year>/allascii_<year>.csv` and `.json`).
2. **Curated Master Workbook & Git-Tracked CSV Snapshots (`utils/codata_constants.py`)**: The cleaned NIST values are loaded into a curated Google Sheet (`utils/codata_constants.xlsx`), where editorial curation adds the SKOS concept hierarchy, quantity groupings, multilingual labels (`@en` and `@fr`), and external vocabulary mappings (QUDT, UCUM, SI Digital Framework, Wikidata). Whenever `codata-constants` runs, it exports **Git-tracked CSV snapshots of every worksheet** into `utils/csv/*.csv` (for human-readable pull request diffs) and compiles `utils/codata_constants.json`. *(Note: A future release will transition editorial maintenance directly to the GitHub-hosted CSV/JSON tables.)*
3. **High-Precision RDF Packaging (`utils/package.py`)**: Reads `utils/codata_constants.json`, constructs the RDF graph with three numeric representations (`codata:value` string, `codata:valueFloat` double, and `codata:valueDecimal` arbitrary-precision decimal), validates round-trip numerical and lexical precision, and outputs `dist/rdf/codata_constants.ttl`, `dist/rdf/codata_constants.jsonld`, and `dist/rdf/codata.ttl`.

### Semantic Model

The project implements a comprehensive semantic model with 6 core entities:

1. **Concepts** (`codata:Concept`) - Taxonomic organization (SI Units, Elementary Particles, Ratios, etc.)
2. **Quantities** (`codata:Quantity`) - Physical measurable properties (also typed as `codata:Concept`)
3. **Constants** (`codata:Constant`) - Specific physical constants with historical values and deprecation flags (`owl:deprecated`)
4. **Units** (`codata:Unit`) - Physical measurement units with `skos:prefLabel`, `ucum:ucum`, and `ucum:si_expression`
5. **Versions** (`codata:Version`) - CODATA release metadata (`1998`, `2002`, `2006`, `2010`, `2014`, `2018`, `2022`)
6. **ConstantValues** (`codata:ConstantValue`) - Versioned values, uncertainties, exactness (`codata:isExact`), and NIST table display exponents (`codata:nistExponent`)

## 🚀 Quick Start

### Data Access

```bash
# Download RDF Turtle dataset
wget https://github.com/codata/drum-constants/raw/main/dist/rdf/codata_constants.ttl

# Download OWL/RDFS Ontology
wget https://github.com/codata/drum-constants/raw/main/dist/rdf/codata.ttl

# Download JSON dataset  
wget https://github.com/codata/drum-constants/raw/main/utils/codata_constants.json
```

### Local Development

```bash
# Clone repository
git clone https://github.com/codata/drum-constants.git
cd drum-constants

# Install dependencies using uv
uv pip install -e ".[dev]"

# Run code quality checks (linting, static type checking, and test suite)
uv run ruff check .
uv run pyrefly check .
uv run pytest

# Refresh JSON & CSV snapshots from workbook and generate RDF products
uv run codata-constants --norefresh
uv run codata-package

# Compare QUDT constants with official CODATA values
uv run codata-compare-qudt --outdated-only
```

### SPARQL Queries

The RDF dataset supports rich semantic queries:

```sparql
# Find all SI defining constants
PREFIX codata: <https://w3id.org/codata/model/>
PREFIX concept: <https://w3id.org/codata/concepts/>
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
PREFIX dcterms: <http://purl.org/dc/terms/>

SELECT ?constant ?label WHERE {
    ?constant a codata:Constant ;
              skos:prefLabel ?label ;
              codata:hasQuantity ?quantity .
    ?quantity dcterms:hasPart ?concept .
    ?concept skos:broader* concept:SIDefiningConstant .
    FILTER(lang(?label) = "en")
}
```

## 📊 Dataset Coverage

- **7 CODATA Releases**: Complete historical coverage (1998–2022)
- **359 Constants**: All fundamental physical constants from NIST (355 active in CODATA 2022 + 4 historical constants marked `owl:deprecated true`)
- **Multi-format**: CSV snapshots, JSON, RDF/Turtle, and JSON-LD datasets
- **Multilingual**: English (`@en`) and French (`@fr`) preferred and alternative labels
- **Cross-referenced**: NIST, QUDT (325 mapped constants), UCUM, SI Digital Framework, and Wikidata identifiers
- **Version Tracking**: Evolution of values and uncertainties over time

## 🛠️ CLI Utilities & Tools

The repository includes CLI utilities exposed via `pyproject.toml`:

- **`codata-compare-qudt`** ([`utils/compare_qudt.py`](utils/compare_qudt.py)): Compares QUDT constants Turtle vocabulary (`https://qudt.org/3.5.0/vocab/constant`) against official CODATA values in `codata_constants.json`. Identifies whether QUDT constant values are up-to-date or match older historical CODATA releases, and produces synchronized, updated QUDT Turtle vocabulary files (`qudt_constants_constant.2022.ttl`) with complete changelogs.
- **`codata-package`** ([`utils/package.py`](utils/package.py)): High-precision RDF generator that serializes the dataset to Turtle (`.ttl`) and JSON-LD (`.jsonld`) with round-trip precision validation.
- **`codata-constants`** ([`utils/codata_constants.py`](utils/codata_constants.py)): Exports the Excel/Google Spreadsheet worksheets into tracked CSV snapshots (`utils/csv/*.csv`) and compiles `utils/codata_constants.json`.
- **`nist-repackage`** ([`nist/repackage.py`](nist/repackage.py)): Parses raw NIST ASCII releases across years (1998–2022).

## 📁 Repository Structure

```
drum-constants/
├── pyproject.toml           # Python package & CLI entrypoints configuration
├── LICENSING.md             # Dual licensing explanation (CC BY 4.0 data / Apache 2.0 code)
├── utils/                   # Data processing and verification utilities
│   ├── csv/                 # Version-controlled CSV snapshots of each workbook sheet
│   ├── compare_qudt.py      # QUDT vs CODATA side-by-side comparison utility
│   ├── compare_qudt.md      # Documentation for QUDT comparison tool
│   ├── package.py           # High-precision RDF generator
│   ├── package.md           # Documentation for RDF packaging
│   ├── codata_constants.py  # Workbook to CSV & JSON converter
│   └── codata_constants.json# Processed dataset master
├── dist/rdf/                # Generated RDF/Turtle, JSON-LD, and codata.ttl files
├── nist/                    # Raw NIST ASCII source data and parsers
├── docs/                    # Semantic data model specifications and OWL ontology
│   ├── CODATA_CONSTANTS_MODEL.md
│   └── codata.ttl
└── tests/                   # Automated SPARQL documentation and data integrity tests
```

## 🗺️ Roadmap & Known Limitations

### Current Release
- ✅ Complete NIST dataset digitization (1998–2022) with versioned CSV snapshots
- ✅ Formal `codata.ttl` OWL/RDFS ontology and validated SPARQL documentation
- ✅ Three-part high-precision numeric representation (`value`, `valueFloat`, `valueDecimal`)
- ✅ Enriched `codata:Unit` nodes with UCUM codes and SI expressions
- ✅ Explicit `owl:deprecated` tagging for retired pre-2019 SI constants

### Planned for Future Releases (Post-GitHub Curation Migration)
- 📅 **GitHub-Native Curation**: Transition editorial maintenance from the Google Sheet directly to GitHub-managed CSV/JSON tables.
- 📅 **CODATA Covariance & Correlation Matrix (`codata:Correlation`)**: Expose the pairwise correlation coefficients (`corrcoef`) for jointly-adjusted CODATA constants so downstream consumers can propagate uncertainties across derived quantities with full covariance.
- 📅 **Constant Adjustment Roles (`codata:adjustmentRole`)**: Explicitly classify constants into `defining` (exact SI defining constants), `adjusted` (primary least-squares fitted constants), and `derived` (computed from defining/adjusted constants).
- 📅 **Computed Relative Uncertainty (`codata:relativeUncertainty`)**: Precomputed relative standard uncertainty $u_r(x) = u(x)/|x|$.

## 📖 Documentation

- **[Semantic Model Guide](docs/CODATA_CONSTANTS_MODEL.md)**: Complete RDF ontology documentation and validated SPARQL examples
- **[OWL Ontology (`docs/codata.ttl`)](docs/codata.ttl)**: Formal class and property definitions
- **[RDF Packaging Guide](utils/package.md)**: High-precision serialization and validation details
- **[QUDT Comparison Guide](utils/compare_qudt.md)**: Synchronization with QUDT constant vocabularies

## 📜 Licensing

- **Data & Ontology**: [Creative Commons Attribution 4.0 International License (CC BY 4.0)](http://creativecommons.org/licenses/by/4.0/)
- **Software**: [Apache License 2.0](https://www.apache.org/licenses/LICENSE-2.0.txt)

See [`LICENSING.md`](LICENSING.md) for details on how data and software licenses apply across the CODATA DRUM repositories.

## 🏛️ About CODATA DRUM & TGFC

This project operates under the umbrella of the [CODATA Digital Representation of Units of Measure (DRUM)](https://codata.org/initiatives/task-groups/drum/) working group, advancing FAIR metrology across scientific disciplines. It also supports the mission and vision of the [CODATA Task Group on Fundamental Physical Constants (TGFC)](https://codata.org/initiatives/data-science-and-stewardship/fundamental-physical-constants/), which maintains and disseminates internationally recommended values of fundamental physical constants.

**Maintainer**: Pascal Heus (CODATA DRUM Task Group)  
**Support**: Use [GitHub Issues](https://github.com/codata/drum-constants/issues) for questions and assistance

## 📚 References

- [NIST Fundamental Physical Constants](https://physics.nist.gov/cuu/Constants/)
- [CODATA 2022 Recommended Values (Mohr et al. 2025, Rev. Mod. Phys. 97, 025002)](https://doi.org/10.1103/RevModPhys.97.025002)
- [CODATA 2018 Recommended Values (Tiesinga et al. 2021, Rev. Mod. Phys. 93, 025010)](https://doi.org/10.1103/RevModPhys.93.025010)
- [BIPM: The International System of Units (SI)](https://www.bipm.org/en/publications/si-brochure)
- [QUDT: Quantities, Units, Dimensions and Types](https://qudt.org)
- [UCUM: Unified Code for Units of Measure](https://ucum.org)
