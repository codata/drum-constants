"""
Package the CODATA constants data
"""

# PENDING:
# - Should we use Constant.hasValue (common in OWL) as a property, or Constant.value (widely used: QUDT, schema.org, DCAT). Same for Quantity.hasContant.
# - Review URIs for resources and identifiers. Confirm use of w3ids (and then update config in w3ids GitHub repo)
# - AngstromStar? What's the 'constant'? isn't this a unit?
# - Should we use PlanckConstantOver2Pi (commonly used) or ReducedPlanckConstant (NIST)? Same for others.
# Units
# - The 'conventional' (1990) constants in the NIST file do not use the '90' suffix as units.
#   - One exception: FaradayConstantConventionalElectricCurrent which uses C90 C_90_mol^-1
# - the *90 conventional units are not in the SI reference point (C90, A90, etc.). C90 expression return C^90.
# - What about E_h unit (Hartree energy). Should this just map to J?
# Todo:
# - Need to create the ontology for the model (namespaces, properties, classes)
#

import argparse
from functools import lru_cache
import json
import logging
import os
from rdflib import XSD, Graph, Namespace, Literal, RDF, URIRef, SKOS, DCTERMS
from urllib.parse import quote

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

MODEL = Namespace("https://w3id.org/codata/fundamental/model/")
CONSTANT = Namespace("https://w3id.org/codata/fundamental/constants/")
QUANTITY = Namespace("https://w3id.org/codata/fundamental/quantities/")
UNIT = Namespace("https://w3id.org/codata/fundamental/units/")

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
    g.bind("codata", MODEL)
    g.bind("constant", CONSTANT)
    g.bind("quantity", QUANTITY)
    g.bind("unit", UNIT)
    return g

def generate_rdf() -> Graph:
    json_data = get_codata_json()
    g = new_rdf_graph()
    # UNITS
    for unit in json_data.get("units", []):
        unit_uriref = URIRef(UNIT[unit.get('id')])
        g += generate_rdf_unit(unit_uriref, unit)
    # QUANTITIES
    for quantity in json_data.get("quantities", []):
        quantity_uriref = URIRef(QUANTITY[quantity.get('id')])
        g += generate_rdf_quantity(quantity_uriref, quantity)
        # CONSTANTS
        for constant in quantity.get("constants", []):
            constant_uriref = URIRef(CONSTANT[constant.get('id')])
            g.add((quantity_uriref, MODEL.hasConstant, constant_uriref))
            g += generate_rdf_constant(constant_uriref, constant)
            g.add((constant_uriref, SKOS.broader, quantity_uriref))
            # VERSIONS/VALUES
            for value in constant.get("values", []):
                version = value.get('version')
                value_uriref = URIRef(f"{constant_uriref}/{version}")
                g += generate_rdf_constant_value(value_uriref, value)
                g.add((constant_uriref, MODEL.hasValue, value_uriref))
                g.add((value_uriref, DCTERMS.isVersionOf, constant_uriref))

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

    # label
    g.add((constant_uriref, SKOS.prefLabel, Literal(data.get('name'),lang="en")))
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
            g.add((alternate_id_uriref, SCHEMA.url, URIRef(quote(f"https://physics.nist.gov/cgi-bin/cuu/Value?{value}"))))
        elif alternate_id == "QUDT":
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
    g.add((value_uriref, MODEL.version, Literal(version)))
    if data.get('value') is not None:
        g.add((value_uriref, MODEL.value, Literal(data.get('value'), datatype=XSD.string))) # use string to prevent loss of precision
    else:
        logger.error(f"Constant value missing for {value_uriref} version {version}")
    if data.get('uncertainty') is not None:
        g.add((value_uriref, MODEL.uncertainty, Literal(data.get('uncertainty'), datatype=XSD.string))) # use string to prevent loss of precision
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
