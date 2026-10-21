# Licensing Policy

This repository contains two distinct categories of intellectual work, each governed by the license best suited to its nature:

## 1. Knowledge Graph, Ontology, and Data Assets — CC BY 4.0

All ontology definitions, controlled vocabularies, RDF graphs, CSV snapshots, and documentation are licensed under the **[Creative Commons Attribution 4.0 International License (CC BY 4.0)](https://creativecommons.org/licenses/by/4.0/)**:

- `dist/rdf/codata_constants.ttl` and `dist/rdf/codata_constants.jsonld`
- `dist/rdf/codata.ttl` and `docs/codata.ttl`
- `utils/csv/*.csv` and `utils/codata_constants.json`
- `docs/*.md`

This aligns with the `dcterms:license <https://creativecommons.org/licenses/by/4.0/>` declaration embedded in the RDF knowledge graph and ontology header.

## 2. Software and Build Scripts — Apache License 2.0

All Python source code, build pipelines, validation scripts, and automated tests in `utils/` and `tests/` are licensed under the **[Apache License, Version 2.0](https://www.apache.org/licenses/LICENSE-2.0)**.
