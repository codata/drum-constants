# CODATA Constants Packaging Utility (`package.py`)

The `package.py` utility is a specialized tool designed to convert parsed CODATA constants data into high-quality semantic RDF representations (Turtle and JSON-LD). It focuses on maintaining absolute numerical precision for physical constants through a multi-layered validation and serialization strategy.

## Purpose

The primary goal of this utility is to transform the intermediate `codata_constants.json` file into FAIR (Findable, Accessible, Interoperable, and Reusable) data products that can be used in scientific applications, knowledge graphs, and semantic reasoning systems without losing the precision inherent in the source NIST data.

## Key Features

### 1. High-Precision Numeric Handling
The utility implements a refined strategy for representing physical constants and their uncertainties:
- **Lexical Stability**: Preserves the original NIST string representation for every value.
- **Decimal Representation**: Generates `xsd:decimal` literals using Python's `Decimal` class to avoid binary float rounding errors.
- **Float Representation**: Generates `xsd:double` literals with at least 12 digits of precision.

### 2. Custom High-Precision Serializer
Standard RDF serializers often round floating-point numbers to shorter scientific notation (e.g., rounding `7294.29954171` to `7.2943e+03`). `package.py` includes a `HighPrecisionTurtleSerializer` that:
- Bypasses automatic numeric shortening in Turtle output.
- Forces explicit lexical forms for all numeric literals.
- Ensures that the resulting Turtle file matches the original data bit-for-bit in precision.

### 3. JSON-LD Optimization
To ensure precision in JSON-LD (and other JSON-based formats), the utility:
- Monkey-patches the `json` encoder to ensure that floating-point values are serialized with at least 8 digits after the decimal point.
- Prevents the standard JSON "e-notation" simplification from degrading the accuracy of the physical constants.

### 4. Automated Validation Suite
The utility includes a built-in validation engine that performs three checks per execution:
- **In-Memory Validation**: Verifies generated literals against master strings immediately after graph construction.
- **Turtle Round-Trip**: Re-parses the saved `.ttl` file and verifies every numeric value against the source data.
- **JSON-LD Round-Trip**: Re-parses the saved `.jsonld` file to ensure the serialization process was loss-less.
- **Precision Threshold**: Discrepancies greater than $2 \times 10^{-16}$ (machine epsilon for doubles) trigger a failure, preventing the creation of imprecise data products.

### 5. Semantic Enrichment
The utility maps CODATA entities to multiple authoritative vocabularies:
- **Schema.org**: For general discoverability and identifiers.
- **QUDT**: Mapping to the Quantity, Unit, Dimension and Type ontology.
- **SI Digital Framework**: Alignment with the SI-Digital-Framework constant and unit definitions.
- **Wikidata**: Linking core concepts to their respective Wikidata entries.

## Usage

Run the script from the `utils` directory:

```bash
python package.py [-o OUTPUT_DIR] [-d]
```

### Arguments:
- `-o, --output-dir`: Specify where to save the generated `.ttl` and `.jsonld` files (defaults to `dist/rdf/`).
- `-d, --debug`: Enable detailed debug logging for troubleshooting the conversion process.

## Output Files
The utility generates two primary products in the `dist/rdf/` directory:
- `codata_constants.ttl`: A high-precision Turtle representation.
- `codata_constants.jsonld`: A semantically enriched JSON-LD representation.
