# CODATA DRUM: Fundamental Physical Constants

[![License: CC BY 4.0](https://img.shields.io/badge/License-CC%20BY%204.0-lightgrey.svg)](http://creativecommons.org/licenses/by/4.0/)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

A comprehensive digitization project that transforms CODATA fundamental physical constants into machine-actionable and legacy formats, enabling seamless integration with modern data science workflows, AI systems, and agent-based applications.

## 🎯 Project Objectives

**Digital Transformation**: Convert fundamental physical constants from human-readable documents into robust, machine-readable formats (JSON, RDF/Turtle) aligned with [FAIR data principles](https://www.go-fair.org/fair-principles/)).

**API-First Approach**: Provide industry-standard REST APIs for programmatic access to constant definitions, values, and metadata across all CODATA releases (1998-2022).

**AI & Data Science Ready**: Enable seamless integration with large language models (LLMs), AI agents, and data science pipelines through structured semantic data and comprehensive query capabilities.

**Robust Semantic Infrastructure**: Establish a comprehensive semantic model with rich ontological relationships, associated domain knowledge, and SPARQL endpoints for advanced querying and reasoning over fundamental constants data.

**Interoperability**: Harmonize with existing standards (QUDT, UCUM, SI Digital Framework) and provide cross-references to enhance discoverability and integration.

## 🏗️ Architecture & Implementation

### Data Formats & Serializations

- **JSON**: Structured hierarchical format for programmatic consumption
- **RDF/Turtle**: Semantic web format with full ontology (37,000+ triples)
- **REST API**: HTTP endpoints for real-time data access

### Semantic Model

The project implements a comprehensive semantic model with 6 core entities:

1. **Concepts** - Taxonomic organization (SI Units, Elementary Particles, etc.)
2. **Quantities** - Physical measurable properties 
3. **Constants** - Specific physical constants with historical values
4. **Units** - Physical measurement units with SI/UCUM expressions
5. **Versions** - CODATA release metadata (1998, 2002, 2006, 2010, 2014, 2018, 2022)
6. **ConstantValues** - Measured values with uncertainties for each release

### Technology Stack

- **Data Processing**: Python scripts for ETL from NIST ASCII sources
- **Semantic Web**: RDFLib for RDF generation and validation
- **SPARQL & Triple Stores**: Query language and graph database support for semantic data access
- **Standards**: Integration with QUDT, UCUM, SI Digital Framework, Wikidata

## 🚀 Quick Start

### Data Access

```bash
# Download RDF dataset
wget https://github.com/codata/drum-constants/raw/main/dist/rdf/codata_constants.ttl

# Download JSON dataset  
wget https://github.com/codata/drum-constants/raw/main/utils/codata_constants.json
```

### Local Development

```bash
# Clone repository
git clone https://github.com/codata/drum-constants.git
cd drum-constants

# Generate RDF from source data
cd utils
python package.py
```

### SPARQL Queries

The RDF dataset supports rich semantic queries:

```sparql
# Find all SI defining constants
PREFIX codata: <https://w3id.org/codata/fundamental/model/>
PREFIX concept: <https://w3id.org/codata/fundamental/concepts/>

SELECT ?constant ?label WHERE {
    ?constant a codata:Constant ;
              skos:prefLabel ?label ;
              codata:hasQuantity ?quantity .
    ?quantity dcterms:hasPart ?concept .
    ?concept skos:broader* concept:SIDefiningConstant .
}
```

## 📊 Dataset Coverage

- **7 CODATA Releases**: Complete historical coverage (1998-2022)
- **350+ Constants**: All fundamental physical constants from NIST
- **Multi-format**: JSON, RDF datasets
- **Multilingual**: English and French labels
- **Cross-referenced**: NIST, QUDT, Wikidata identifiers
- **Version Tracking**: Evolution of values and uncertainties over time

## 🔬 Use Cases & Applications

### For Data Scientists
- **Pandas Integration**: Direct JSON loading for analysis
- **Uncertainty Analysis**: Track measurement precision evolution
- **Unit Conversion**: SI, UCUM, and natural unit systems
- **Statistical Analysis**: Historical value trends and correlations

### For AI/LLM/Agents
- **Structured Knowledge**: Semantic RDF for reasoning systems
- **Direct File Access**: Load JSON/RDF datasets for processing
- **Contextual Search**: Find constants by physical concepts
- **Validation**: Verify calculations against authoritative values

### For Researchers
- **Citation Ready**: Traceable to CODATA/NIST sources
- **Historical Analysis**: Compare values across decades
- **Interoperability**: Compatible with QUDT/UCUM ecosystems
- **FAIR Compliance**: Findable, Accessible, Interoperable, Reusable

## 📁 Repository Structure

```
drum-constants/
├── utils/           # Data processing utilities
│   ├── package.py   # RDF generation script
│   ├── codata_constants.py # Data parsing
│   └── codata_constants.json # Processed dataset
├── dist/rdf/        # Generated RDF/Turtle files
├── nist/           # Raw NIST ASCII source data
└── docs/           # Documentation and model specs
```

## 🔗 Standards & Interoperability

- **QUDT**: Quantity, Unit, Dimension, and Type integration
- **UCUM**: Unified Code for Units of Measure expressions  
- **SI Digital Framework**: SI base unit relationships
- **Wikidata**: Cross-references for enhanced discoverability
- **Dublin Core**: Metadata and versioning
- **SKOS**: Concept organization and hierarchies

## 🛠️ Development Roadmap

### Current Release (v1.0)
✅ Complete NIST dataset digitization (1998-2022)  
✅ JSON and RDF serializations  
✅ Comprehensive semantic model documentation  

### Next Release (v1.1)
🔄 New API project deployment  
🔄 Enhanced SPARQL endpoint  
🔄 OpenAPI/Swagger documentation  
🔄 Docker containerization  

### Future Releases
📅 Real-time NIST synchronization  
📅 GraphQL API support  
📅 Enhanced unit conversion utilities  
📅 Integration with computational physics libraries  

## 📖 Documentation

- **[Semantic Model Guide](docs/CODATA_CONSTANTS_MODEL.md)**: Complete RDF ontology documentation
- **Data Format Specifications**: JSON and RDF structure documentation
- **SPARQL Examples**: Query patterns for common use cases
- **Integration Guides**: Language-specific usage examples

## 🤝 Contributing

We welcome contributions from the global metrology and data science communities:

- **Data Quality**: Report inconsistencies or missing values
- **Data Formats**: Suggest new serialization formats or improvements
- **Standards**: Propose additional format integrations
- **Documentation**: Improve guides and examples

## 📜 Licensing

**Data**: [Creative Commons Attribution 4.0 International License](http://creativecommons.org/licenses/by/4.0/)  
**Software**: [Apache License 2.0](https://www.apache.org/licenses/LICENSE-2.0.txt)

## 🏛️ About CODATA DRUM & TGFC

This project operates under the umbrella of the [CODATA Digital Representation of Units of Measure (DRUM)](https://codata.org/initiatives/task-groups/drum/) working group, advancing FAIR metrology across scientific disciplines. It also supports the mission and vision of the [CODATA Task Group on Fundamental Physical Constants (TGFC)](https://codata.org/initiatives/data-science-and-stewardship/fundamental-physical-constants/), which maintains and disseminates internationally recommended values of fundamental physical constants.

**Maintainer**: Pascal Heus (CODATA DRUM Task Group)  
**Support**: Use [GitHub Issues](https://github.com/codata/drum-constants/issues) for questions and assistance

## 📚 References

- [NIST Fundamental Physical Constants](https://physics.nist.gov/cuu/Constants/)
- [CODATA 2022 Recommended Values](https://doi.org/10.1103/RevModPhys.93.025010)
- [BIPM: The International System of Units (SI)](https://www.bipm.org/en/publications/si-brochure)
- [QUDT: Quantities, Units, Dimensions and Types](https://qudt.org)
- [UCUM: Unified Code for Units of Measure](https://ucum.org)
 