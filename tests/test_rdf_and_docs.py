"""Automated verification of the CODATA RDF Knowledge Graph and Documentation."""

import math
import re
from pathlib import Path
import pytest
import rdflib
from rdflib.namespace import OWL, RDF, SKOS

ROOT_DIR = Path(__file__).resolve().parent.parent
TTL_PATH = ROOT_DIR / "dist" / "rdf" / "codata_constants.ttl"
ONTOLOGY_PATH = ROOT_DIR / "dist" / "rdf" / "codata.ttl"
MODEL_DOC_PATH = ROOT_DIR / "docs" / "CODATA_CONSTANTS_MODEL.md"
README_PATH = ROOT_DIR / "README.md"

MODEL = rdflib.Namespace("https://w3id.org/codata/model/")
CONSTANT = rdflib.Namespace("https://w3id.org/codata/constants/")
UNIT = rdflib.Namespace("https://w3id.org/codata/units/")


@pytest.fixture(scope="module")
def graph() -> rdflib.Graph:
    g = rdflib.Graph()
    g.parse(TTL_PATH, format="turtle")
    return g


def test_ontology_parses():
    """Verify that the formal OWL/RDFS ontology file exists and parses cleanly."""
    assert ONTOLOGY_PATH.exists()
    g = rdflib.Graph()
    g.parse(ONTOLOGY_PATH, format="turtle")
    assert (rdflib.URIRef("https://w3id.org/codata/model/"), RDF.type, OWL.Ontology) in g


def test_markdown_sparql_queries_return_results(graph: rdflib.Graph):
    """Extract all ```sparql code blocks from documentation and assert non-empty results."""
    sparql_pattern = re.compile(r"```sparql\s+(.*?)```", re.DOTALL)
    for doc_path in (MODEL_DOC_PATH, README_PATH):
        content = doc_path.read_text(encoding="utf-8")
        queries = sparql_pattern.findall(content)
        assert len(queries) > 0, f"Expected SPARQL queries in {doc_path.name}"
        for idx, query in enumerate(queries, start=1):
            results = list(graph.query(query))
            assert len(results) > 0, (
                f"SPARQL query #{idx} in {doc_path.name} returned 0 rows:\n{query}"
            )


def test_labels_have_language_tags_and_valid_si_casing(graph: rdflib.Graph):
    """Verify language tags on labels and ensure no badly cased SI symbols or Momentum typos."""
    bad_si_tokens = {"Mev", "Ev", "Kpa", "Gev", "Mhz", "Fm"}
    for s in graph.subjects(RDF.type, MODEL.Constant):
        const_id = str(s).split("/")[-1]
        pref_labels = list(graph.objects(s, SKOS.prefLabel))
        assert len(pref_labels) >= 1, f"Missing skos:prefLabel for {const_id}"
        for lbl in pref_labels:
            assert isinstance(lbl, rdflib.Literal)
            assert lbl.language in {"en", "fr"}, f"Expected @en or @fr language tag on {const_id} prefLabel {lbl!r}"
            if lbl.language == "en":
                words = set(re.findall(r"\b[A-Za-z]+\b", str(lbl)))
                overlap = words.intersection(bad_si_tokens)
                assert not overlap, f"Bad SI casing {overlap} in prefLabel {lbl!r} of {const_id}"
                if "Momentum" in const_id:
                    assert "Momentum" in str(lbl), (
                        f"Momentum constant {const_id} has truncated label {lbl!r}"
                    )

    # Specifically verify NeutronProtonMassDifferenceInU
    np_diff = CONSTANT.NeutronProtonMassDifferenceInU
    np_labels = [str(o) for o in graph.objects(np_diff, SKOS.prefLabel)]
    assert "Neutron - Proton Mass Difference In U" in np_labels


def test_deprecated_constants_and_2022_coverage(graph: rdflib.Graph):
    """Verify every constant either has a 2022 ConstantValue or is marked owl:deprecated true."""
    expected_deprecated = {
        "FaradayConstantConventionalElectricCurrent",
        "MolarPlanckConstantTimesC",
        "TritonElectronMagneticMomentRatio",
        "TritonNeutronMagneticMomentRatio",
    }
    actual_deprecated = set()
    missing_2022 = set()

    for s in graph.subjects(RDF.type, MODEL.Constant):
        const_id = str(s).split("/")[-1]
        is_dep = (s, OWL.deprecated, rdflib.Literal(True)) in graph
        if is_dep:
            actual_deprecated.add(const_id)

        has_2022 = False
        for val_uri in graph.objects(s, MODEL.hasValue):
            if str(val_uri).endswith("/2022"):
                has_2022 = True
                # Verify 2022 values do not emit codata:isTruncated false
                assert (val_uri, MODEL.isTruncated, rdflib.Literal(False)) not in graph
        if not has_2022:
            missing_2022.add(const_id)

    assert actual_deprecated == expected_deprecated
    assert missing_2022 == expected_deprecated


def test_units_enrichment(graph: rdflib.Graph):
    """Verify codata:Unit nodes have skos:prefLabel and (for non-conventional SI units) ucum:ucum."""
    ucum_ns = rdflib.Namespace("https://w3id.org/uom/")
    units = list(graph.subjects(RDF.type, MODEL.Unit))
    assert len(units) >= 60
    for u in units:
        unit_id = str(u).split("/")[-1]
        assert list(graph.objects(u, SKOS.prefLabel)), f"Unit {u} missing skos:prefLabel"
        if "XC" not in unit_id:
            assert list(graph.objects(u, ucum_ns.ucum)), f"Unit {u} missing ucum:ucum"
            assert list(graph.objects(u, ucum_ns.si_expression)), f"Unit {u} missing ucum:si_expression"


def test_metrological_identities_2022(graph: rdflib.Graph):
    """Verify fundamental physical relations among 2022 CODATA values."""
    def get_float(const_id: str) -> float:
        uri = CONSTANT[f"{const_id}/2022"]
        val = graph.value(uri, MODEL.valueFloat)
        assert val is not None, f"Missing 2022 valueFloat for {const_id}"
        return float(val)

    c = get_float("SpeedOfLight")
    h = get_float("PlanckConstant")
    e = get_float("ElementaryCharge")
    k = get_float("BoltzmannConstant")
    n_a = get_float("AvogadroConstant")
    r_gas = get_float("MolarGasConstant")
    faraday = get_float("FaradayConstant")
    alpha = get_float("FineStructureConstant")
    m_e = get_float("ElectronMass")
    rydberg = get_float("RydbergConstant")
    hartree = get_float("HartreeEnergy")

    # Exact SI defining constants
    assert c == 299792458.0
    assert math.isclose(h, 6.62607015e-34, rel_tol=1e-15)
    assert math.isclose(e, 1.602176634e-19, rel_tol=1e-15)
    assert math.isclose(k, 1.380649e-23, rel_tol=1e-15)
    assert math.isclose(n_a, 6.02214076e23, rel_tol=1e-15)

    # Derived identities: R = k * N_A, F = N_A * e, E_h = 2 * R_inf * h * c = alpha^2 * m_e * c^2
    assert math.isclose(r_gas, k * n_a, rel_tol=1e-9)
    assert math.isclose(faraday, n_a * e, rel_tol=1e-9)
    assert math.isclose(hartree, 2.0 * rydberg * h * c, rel_tol=1e-9)
    assert math.isclose(hartree, (alpha**2) * m_e * (c**2), rel_tol=1e-9)
