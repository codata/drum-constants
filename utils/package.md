# CODATA Constants Packaging Utility (`package.py`)

The `package.py` utility is a specialized tool designed to convert parsed CODATA constants data into high-quality semantic RDF representations (Turtle and JSON-LD). It focuses on maintaining absolute numerical precision for physical constants through a multi-layered validation and serialization strategy.

## Purpose

The primary goal of this utility is to transform the intermediate `codata_constants.json` file into FAIR (Findable, Accessible, Interoperable, and Reusable) data products that can be used in scientific applications, knowledge graphs, and semantic reasoning systems without losing the precision inherent in the source NIST data.

## Key Features

### 1. Three-Part High-Precision Numeric Handling
The utility implements a three-part strategy for representing physical constants and their uncertainties:
- **Canonical String (`codata:value` / `codata:uncertainty`, `xsd:string`)**: Mirrors the exact string representation published by NIST, preserving significant trailing zeros.
- **Double-Precision Float (`codata:valueFloat` / `codata:uncertaintyFloat`, `xsd:double`)**: Provides standard scientific-notation floating-point literals (e.g., `6.62607015e-34`) with full double precision.
- **Arbitrary-Precision Decimal (`codata:valueDecimal` / `codata:uncertaintyDecimal`, `xsd:decimal`)**: Generates `xsd:decimal` literals using Python's `Decimal` class to guarantee zero binary floating-point rounding loss and verify precision against the floating-point representation. Note that because the W3C XML Schema (`xsd:decimal`) and W3C RDF 1.1 Turtle grammar (`DECIMAL ::= [+-]? [0-9]* '.' [0-9]+`) prohibit exponent notation (`e-34`), `valueDecimal` is serialized in fixed-point form in Turtle while `valueFloat` carries the scientific notation.

### 2. Custom High-Precision Serializer
Standard RDF serializers often round floating-point numbers to shorter scientific notation (e.g., rounding `7294.29954171` to `7.2943e+03`). `package.py` includes a `HighPrecisionTurtleSerializer` that:
- Bypasses automatic numeric shortening in Turtle output.
- Forces explicit full-precision lexical forms for all `xsd:double` and `xsd:decimal` literals.
- Ensures that the resulting Turtle file matches the original data bit-for-bit in precision.

### 3. JSON-LD Optimization
To ensure precision in JSON-LD (and other JSON-based formats), the utility:
- Monkey-patches the `json` encoder to ensure that floating-point values are serialized with at least 8 digits after the decimal point.
- Prevents the standard JSON "e-notation" simplification from degrading the accuracy of the physical constants.

### 4. Automated Validation Suite
The utility includes a built-in validation engine (`validate_graph_precision`) that performs three checks per execution:
- **In-Memory Validation**: Verifies generated literals against master strings immediately after graph construction.
- **Turtle Round-Trip**: Re-parses the saved `.ttl` file and verifies every numeric value and its normalized significant digits (`Decimal.as_tuple().digits`) against the source data.
- **JSON-LD Round-Trip**: Re-parses the saved `.jsonld` file to ensure the serialization process was loss-less.
- **Precision Threshold**: Discrepancies greater than $2 \times 10^{-16}$ (machine epsilon for doubles) or any mismatch in decimal significant digits trigger a failure, preventing the creation of imprecise data products.

### 5. Semantic Enrichment & Deprecation Tracking
The utility maps CODATA entities to multiple authoritative vocabularies and tracks historical continuity:
- **OWL Ontology (`docs/codata.ttl`)**: Formal class and property definitions copied alongside the distribution files.
- **Deprecation (`owl:deprecated`)**: Automatically tags constants that are no longer part of the latest CODATA release (e.g., conventional electric units retired after the 2019 SI redefinition).
- **Backward-Compatible Aliases (`owl:sameAs`)**: Preserves links from legacy IRIs to canonical PascalCase IRIs.
- **Schema.org, QUDT, UCUM, SI Digital Framework, and Wikidata**: Cross-references for units, constants, and concepts.

## Usage

Run the script via `uv` or directly from the `utils` directory:

```bash
uv run codata-package [-o OUTPUT_DIR] [-d]
```

### Arguments:
- `-o, --output-dir`: Specify where to save the generated `.ttl` and `.jsonld` files (defaults to `dist/rdf/`).
- `-d, --debug`: Enable detailed debug logging for troubleshooting the conversion process.

## Output Files
The utility generates three products in the `dist/rdf/` directory:
- `codata_constants.ttl`: High-precision Turtle dataset representation.
- `codata_constants.jsonld`: Semantically enriched JSON-LD dataset representation.
- `codata.ttl`: Formal OWL/RDFS ontology for the `https://w3id.org/codata/model/` namespace.
