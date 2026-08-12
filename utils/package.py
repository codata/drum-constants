"""
CODATA Constants Packaging Tool

This script processes the CODATA constants data from a JSON source and generates
semantic representations in RDF formats (Turtle and JSON-LD). It implements
specialized handling for high-precision physical constants to ensure that
accuracy is preserved during serialization and transport.

Key Features:
1. High-Precision Numeric Handling: Uses Decimal for formatting and a custom
   serializer to prevent rounding of xsd:double/xsd:decimal in Turtle.
2. JSON-LD Float Precision: Monkey-patches the JSON encoder to ensure 8-digit
   precision for floating-point values.
3. Automated Validation: Implements an in-memory and round-trip validation
   suite that compares serialized numeric literals against authoritative
   master strings.
4. Semantic Enrichment: Links CODATA constants to external vocabularies like
   QUDT, SI-Digital-Framework, and Wikidata.

Usage:
    python package.py [-o OUTPUT_DIR] [-d]
"""

import argparse
import json
import json.encoder
import logging
import os
from decimal import Decimal, InvalidOperation
from functools import lru_cache
from urllib.parse import quote

from rdflib import DCTERMS, RDF, SKOS, XSD, Graph, Literal, Namespace, URIRef
from rdflib.plugin import Serializer, register
from rdflib.plugins.serializers.turtle import TurtleSerializer

# Monkey patch json encoder to increase float precision to 8 digits after decimal point
# This is used when serializing to JSON-LD or other JSON-based formats
json.encoder.c_make_encoder = None  # type: ignore[attr-defined] # pyrefly: ignore
json.encoder.FLOAT_REPR = lambda o: format(o, '.8f')  # type: ignore[attr-defined] # pyrefly: ignore


SCHEMA = Namespace("https://schema.org/")
QUDT = Namespace("http://qudt.org/vocab/constant/")
UCUM = Namespace("https://w3id.org/uom/")
SICONSTANT = Namespace("https://si-digital-framework.org/constants/")
SIUNIT = Namespace("https://si-digital-framework.org/SI/units/")
WIKIDATA = Namespace("https://www.wikidata.org/entity/")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

MODEL = Namespace("https://w3id.org/codata/model/")
CONCEPT = Namespace("https://w3id.org/codata/concepts/")
CONSTANT = Namespace("https://w3id.org/codata/constants/")
QUANTITY = Namespace("https://w3id.org/codata/quantities/")
UNIT = Namespace("https://w3id.org/codata/units/")
VERSION = Namespace("https://w3id.org/codata/constants/versions/")

def format_float_precision(val_str: str, precision: int = 12) -> str:
    """
    Formats a numeric string to a high-precision float representation.

    This function uses the Decimal class to avoid binary floating-point rounding
    errors and ensures that the output string has at least the requested
    number of significant digits of precision.

    Args:
        val_str: The original numeric value as a string.
        precision: The number of decimal places to ensure for the output.

    Returns:
        A precisely formatted string, or the original string if the
        standard formatting would result in data loss.
    """
    try:
        d = Decimal(val_str)
        # normalize to remove trailing zeros and then use scientific notation if needed
        # but ensure we have at least 'precision' decimal places if possible
        if 'e' in val_str.lower() or 'E' in val_str.lower() or abs(d) < Decimal('1e-4'):
            formatted = format(d, f'.{precision}e')
        else:
            formatted = format(d, f'.{precision}f')

        # Validation: if the formatted float has less precision than the original, use original
        if Decimal(formatted) != d:
            return val_str
        return formatted
    except Exception:
        return val_str

def validate_graph_precision(g: Graph, name: str = "In-memory"):
    """
    Validates numeric literals in an RDF graph against their master strings.

    This function iterates through all triples containing numeric values and
    compares them to the master string value stored in the graph. It calculates
    the relative error for floats and check for exact matches for decimals.

    Args:
        g: The RDFLib Graph to validate.
        name: A descriptive name for the validation source (used in logging).

    Raises:
        ValueError: If any precision discrepancies are detected.
    """
    logger.info(f"Validating {name} graph precision...")
    errors = 0
    checked = 0
    for s, p, o in g:
        if p in [MODEL.valueFloat, MODEL.uncertaintyFloat, MODEL.valueDecimal, MODEL.uncertaintyDecimal]:
            checked += 1
            # determine if it's a value or uncertainty
            is_val = p in [MODEL.valueFloat, MODEL.valueDecimal]
            string_p = MODEL.value if is_val else MODEL.uncertainty
            string_val = g.value(s, string_p)

            if string_val:
                try:
                    orig_str = str(string_val)
                    new_lex = str(o)

                    if p in [MODEL.valueDecimal, MODEL.uncertaintyDecimal]:
                        # Decimal should be EXACTly equal to the original when parsed back
                        # Use Decimal to handle the conversion from string correctly
                        if Decimal(orig_str) != Decimal(new_lex):
                            logger.error(f"Decimal precision loss detected in {name} at {s}:\n  Original: {orig_str}\n  Decimal:  {new_lex}")
                            errors += 1
                    else:
                        # Float/Double precision check with strict epsilon
                        orig_f = float(orig_str)
                        new_f = float(new_lex)
                        if orig_f != 0:
                            rel_error = abs(orig_f - new_f) / abs(orig_f)
                        else:
                            rel_error = abs(orig_f - new_f)

                        # Double precision epsilon is ~2.2e-16
                        if rel_error > 2e-16:
                            logger.error(f"Float precision loss detected in {name} at {s}:\n  Original: {orig_str}\n  Float:    {new_lex}")
                            errors += 1
                except (ValueError, InvalidOperation):
                    continue

    if errors > 0:
        raise ValueError(f"Validation failed for {name}: {errors} precision errors found in {checked} checked values.")
    logger.info(f"Validation successful for {name}: {checked} values verified.")

def validate_file_precision(filepath: str, format: str):
    """
    Performs a round-trip precision validation for a serialized file.

    Loads the specified file back into an RDF graph and runs the precision
    validation suite to ensure serialization did not degrade data accuracy.

    Args:
        filepath: Path to the RDF file on disk.
        format: The RDF format (e.g., 'turtle', 'json-ld').
    """
    logger.info(f"Performing round-trip validation for {filepath}...")
    temp_g = Graph()
    temp_g.parse(filepath, format=format)
    # Bind namespaces to the temp graph for correct property lookup
    temp_g.bind("codata", MODEL)
    validate_graph_precision(temp_g, os.path.basename(filepath))

class HighPrecisionTurtleSerializer(TurtleSerializer):
    """
    Custom Turtle Serializer for high-precision numeric data.

    Overrides the default label generation for xsd:double and xsd:decimal literal
    nodes. The standard rdflib Turtle serializer rounds doubles to 5-6
    significant digits for 'clean' formatting; this class bypasses that
    behavior by using the explicit lexical string and full datatype URIs.
    """
    def label(self, node, position):
        if isinstance(node, Literal):
            if node.datatype == XSD.double:
                # Use Python's standard float-to-string conversion which is full precision
                val = float(node)
                res = str(val)
                # Ensure it remains a double in RDF shorthand (needs 'e' or '.')
                if "e" not in res.lower() and "." not in res:
                    res += ".0"
                return res
            elif node.datatype == XSD.decimal:
                # Ensure decimals don't use scientific notation and have at least one dot
                val = node.toPython()
                res = format(val, "f")
                if "." not in res:
                    res += ".0"
                return res

        return super().label(node, position)

#    def label(self, node, position=None):
#        if isinstance(node, Literal):
#            # If it's a numeric type we care about, bypass rdflib's shortening/rounding
#            if node.datatype in [XSD.double, XSD.decimal]:
#                # Wrap with quotes and use full URI for datatype to be 100% safe for round-trips
#                return f'"{node}"^^<{node.datatype}>'
#       return super().label(node, position)

# Register the high precision turtle serializer
register('turtle-hp', Serializer, '__main__', 'HighPrecisionTurtleSerializer')

def get_codata_json() -> dict:
    """
    Loads and caches the source CODATA constants JSON data.

    Returns:
        The content of codata_constants.json as a dictionary.
    """
    @lru_cache(maxsize=1)
    def _load_codata_json():
        current_dir = os.path.dirname(os.path.abspath(__file__))
        json_path = os.path.join(current_dir, 'codata_constants.json')
        with open(json_path, 'r') as f:
            return json.load(f)
    return _load_codata_json()

def new_rdf_graph():
    """
    Initializes a new RDFLib graph with standard CODATA namespace bindings.

    Returns:
        An RDFLib Graph object with bound prefixes.
    """
    g = Graph()
    g.bind("codata", MODEL)
    g.bind("concept", CONCEPT)
    g.bind("constant", CONSTANT)
    g.bind("quantity", QUANTITY)
    g.bind("version", VERSION)
    g.bind("schema", SCHEMA)
    g.bind("si-constant", SICONSTANT)
    g.bind("si-unit", SIUNIT)
    g.bind("unit", UNIT)
    g.bind("ucum", UCUM)
    g.bind("wikidata", WIKIDATA)
    return g

def generate_rdf() -> Graph:
    """
    Orchestrates the conversion of JSON data into a semantic RDF graph.

    Iterates through concepts, units, versions, and quantities to build a
    comprehensive representation of the CODATA constants dataset.

    Returns:
        A populated RDFLib Graph.
    """
    json_data = get_codata_json()
    g = new_rdf_graph()
    # CONCEPTS URIs & INDEX
    # A concept can be a concept or a quantity.
    # Pre-generate the URIRef and add to index
    concepts_index = {}
    for concept in json_data.get("concepts", []):
        # add to index
        concepts_index[concept.get('id')] = concept
        # add URI to concept dict for later use
        if concept.get('is_quantity'):
            concept['uri'] = URIRef(QUANTITY[concept.get('id')])
        else:
            concept['uri'] = URIRef(CONCEPT[concept.get('id')])
    # CONCEPTS
    for concept in json_data.get("concepts", []):
        if concept.get('is_quantity'):
            # do not generate quantity concepts here, will do it when generating quantities
            continue
        concept_uriref = URIRef(CONCEPT[concept.get('id')])
        g += generate_rdf_concept(concept_uriref, concept)
        g += generate_rdf_conceptual_properties(concept_uriref, concept, concepts_index)
    # UNITS
    for version in json_data.get("units", []):
        unit_uriref = URIRef(UNIT[version.get('id')])
        g += generate_rdf_unit(unit_uriref, version)
    # VERSIONS
    for version in json_data.get("versions", []):
        version_uriref = URIRef(VERSION[version.get('id')])
        g += generate_rdf_version(version_uriref, version)
    # QUANTITIES
    for quantity in json_data.get("quantities", []):
        quantity_uriref = URIRef(QUANTITY[quantity.get('id')])
        g.add((quantity_uriref, RDF.type, MODEL.Concept)) # A Quantity is also a Concept
        g += generate_rdf_quantity(quantity_uriref, quantity)
        quantity_concept = concepts_index.get(quantity.get('id'))
        if quantity_concept:
            g += generate_rdf_conceptual_properties(quantity_uriref, quantity_concept, concepts_index)
        # CONSTANTS
        for constant in quantity.get("constants", []):
            constant_uriref = URIRef(CONSTANT[constant.get('id')])
            g.add((quantity_uriref, MODEL.hasConstant, constant_uriref))
            g += generate_rdf_constant(constant_uriref, constant)
            # related the constant to the quantity concept
            g.add((constant_uriref, MODEL.hasQuantity, quantity_uriref))
            # VERSIONS/VALUES
            for value in constant.get("values", []):
                version = value.get('version')
                value_uriref = URIRef(f"{constant_uriref}/{version}")
                g += generate_rdf_constant_value(value_uriref, value)
                # associate value <--> constant
                g.add((constant_uriref, MODEL.hasValue, value_uriref))
                g.add((value_uriref, DCTERMS.isVersionOf, constant_uriref))
                # associate value with version
                g.add((value_uriref, MODEL.hasVersion, URIRef(VERSION[version])))
                # Give the value. a friendly name
                g.add((value_uriref, SKOS.prefLabel, Literal(f"{version} {constant.get('name')}")))
    return g

def generate_rdf_concept(concept_uriref: URIRef, data: dict) -> Graph:
    """
    Generates an RDF representation for a CODATA concept.

    Args:
        concept_uriref: The URIRef of the concept.
        data: Dictionary containing concept metadata (id, name).

    Returns:
        A Graph containing the concept triples.
    """
    logger.debug(f"Generating concept {data.get('id')}")
    g = new_rdf_graph()
    g.add((concept_uriref, RDF.type, MODEL.Concept))
    # g.add((concept_uriref, RDF.type, SKOS.Concept))
    g.add((concept_uriref, SCHEMA.identifier, Literal(data.get('id'))))
    g.add((concept_uriref, SKOS.prefLabel, Literal(data.get('name'))))
    return g

def generate_rdf_conceptual_properties(resource_uriref: URIRef, data: dict, concepts: dict) -> Graph:
    """
    Generates triples for semantic relationships between concepts.

    Handles broader, parts, related, and exactMatch (Wikidata) relationships.

    Args:
        resource_uriref: The URIRef of the resource being described.
        data: Dictionary containing semantic relationship data.
        concepts: An index of all concepts for URI resolution.

    Returns:
        A Graph containing the relationship triples.
    """
    g = new_rdf_graph()
    if data.get('name_fr'):
        g.add((resource_uriref, SKOS.prefLabel, Literal(data.get('name_fr'),lang="fr")))
    for broader_id in data.get('broader', []):
        broader_uriref = concepts[broader_id].get('uri')
        g.add((resource_uriref, SKOS.broader, broader_uriref))
    for part_id in data.get('parts', []):
        part_uriref = concepts[part_id].get('uri')
        g.add((resource_uriref, DCTERMS.hasPart, part_uriref))
    for related_id in data.get('related', []):
        related_uriref = concepts[related_id].get('uri')
        g.add((resource_uriref, SKOS.related, related_uriref))
    for alternate_id, value in data.get('ids', {}).items():
        if alternate_id == "WIKIDATA":
            g.add((resource_uriref, SKOS.exactMatch , URIRef(WIKIDATA[value])))
    return g

def generate_rdf_constant(constant_uriref: URIRef,  data: dict) -> Graph:
    """
    Generates an RDF representation for a specific physical constant.

    Includes IDs, labels, unit associations, and external identifiers
    (NIST, QUDT, SI).

    Args:
        constant_uriref: The URIRef of the constant.
        data: Dictionary containing the constant's details.

    Returns:
        A Graph containing the constant's triples.
    """
    logger.debug(f"Generating constants {data.get('id')}")
    g = new_rdf_graph()
    g.add((constant_uriref, RDF.type, MODEL.Constant))
    g.add((constant_uriref, SCHEMA.identifier, Literal(data.get('id'))))

    # label
    g.add((constant_uriref, SKOS.prefLabel, Literal(data.get('name'))))
    if data.get('name_fr'):
        g.add((constant_uriref, SKOS.prefLabel, Literal(data.get('name_fr'),lang="fr")))

    # Unit
    if data.get('unit_id'):
        unit_uriref = URIRef(UNIT[data.get('unit_id')])
        g.add((constant_uriref, MODEL.hasUnit, unit_uriref))

    if data.get('is_ratio'):
        g.add((constant_uriref, MODEL.isRatio, Literal(data.get('is_ratio'), datatype=XSD.boolean)))
    if data.get('is_relationship'):
        g.add((constant_uriref, MODEL.isRelationship, Literal(data.get('is_relationship'), datatype=XSD.boolean)))

    # additional identifiers / URIs
    for alternate_id, value in data.get('ids', {}).items():
        if alternate_id == "NIST":
            alternate_id_uriref = URIRef(constant_uriref+"#NIST")
            g.add((constant_uriref, SCHEMA.identifier, alternate_id_uriref))
            g.add((alternate_id_uriref, RDF.type, SCHEMA.PropertyValue))
            g.add((alternate_id_uriref, SCHEMA.propertyID, Literal("NIST")))
            g.add((alternate_id_uriref, SCHEMA.value, Literal(value)))
            g.add((alternate_id_uriref, SCHEMA.url, URIRef(f"https://pml.nist.gov/cgi-bin/cuu/Value?{value}")))
        elif alternate_id == "QUDT":
            alternate_id_uriref = URIRef(constant_uriref+"#QUDT")
            g.add((constant_uriref, SCHEMA.identifier, alternate_id_uriref))
            g.add((alternate_id_uriref, RDF.type, SCHEMA.PropertyValue))
            g.add((alternate_id_uriref, SCHEMA.propertyID, Literal("QUDT")))
            g.add((alternate_id_uriref, SCHEMA.value, Literal(value)))
            g.add((alternate_id_uriref, SCHEMA.url, URIRef(QUDT[value])))
        elif alternate_id == "SI":
            alternate_id_uriref = URIRef(constant_uriref+"#SI")
            g.add((constant_uriref, SCHEMA.identifier, alternate_id_uriref))
            g.add((alternate_id_uriref, RDF.type, SCHEMA.PropertyValue))
            g.add((alternate_id_uriref, SCHEMA.propertyID, Literal("SI")))
            g.add((alternate_id_uriref, SCHEMA.value, Literal(value)))
            g.add((alternate_id_uriref, SCHEMA.url, URIRef(SICONSTANT[value])))
    return g

def generate_rdf_constant_value(value_uriref: URIRef, data: dict) -> Graph:
    """
    Generates triples for a specific versioned value of a physical constant.

    This function implements the high-precision numeric literal generation
    for the master string, decimal, and float representations.

    Args:
        value_uriref: The URIRef for this specific versioned value.
        data: Dictionary containing value, uncertainty, and metadata.

    Returns:
        A Graph containing the value triples.
    """
    logger.debug(f"Generating constants values graph for: {data.get('id')}")
    version = data.get('version')
    g = new_rdf_graph()
    g.add((value_uriref, RDF.type, MODEL.ConstantValue))
    g.add((value_uriref, MODEL.versionId, Literal(version)))

    val_str = data.get('value')
    if val_str is not None:
        # Initial string representation (preserves full precision)
        g.add((value_uriref, MODEL.value, Literal(val_str, datatype=XSD.string)))

        # Add decimal and float representations
        try:
            # Use original string for Decimal
            g.add((value_uriref, MODEL.valueDecimal, Literal(val_str, datatype=XSD.decimal)))

            # For Float/Double, we use the literal with XSD.double.
            # Our custom serializer will ensure this is not rounded.
            val_float_formatted = format_float_precision(val_str, 12)
            g.add((value_uriref, MODEL.valueFloat, Literal(val_float_formatted, datatype=XSD.double)))
        except (ValueError, TypeError, InvalidOperation):
            logger.error(f"Could not convert value to numeric literals: {val_str}")
    else:
        logger.error(f"Constant value missing for {value_uriref} version {version}")

    unc_str = data.get('uncertainty')
    if unc_str is not None:
        # Initial string representation (preserves full precision)
        g.add((value_uriref, MODEL.uncertainty, Literal(unc_str, datatype=XSD.string)))

        # Add decimal and float representations
        try:
            g.add((value_uriref, MODEL.uncertaintyDecimal, Literal(unc_str, datatype=XSD.decimal)))

            unc_float_formatted = format_float_precision(unc_str, 12)
            g.add((value_uriref, MODEL.uncertaintyFloat, Literal(unc_float_formatted, datatype=XSD.double)))
        except (ValueError, TypeError, InvalidOperation):
            pass

    if data.get('exponent') is not None:
        g.add((value_uriref, MODEL.exponent, Literal(data.get('exponent'), datatype=XSD.integer)))
    if data.get('is_exact') is not None:
        g.add((value_uriref, MODEL.isExact, Literal(data.get('is_exact'), datatype=XSD.boolean)))
    if data.get('is_truncated') is not None:
        g.add((value_uriref, MODEL.isTruncated, Literal(data.get('is_truncated'), datatype=XSD.boolean)))
    return g

def generate_rdf_quantity(quantity_uriref: URIRef, data: dict) -> Graph:
    """
    Generates an RDF representation for a physical quantity.

    Args:
        quantity_uriref: The URIRef of the quantity.
        data: Dictionary containing quantity metadata.

    Returns:
        A Graph containing the quantity triples.
    """
    logger.debug(f"Generating quantity {data.get('id')}")
    g = new_rdf_graph()
    g.add((quantity_uriref, RDF.type, MODEL.Quantity))
    # g.add((quantity_uriref, RDF.type, SKOS.Concept)) # Should be in the ontology
    g.add((quantity_uriref, SCHEMA.identifier, Literal(data.get('id'))))
    if data.get('name'):
        g.add((quantity_uriref, SKOS.prefLabel, Literal(data.get('name'))))
    return g

def generate_rdf_unit(unit_uriref: URIRef, data: dict) -> Graph:
    """
    Generates an RDF representation for an SI/UCUM unit.

    Args:
        unit_uriref: The URIRef of the unit.
        data: Dictionary containing unit identifiers.

    Returns:
        A Graph containing the unit triples.
    """
    logger.debug(f"Generating unit {data.get('id')}")
    g = new_rdf_graph()
    g.add((unit_uriref, RDF.type, MODEL.Unit))
    g.add((unit_uriref, SCHEMA.identifier, Literal(data.get('id'))))

    # additional identifiers / URIs
    for alternate_id, value in data.get('ids', {}).items():
        if alternate_id == "SI":
            alternate_id_uriref = URIRef(unit_uriref+"#SI")
            g.add((unit_uriref, SCHEMA.identifier, alternate_id_uriref))
            g.add((alternate_id_uriref, RDF.type, SCHEMA.PropertyValue))
            g.add((alternate_id_uriref, SCHEMA.propertyID, Literal("SI")))
            g.add((alternate_id_uriref, SCHEMA.identifier, Literal(value)))
            g.add((alternate_id_uriref, SCHEMA.url, URIRef(SIUNIT[value])))
        if alternate_id == "UCUM":
            alternate_id_uriref = URIRef(unit_uriref+"#UCUM")
            g.add((unit_uriref, SCHEMA.identifier, alternate_id_uriref))
            g.add((alternate_id_uriref, RDF.type, SCHEMA.PropertyValue))
            g.add((alternate_id_uriref, SCHEMA.propertyID, Literal("UCUM")))
            g.add((alternate_id_uriref, SCHEMA.identifier, Literal(value)))
            g.add((alternate_id_uriref, SCHEMA.url, URIRef(UCUM[quote(value)])))
    return g

def generate_rdf_version(version_uriref: URIRef, data: dict) -> Graph:
    """
    Generates an RDF representation for a CODATA version.

    Args:
        version_uriref: The URIRef of the version.
        data: Dictionary containing version ID and publication date.

    Returns:
        A Graph containing the version triples.
    """
    logger.debug(f"Generating version {data.get('id')}")
    g = new_rdf_graph()
    g.add((version_uriref, RDF.type, MODEL.Version))
    g.add((version_uriref, SCHEMA.identifier, Literal(data.get('id'))))
    g.add((version_uriref, DCTERMS.issued, Literal(data.get('published'), datatype=XSD.date)))
    return g

def main():
    parser = argparse.ArgumentParser(description="Package CODATA constants products")
    parser.add_argument(
        "-o", "--output-dir",
        default=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "dist/rdf"),
        help="Output directory for generated files"
    )
    parser.add_argument(
        "-d", "--debug",
        action="store_true",
        help="Enable debug logging"
    )
    args = parser.parse_args()

    # Setup logging level based on debug flag
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)

    # Ensure output directory exists
    os.makedirs(args.output_dir, exist_ok=True)

    # Generate the graph
    graph = generate_rdf()

    # Validate precision before saving
    validate_graph_precision(graph)

    # Save as Turtle using the custom high-precision serializer
    ttl_filepath = os.path.join(args.output_dir, "codata_constants.ttl")
    graph.serialize(destination=ttl_filepath, format="turtle-hp")
    logger.info(f"High-precision Turtle data saved to {ttl_filepath}")

    # Perform round-trip validation for Turtle
    validate_file_precision(ttl_filepath, "turtle")

    # Save as JSON-LD (utilizes the monkey patch for float precision)
    jsonld_filepath = os.path.join(args.output_dir, "codata_constants.jsonld")
    graph.serialize(destination=jsonld_filepath, format="json-ld", indent=4)
    logger.info(f"JSON-LD data saved to {jsonld_filepath}")

    # Perform round-trip validation for JSON-LD
    validate_file_precision(jsonld_filepath, "json-ld")



if __name__ == "__main__":
    main()
