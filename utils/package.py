"""
Package the CODATA constants data
"""
# Todo:
# - Need to create the ontology for the model (namespaces, properties, classes)
# - Add Versions
# - Create monkey patch to encode floats with full precision when writing JSON-LD and serialize both float and string values/uncertainties
#

import argparse
from functools import lru_cache
import json
import logging
import os
from urllib.parse import quote
from rdflib import XSD, Graph, Namespace, Literal, RDF, URIRef, SKOS, DCTERMS

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

MODEL = Namespace("https://w3id.org/codata/model/")
CONCEPT = Namespace("https://w3id.org/codata/concepts/")
CONSTANT = Namespace("https://w3id.org/codata/constants/")
QUANTITY = Namespace("https://w3id.org/codata/quantities/")
UNIT = Namespace("https://w3id.org/codata/units/")
VERSION = Namespace("https://w3id.org/codata/constants/versions/")

SCHEMA = Namespace("https://schema.org/")
QUDT = Namespace("http://qudt.org/vocab/constant/")
UCUM = Namespace("https://w3id.org/uom/")
SICONSTANT = Namespace("https://si-digital-framework.org/constants/")
SIUNIT = Namespace("https://si-digital-framework.org/SI/units/")
WIKIDATA = Namespace("https://www.wikidata.org/entity/")

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
    logger.debug(f"Generating concept {data.get('id')}")
    g = new_rdf_graph()
    g.add((concept_uriref, RDF.type, MODEL.Concept))
    # g.add((concept_uriref, RDF.type, SKOS.Concept))
    g.add((concept_uriref, SCHEMA.identifier, Literal(data.get('id'))))
    g.add((concept_uriref, SKOS.prefLabel, Literal(data.get('name'))))
    return g

def generate_rdf_conceptual_properties(resource_uriref: URIRef, data: dict, concepts: dict) -> Graph:
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
    logger.debug(f"Generating constants values graph for: {data.get('id')}")
    version = data.get('version')
    g = new_rdf_graph()
    g.add((value_uriref, RDF.type, MODEL.ConstantValue))
    g.add((value_uriref, MODEL.versionId, Literal(version)))
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

def generate_rdf_quantity(quantity_uriref: URIRef, data: dict) -> Graph:
    logger.debug(f"Generating quantity {data.get('id')}")
    g = new_rdf_graph()
    g.add((quantity_uriref, RDF.type, MODEL.Quantity))
    # g.add((quantity_uriref, RDF.type, SKOS.Concept)) # Should be in the ontology
    g.add((quantity_uriref, SCHEMA.identifier, Literal(data.get('id'))))
    if data.get('name'):
        g.add((quantity_uriref, SKOS.prefLabel, Literal(data.get('name'))))
    return g

def generate_rdf_unit(unit_uriref: URIRef, data: dict) -> Graph:
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
