"""
Package the CODATA constants data
"""

# PENDING:
# - should we use Constant.hasValue or Constant.value (QUDT, schema.org, DCAT). Same for Quantity.hasContant.
# - Review URIs for resources and identifiers. Confirm use of w3ids (and then update config)
# - Fix duplicate ids for 'over 2 pi' vs 'reduced'
# - AngstromStar? What's the 'constant'?
# - Need to create the ontology for the model (namespaces, properties, classes)
#

import argparse
from functools import lru_cache
import json
import logging
import os
from rdflib import XSD, Graph, Namespace, Literal, RDF, URIRef, SKOS
from urllib.parse import quote

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

MODEL = Namespace("https://w3id.org/codata/fundamental/model/")
CONSTANTS = Namespace("https://w3id.org/codata/fundamental/constants/")
QUANTITIES = Namespace("https://w3id.org/codata/fundamental/quantities/")
UNITS = Namespace("https://w3id.org/codata/fundamental/units/")

SCHEMA = Namespace("https://schema.org/")
QUDT = Namespace("http://qudt.org/vocab/quantitykind/")
UCUM = Namespace("https://w3id.org/uom/")


def get_codata_json() -> dict:
    @lru_cache(maxsize=1)
    def _load_codata_json():
        current_dir = os.path.dirname(os.path.abspath(__file__))
        json_path = os.path.join(current_dir, 'codata_constants.json')
        with open(json_path, 'r') as f:
            return json.load(f)
    return _load_codata_json()

def new_rdf_graph():
    g = Graph()
    g.bind("drum", MODEL)
    g.bind("constant", CONSTANTS)
    g.bind("quantity", QUANTITIES)
    return g

def generate_rdf() -> Graph:
    json_data = get_codata_json()
    g = new_rdf_graph()
    # UNITS
    for unit in json_data.get("units", []):
        unit_uriref = URIRef(UNITS[unit.get('id')])
        g += generate_rdf_unit(unit_uriref, unit)
    # QUANTITIES
    for quantity in json_data.get("quantities", []):
        quantity_uriref = URIRef(QUANTITIES[quantity.get('id')])
        g += generate_rdf_quantity(quantity_uriref, quantity)
        # CONSTANTS
        for constant in quantity.get("constants", []):
            constant_uriref = URIRef(CONSTANTS[constant.get('id')])
            g.add((quantity_uriref, MODEL.hasConstant, constant_uriref))
            g += generate_rdf_constant(constant_uriref, constant)
            # VERSIONS/VALUES
            for value in constant.get("values", []):
                version = value.get('version')
                value_uriref = URIRef(f"{constant_uriref}/values/{version}")
                g += generate_rdf_constant_value(value_uriref, value)
                g.add((constant_uriref, MODEL.hasValue, value_uriref))

    return g

def generate_rdf_quantity(quantity_uriref: URIRef, data: dict) -> Graph:
    logger.debug(f"Generating quantity {data.get('id')}")
    g = new_rdf_graph()
    g.add((quantity_uriref, RDF.type, MODEL.Quantity))
    g.add((quantity_uriref, SCHEMA.identifier, Literal(data.get('id'))))
    if data.get('name'):
        g.add((quantity_uriref, SKOS.prefLabel, Literal(data.get('name'),lang="en")))
    return g

def generate_rdf_unit(unit_uriref: URIRef, data: dict) -> Graph:
    logger.debug(f"Generating unit {data.get('id')}")
    g = new_rdf_graph()
    g.add((unit_uriref, RDF.type, MODEL.Unit))
    g.add((unit_uriref, SCHEMA.identifier, Literal(data.get('id'))))

    # additional identifiers / URIs
    for alternate_id, value in data.get('ids', {}).items():
        if alternate_id == "SI":
            g.add((unit_uriref, SCHEMA.identifier, URIRef(quote(value))))
        if alternate_id == "UOM":
            g.add((unit_uriref, SCHEMA.identifier, URIRef(quote(value))))

    return g


def generate_rdf_constant(constant_uriref: URIRef,  data: dict) -> Graph:
    logger.debug(f"Generating constants {data.get('id')}")
    g = new_rdf_graph()
    g.add((constant_uriref, RDF.type, MODEL.Constant))
    g.add((constant_uriref, SCHEMA.identifier, Literal(data.get('id'))))

    # label (Preferably use BIPM)
    if data.get('name_bipm_en'):
        g.add((constant_uriref, SKOS.prefLabel, Literal(data.get('name_bipm_en'),lang="en")))
    else:
        g.add((constant_uriref, SKOS.prefLabel, Literal(data.get('name'),lang="en")))
    if data.get('name_bipm_fr'):
        g.add((constant_uriref, SKOS.prefLabel, Literal(data.get('name_bipm_fr'),lang="fr")))

    # Unit
    if data.get('unit_id'):
        units_uriref = URIRef(UNITS[data.get('unit_id')])
        g.add((constant_uriref, MODEL.hasUnit, units_uriref))

    # additional identifiers / URIs
    for alternate_id, value in data.get('ids', {}).items():
        if alternate_id == "SI":
            alternate_id_uriref = URIRef(constant_uriref+"#NIST")
            g.add((constant_uriref, SCHEMA.identifier, alternate_id_uriref))
            g.add((alternate_id_uriref, RDF.type, SCHEMA.PropertyValue))
            g.add((alternate_id_uriref, SCHEMA.propertyID, Literal("NIST")))
            g.add((alternate_id_uriref, SCHEMA.value, Literal(value)))
            g.add((alternate_id_uriref, SCHEMA.url, URIRef(quote(f"https://physics.nist.gov/cgi-bin/cuu/Value?{value}"))))
        if alternate_id == "QUDT":
            alternate_id_uriref = URIRef(constant_uriref+"#QUDT")
            g.add((constant_uriref, SCHEMA.identifier, alternate_id_uriref))
            g.add((alternate_id_uriref, RDF.type, SCHEMA.PropertyValue))
            g.add((alternate_id_uriref, SCHEMA.propertyID, Literal("QUDT")))
            g.add((alternate_id_uriref, SCHEMA.value, Literal(value)))
            g.add((alternate_id_uriref, SCHEMA.url, UCUM[value]))
    return g

def generate_rdf_constant_value(value_uriref: URIRef, data: dict) -> Graph:
    logger.debug(f"Generating constants values graph for: {data.get('id')}")
    version = data.get('version')
    g = new_rdf_graph()
    g.add((value_uriref, RDF.type, MODEL.ConstantValue))
    g.add((value_uriref, URIRef(str(MODEL.ConstantValue) + "#version"), Literal(version)))
    if data.get('value') is not None:
        g.add((value_uriref, MODEL.value, Literal(data.get('value'), datatype=XSD.double)))
    else:
        logger.error(f"Constant value missing for {value_uriref} version {version}")
    if data.get('uncertainty') is not None:
        g.add((value_uriref, MODEL.uncertainty, Literal(data.get('uncertainty'), datatype=XSD.double)))
    if data.get('exponent') is not None:
        g.add((value_uriref, MODEL.exponent, Literal(data.get('exponent'), datatype=XSD.integer)))
    if data.get('is_exact') is not None:
        g.add((value_uriref, MODEL.isExact, Literal(data.get('is_exact'), datatype=XSD.boolean)))
    if data.get('is_truncated') is not None:
        g.add((value_uriref, MODEL.isTruncated, Literal(data.get('is_truncated'), datatype=XSD.boolean)))
    return g

def main():
    parser = argparse.ArgumentParser(description="Package CODATA constants products")
    parser.add_argument(
        "-o", "--output-dir",
        default=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "dist"),
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
    args = parser.parse_args()
    
    # Ensure output directory exists
    os.makedirs(args.output_dir, exist_ok=True)
    
    # Generate the graph
    graph = generate_rdf()
    ttl_filepath = os.path.join(args.output_dir, "codata_constants.ttl")
    graph.serialize(destination=ttl_filepath, format="turtle")
    return

if __name__ == "__main__":
    main()
