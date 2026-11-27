# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Fixed
- Restored scientific symbol casing (`u`, `g`, `kPa`, `c`, `hc`, `h-bar`, `pi`, `d`, `p`, `t`, `x`, `HD`, `HT`, `s`, `Si`/`SI`) across 41 English constant names, `default_constant_name_en()` in `utils/models.py`, the browser editor in `utils/editor/index.html`, and `_BAD_SI_TOKENS` (`"KPa"`) in `utils/validate.py` (PR #11, #10).
- Preserved trailing significant zeros in 34-digit truncated `computed_exact` values via `format_canonical_decimal(..., keep_trailing_zeros=True)`, updating 16 values across 2018 and 2022 (PR #13, #12).
- Preserved curated `adjustment_role` values in `sync-nist`, added pre-save validation on `--apply`, and added `--allow-missing-roles` scoped to `MISSING_ADJUSTMENT_ROLE` on the synced release (PR #15, #14).
- Corrected French labels (`name_fr` and `name_bipm_fr`) of `ShieldingDifferenceOfTAndP` from `dans HD` to `dans HT` (#16).

## [0.4.0] - 2026-11-21

### Added
- **Formula Engine & Safe AST Evaluator (`utils/formulas.py`)**: Added AST-validated formula grammar supporting `**`, `+`, `-`, `*`, `/`, `sqrt()`, `ln()`, `abs()`, and high-precision math constants (`pi`, `wien_x_wavelength`, `wien_x_frequency`), topological `Fraction` DAG evaluation (`evaluate_exact_dag`) recovering full terminating rational expansions, 34-digit IEEE 754 `decimal128` (`ROUND_DOWN`) fallback truncation, and IEEE 754 `binary32`/`binary64` lossless sufficiency checks.
- **Determination Role Taxonomy & Algebraic Metadata (`ConstantValueModel`, `data/constants.yaml`)**: Scoped `adjustment_role` and `is_computed` per release on `ConstantValueModel` (`codata:adjustmentRole` and `codata:isComputed` in RDF), eliminating historical SI anachronisms across the 2019 SI redefinition (e.g. $h, e, k, N_{\text{A}}$ accurately classified as `adjusted` in 1998–2014 and `defining` in 2018–2022; $\mu_0$ as `defining` in 1998–2014 and `computed_derived` in 2018–2022; $F, R$ as `computed_derived` in 1998–2014 and `computed_exact` in 2018–2022). Physical relationships (`symbol_tex`, `formula`, `formula_tex`, `derived_from`) remain invariant on `ConstantModel` (`codata:Constant`).
- **Two-Source Precision Model (`ConstantValueModel`)**: Added `value_nist` (`codata:nistValue`), `value_source` (`"nist"` | `"computed"`), and `is_nist_truncated` (`codata:isNistTruncated`). Upgraded 124 truncated `computed_exact` entries across `2018` and `2022` (`62` per release), recovering complete exact expansions for `20` terminating rationals (`10` per release, including `FaradayConstant`, `MolarGasConstant`, `MolarPlanckConstant`, `ConventionalValueOfAmpere90`, `ConventionalValueOfCoulomb90`, and `ConventionalValueOfWatt90`) and 34 significant digits for the remaining `104` irrational/repeating constants (`52` per release).
- **IEEE 754 Numeric Type & Digit Sufficiency Metadata**: Added computed fields `significant_digits`, `fits_float32`, `fits_float64`, and `recommended_numeric_type` (`"float32"`, `"float64"`, or `"decimal"`) to `ConstantValueModel`, CSV exports, legacy JSON, RDF (`codata:significantDigits`, `codata:fitsFloat32`, `codata:fitsFloat64`, `codata:recommendedNumericType`), and HTML editor.
- **Formula DAG & Role Validation (`utils/validate.py`)**: Extended L1/L2/L4 checks with formula syntax validation, role-exactness consistency, formula DAG cycle detection, `value_nist`/`is_nist_truncated`/`nist_exponent` NIST parity checks, and end-to-end verification of all 380 exact and derived formula evaluations (`2018` exact + `2022` exact/derived).
- **Historical Narrative & Citations (`docs/COMPUTABLE_CONSTANTS.md`)**: Documented the pre-2019 (`1998`–`2014`) to revised SI (`2018`–`2022`) transition (70 constants gaining/entering as exact vs. 6 losing exactness, 1990 electrical metrology, two-source precision, and IEEE 754 limits) with full citations (Mohr et al. 2025, Tiesinga et al. 2021, NIST SP 961/SP 959/SRD 121, BIPM 9th SI Brochure, Mohr et al. 2018, Newell et al. 2018).

### Changed
- **Field Rename (`exponent` -> `nist_exponent`)**: Aligned `ConstantValueModel`, YAML, CSV snapshots, HTML editor, `sync-nist`, `migrate.py`, and RDF generator with `codata:nistExponent` (no backward-compatibility alias in `0.4.0` experimental schema).
- **High-Precision RDF Decimal Verification (`utils/package.py`)**: Wrapped `validate_graph_precision` decimal comparisons in `localcontext(prec=100)` so 34-digit `xsd:decimal` literals verify without Python's default 28-digit `Decimal.normalize()` truncation, and emitted `codata:derivedFrom` and all new ontology properties to Turtle and JSON-LD.
- **Ontology, Report, Editor & Docs (`v0.4.0`)**: Bumped schema, `docs/codata.ttl` (`owl:versionInfo`), FastAPI editor, and UI to `0.4.0`; expanded `docs/DATASET_REPORT.md` and `docs/CODATA_CONSTANTS_MODEL.md`.

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
