# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
