# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.3.0] - 2026-11-20

### Added
- **GitHub-Native YAML Curation (`data/*.yaml`)**: Migrated all 7 CODATA versions, 84 units, 442 concepts, 306 quantities, 359 constants, and 2,313 versioned values into modular, deterministically sorted YAML files (`versions.yaml`, `units.yaml`, `concepts.yaml`, `quantities.yaml`, `constants.yaml`).
- **Pydantic v2 Domain Models & YAML I/O (`utils/models.py`, `utils/dataset.py`)**: Strict schema and decimal-string precision validation, computed properties replacing spreadsheet lookup/count formulas, and `CodataYamlDumper` quoting rules preserving trailing zeros and string identifiers.
- **Four-Layer Validation Engine (`codata-validate` / `utils/validate.py`)**: Validates exact decimal precision (L1), ID uniqueness, foreign keys, and concept DAG cycles (L2), SI symbol casing and unit/label hygiene (L3), and 2,313-value NIST JSON cross-checks + 2022 metrological identities (L4).
- **Automated Markdown Reporting (`codata-report` / `utils/report.py`)**: Generates `docs/DATASET_REPORT.md` with release coverage matrices, external alignment progress (`NIST`, `QUDT`, `SI`, `UCUM`, `Wikidata`), deprecated constants, metrological identity checks, and validation audits.
- **Hybrid HTML YAML Editor (`codata-editor` / `utils/editor.py` + `utils/editor/index.html`)**: Single-page editor supporting both Connected Server Mode (FastAPI direct YAML read/save/validate/package) and Standalone Browser Mode (File System Access API + YAML import/download).
- **YAML Pipeline Test Suite (`tests/test_yaml_pipeline.py`)**: Covers dataset counts, 4-layer validation, YAML round-trip precision, computed helpers, negative validation checks, Markdown reporting, and FastAPI editor endpoints.
- **Transition Documentation (`docs/YAML_MIGRATION_REPORT.md`)**: Detailed report documenting schema design, formula mapping, retired artifacts, and spreadsheet defects resolved during migration.

### Changed
- **Direct YAML-to-RDF Packaging (`utils/package.py`, `utils/codata_constants.py`)**: Refactored `codata-package` to read directly from `data/*.yaml` and upgraded `codata-constants` into a Typer CLI (`build`, `validate`, `report`, `sync-nist`).
- **Consolidated NIST Repackaging (`nist/repackage.py`)**: Folded `Ruj`, `Rukg`, and `eshbar` identifier disambiguations and abbreviation expansions into `nist-repackage`, eliminating dependence on the spreadsheet `nist_names_ids` tab.
- **Documentation & Ontology Version**: Bumped project, schema, editor API, and `docs/codata.ttl` `owl:versionInfo` to `0.3.0`.

### Fixed
- **Pre-2010 NIST Uncertainties & Exactness (`1998`, `2002`, `2006`)**: Corrected the Google Sheet regex `10^k` uncertainty shrinkage across 886 values and restored `is_exact: true` on 48 pre-2010 exact constant values from authoritative `nist/<year>/allascii_<year>.json`.
- **CODATA `2022` Truncation Flags**: Restored `is_truncated: true` on 62 truncated irrational exact constants from `nist/2022/allascii_2022.json`.
- **Taxonomy Cycles & Unit References**: Removed self-loops on `Concept:SIConstant`, `Concept:WeakMixingAngle`, and `Concept:Relationship`, cleared errant `Acceleration.is_ratio`, added `unit:Hz_V-1` for `JosephsonConstant`, and aligned `FaradayConstantConventionalElectricCurrent` (`CXC_mol-1`) and `ConventionalValueOfCoulomb90` (`CXC`).

### Removed
- Retired the Google Sheet downloader, `utils/codata_constants.xlsx`, `utils/csv/nist_names_ids.csv`, and the `openpyxl` dependency.

## [0.2.0] - 2026-10-20

### Added
- **Formal OWL/RDFS Ontology**: Published standalone ontology definition at `docs/codata.ttl` and `dist/rdf/codata.ttl` specifying classes, object properties, datatype properties, and domain/range axioms.
- **Automated CSV Snapshots**: Pipeline now exports git-tracked CSV snapshots of all 13 Google Sheet worksheets to `utils/csv/` on every execution of `utils/codata_constants.py`.
- **Unit Enrichment**: Enriched `codata:Unit` instances with `skos:prefLabel` English names, `ucum:ucum` codes, and `ucum:si_expression` strings.
- **Deprecation Modeling**: Constants discontinued in the 2022 adjustment (`FaradayConstantConventionalElectricCurrent`, `MolarPlanckConstantTimesC`, `TritonElectronMagneticMomentRatio`, `TritonNeutronMagneticMomentRatio`) are explicitly flagged with `owl:deprecated true`.
- **Backward Compatibility Aliases**: Emitted `owl:sameAs` triples for renamed concept and constant IRIs (`concept:EletronVolt` -> `quantity:ElectronVolt` and 6 legacy Pascal/Electronvolt IDs).
- **Automated Validation Suite**: Added comprehensive pytest suite (`tests/test_rdf_and_docs.py`) validating ontology syntax, markdown SPARQL documentation queries, SI symbol casing, deprecation status, and 2022 metrological identities.
- **Dual Licensing Policy**: Added `LICENSING.md` documenting CC BY 4.0 for data/ontology distributions and Apache 2.0 for code and tooling.

### Changed
- **NIST Exponent Predicate**: Renamed `codata:exponent` to `codata:nistExponent` (`MODEL.nistExponent`) to clarify that it represents NIST's publication display scale factor rather than a normalized mantissa exponent.
- **Language Tagging**: Added `@en` and `@fr` BCP 47 language tags across all `skos:prefLabel` and `skos:altLabel` triples.
- **Truncation Semantics**: Ceased emitting `codata:isTruncated false` on 2022 constant values; truncation is now omitted or only asserted when `true` post-2019 SI redefinition.
- **Precision Validation**: Strengthened `validate_graph_precision` in `utils/package.py` to compare normalized significand digit tuples (`Decimal.normalize().as_tuple().digits`).
- **QUDT Comparison**: Updated QUDT comparison reports and alignments for the 2022 release.
- **Documentation**: Corrected namespace prefixes to `https://w3id.org/codata/` across `README.md` and `docs/CODATA_CONSTANTS_MODEL.md`, and documented correlation matrix roadmap.

### Fixed
- Fixed typo in `concept:EletronVolt` to `quantity:ElectronVolt`.
- Fixed Momentum constant naming and labels (`Moment` -> `Momentum`).
- Fixed SI unit symbol casing across labels (`Kpa` -> `kPa`, `Mev` -> `MeV`, `Ev` -> `eV`, `Mhz` -> `MHz`, `Fm` -> `fm`).
- Fixed formula row lookup in spreadsheet row 252 (`mnmmpu` / `NeutronProtonMassDifferenceInU`).

## [0.1.0] - 2025-11-20

### Added
- Initial release of the CODATA fundamental constants ETL pipeline.
- High-precision Turtle and JSON-LD RDF serializers.
- Three numeric representations per constant value (`value` string, `valueFloat` IEEE double, `valueDecimal` fixed-point decimal).
- Multi-version historical support covering CODATA adjustments from 1998 through 2022.
- QUDT alignment comparison tool.
