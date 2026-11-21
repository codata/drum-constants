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

The dataset is produced through a GitHub-native YAML curation pipeline combining official NIST ASCII tables with editorial semantic enrichment:

1. **NIST ASCII Extraction (`nist/repackage.py`)**: Raw NIST ASCII release tables (`nist/<year>/allascii_<year>.txt` and `corrcoef<year>.txt` from 1998 to 2022) are parsed and cleaned into normalized CSV and JSON files (`nist/<year>/allascii_<year>.csv` and `.json`), including canonical NIST identifier resolution (`nist/nist_ids.json`).
2. **Modular YAML Curation (`data/*.yaml`)**: Editorial curation (SKOS concept hierarchy, quantity groupings, multilingual `@en`/`@fr` labels, and external vocabulary mappings to QUDT, UCUM, SI Digital Framework, and Wikidata) is maintained directly in five deterministic, Git-tracked YAML files under `data/` (`versions.yaml`, `units.yaml`, `concepts.yaml`, `quantities.yaml`, `constants.yaml`). An interactive hybrid HTML editor (`codata-editor`, also usable standalone in a browser) simplifies editing and validation.
3. **Validation, Reporting & Packaging (`utils/validate.py`, `utils/report.py`, `utils/package.py`)**: Running `codata-constants build` executes 4-layer validation (Pydantic schema/exactness/formula syntax, referential integrity & concept/formula DAG cycle checks, SI hygiene, and NIST JSON cross-checks + full 380-formula algebraic DAG verification across `computed_exact` and `computed_derived` constants), exports legacy JSON (`utils/codata_constants.json`) and CSV snapshots (`dist/csv/*.csv` / `utils/csv/*.csv`), compiles `docs/DATASET_REPORT.md`, and generates high-precision RDF outputs (`dist/rdf/codata_constants.ttl`, `dist/rdf/codata_constants.jsonld`, and `dist/rdf/codata.ttl`).

### Semantic Model

The project implements a comprehensive semantic model with 6 core entities:

1. **Concepts** (`codata:Concept`) - Taxonomic organization (SI Units, Elementary Particles, Ratios, etc.)
2. **Quantities** (`codata:Quantity`) - Physical measurable properties (also typed as `codata:Concept`)
3. **Constants** (`codata:Constant`) - Specific physical constants with determination role (`codata:adjustmentRole`), LaTeX symbol (`codata:hasSymbol`), algebraic formula (`codata:formula`, `codata:formulaLatex`, `codata:derivedFrom`), historical values, and deprecation flags (`owl:deprecated`)
4. **Units** (`codata:Unit`) - Physical measurement units with `skos:prefLabel`, `ucum:ucum`, and `ucum:si_expression`
5. **Versions** (`codata:Version`) - CODATA release metadata (`1998`, `2002`, `2006`, `2010`, `2014`, `2018`, `2022`)
6. **ConstantValues** (`codata:ConstantValue`) - Versioned two-source values (`codata:value` upgraded when NIST truncates post-2019 exact constants + verbatim `codata:nistValue`), provenance (`codata:valueSource`), NIST truncation tracking (`codata:isNistTruncated`), IEEE 754 precision metadata (`codata:significantDigits`, `codata:fitsFloat32`, `codata:fitsFloat64`, `codata:recommendedNumericType`), uncertainties, and `codata:nistExponent`

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
uv sync --extra dev

# Run code quality checks (linting, static type checking, and test suite)
uv run ruff check .
uv run pyrefly check .
uv run pytest

# Validate YAML files, generate Markdown report, and build JSON/CSV/RDF products
uv run codata-validate
uv run codata-constants build

# Launch the interactive HTML YAML editor (http://127.0.0.1:8080)
uv run codata-editor

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

- **`codata-constants`** ([`utils/codata_constants.py`](utils/codata_constants.py)): Main pipeline CLI with subcommands `build` (validates `data/*.yaml` and generates JSON, CSV snapshots, RDF products, and `docs/DATASET_REPORT.md`), `validate`, `report`, and `sync-nist --year <YYYY> [--apply]`.
- **`codata-validate`** ([`utils/validate.py`](utils/validate.py)): 4-layer dataset validator verifying Pydantic schema & exact decimal strings, referential integrity & DAG cycles, SI symbol casing & multilingual hygiene, and NIST JSON + metrological identity checks.
- **`codata-report`** ([`utils/report.py`](utils/report.py)): Generates the Markdown dataset & validation audit report at [`docs/DATASET_REPORT.md`](docs/DATASET_REPORT.md).
- **`codata-editor`** ([`utils/editor.py`](utils/editor.py)): Launches the local FastAPI backend and single-page HTML YAML editor ([`utils/editor/index.html`](utils/editor/index.html)), which also works standalone in a browser via the File System Access API or YAML upload/download.
- **`codata-package`** ([`utils/package.py`](utils/package.py)): High-precision RDF generator reading directly from `data/*.yaml` and serializing to Turtle (`.ttl`) and JSON-LD (`.jsonld`) with round-trip precision validation.
- **`codata-compare-qudt`** ([`utils/compare_qudt.py`](utils/compare_qudt.py)): Compares QUDT constants Turtle vocabulary (`https://qudt.org/3.5.0/vocab/constant`) against official CODATA values in `codata_constants.json`.
- **`nist-repackage`** ([`nist/repackage.py`](nist/repackage.py)): Parses raw NIST ASCII releases across years (1998–2022) and resolves canonical NIST IDs.

## 📁 Repository Structure

```
drum-constants/
├── pyproject.toml           # Python package & CLI entrypoints configuration
├── LICENSING.md             # Dual licensing explanation (CC BY 4.0 data / Apache 2.0 code)
├── data/                    # Authoritative Git-tracked YAML dataset
│   ├── versions.yaml        # CODATA release versions (1998–2022)
│   ├── units.yaml           # Physical units with SI & UCUM mappings
│   ├── concepts.yaml        # SKOS concept taxonomy & Wikidata links
│   ├── quantities.yaml      # Physical quantity groupings
│   └── constants.yaml       # Constants metadata & versioned NIST values
├── utils/                   # Data processing, validation, reporting & editor tools
│   ├── models.py            # Pydantic v2 models & computed-field helpers
│   ├── dataset.py           # Deterministic YAML load/save & JSON/CSV exporters
│   ├── validate.py          # 4-layer dataset & NIST cross-check validator
│   ├── report.py            # Markdown dataset & validation report generator
│   ├── editor.py            # FastAPI backend for the hybrid HTML editor
│   ├── editor/index.html    # Single-page hybrid HTML/JS YAML editor
│   ├── csv/                 # Generated CSV snapshots exported from data/*.yaml
│   ├── compare_qudt.py      # QUDT vs CODATA side-by-side comparison utility
│   ├── package.py           # High-precision RDF generator (YAML -> TTL/JSON-LD)
│   ├── codata_constants.py  # Orchestration CLI (build, validate, report, sync-nist)
│   └── codata_constants.json# Exported JSON dataset master
├── dist/rdf/                # Generated RDF/Turtle, JSON-LD, and codata.ttl files
├── nist/                    # Raw NIST ASCII source data and parsers
├── docs/                    # Semantic model specs, OWL ontology & dataset report
│   ├── CODATA_CONSTANTS_MODEL.md
│   ├── DATASET_REPORT.md
│   └── codata.ttl
└── tests/                   # Automated SPARQL, YAML pipeline & editor tests
```

## 🗺️ Roadmap & Known Limitations

### Current Release (`v0.4.0`)
- ✅ Complete NIST dataset digitization (1998–2022) in Git-native modular YAML (`data/*.yaml`)
- ✅ **Determination Role Taxonomy & Algebraic Formulas**: All 355 active constants categorized (`defining`, `computed_exact`, `adjusted`, `computed_derived`) with safe Python/SymPy formulas, LaTeX symbols/formulas, and acyclic `derived_from` DAGs validated end-to-end
- ✅ **Two-Source Precision Model**: Preserves verbatim NIST strings in `value_nist` (`codata:nistValue`) / `is_nist_truncated` while elevating truncated post-2019 exact constants (`124` entries across `2018+2022`) to complete terminating rationals (`20` entries recovered) or 34-digit IEEE 754 `decimal128` expansions
- ✅ **IEEE 754 Storage Sufficiency**: Dynamically computes `significant_digits`, `fits_float32`, `fits_float64`, and `recommended_numeric_type` (`float32` / `float64` / `decimal`)
- ✅ 4-layer automated validation, Markdown reporting (`docs/DATASET_REPORT.md`), and hybrid HTML editor (`codata-editor`)
- ✅ Formal `codata.ttl` OWL/RDFS ontology and validated SPARQL documentation
- ✅ Three-part high-precision numeric representation (`value`, `valueFloat`, `valueDecimal`)
- ✅ Enriched `codata:Unit` nodes with UCUM codes and SI expressions
- ✅ Explicit `owl:deprecated` tagging for retired pre-2019 SI constants

### Planned for Future Releases
- 📅 **CODATA Covariance & Correlation Matrix (`codata:Correlation`)**: Expose the pairwise correlation coefficients (`corrcoef`) for jointly-adjusted CODATA constants so downstream consumers can propagate uncertainties across derived quantities with full covariance.
- 📅 **Computed Relative Uncertainty (`codata:relativeUncertainty`)**: Precomputed relative standard uncertainty $u_r(x) = u(x)/|x|$.

## 📖 Documentation

- **[Computable Constants, Roles & Precision Guide](docs/COMPUTABLE_CONSTANTS.md)**: Historical 2019 SI transition story, 4-role taxonomy, safe formula grammar, two-source precision model, IEEE 754 limits, and citations
- **[YAML Migration Report](docs/YAML_MIGRATION_REPORT.md)**: Detailed report on transitioning from Google Sheets to GitHub-native YAML (`v0.3.0`)
- **[Dataset & Validation Report](docs/DATASET_REPORT.md)**: Automated release coverage, external alignment & quality audit
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
