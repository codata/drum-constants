"""Automated verification of the CODATA RDF Knowledge Graph and Documentation."""

import math
import re
from decimal import Decimal, localcontext
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
    """Verify that the formal OWL/RDFS ontology file exists and parses cleanly with v0.4.0 terms."""
    assert ONTOLOGY_PATH.exists()
    g = rdflib.Graph()
    g.parse(ONTOLOGY_PATH, format="turtle")
    ont = rdflib.URIRef("https://w3id.org/codata/model/")
    assert (ont, RDF.type, OWL.Ontology) in g
    assert (ont, OWL.versionInfo, rdflib.Literal("0.4.0")) in g
    for prop in (
        MODEL.derivedFrom,
        MODEL.adjustmentRole,
        MODEL.isComputed,
        MODEL.hasSymbol,
        MODEL.formula,
        MODEL.formulaLatex,
        MODEL.nistValue,
        MODEL.valueSource,
        MODEL.isNistTruncated,
        MODEL.significantDigits,
        MODEL.fitsFloat32,
        MODEL.fitsFloat64,
        MODEL.recommendedNumericType,
    ):
        assert (prop, RDF.type, None) in g, f"Ontology missing declaration for {prop}"


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
    bad_si_tokens = {"Mev", "Ev", "Kpa", "KPa", "Gev", "Mhz", "Fm"}
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
    assert "Neutron - Proton Mass Difference In u" in np_labels


# Case-sensitive symbols that occur in NIST quantity names
NIST_SYMBOL_TOKENS = frozenset({
    "u", "s", "m", "g", "K", "J", "T", "W", "Hz", "MHz", "GHz", "Pa", "kPa",
    "eV", "keV", "MeV", "GeV", "fm", "kg", "mol",
    "c", "h", "hc", "bar", "pi", "d", "p", "t", "x", "Z", "HD", "HT", "Cs", "Si",
})  # fmt: skip


def test_english_labels_keep_nist_symbol_case(graph: rdflib.Graph):
    """Symbols in a constant's NIST name(s) (u, c, hc, g, HD, kPa, ...) keep their case in prefLabel@en.

    Symbols that NIST writes in more than one case for the same constant are not checked.
    """
    import json

    names: dict[str, list[str]] = {}
    for f in sorted((ROOT_DIR / "nist").glob("*/allascii_*.json")):
        for row in json.loads(f.read_text(encoding="utf-8")):
            nist_id, qty = row.get("nist_id"), row.get("quantity")
            if nist_id and qty and qty not in names.setdefault(nist_id, []):
                names[nist_id].append(qty)
    assert names

    schema = rdflib.Namespace("https://schema.org/")
    bad = []
    compared = 0
    for s in graph.subjects(RDF.type, MODEL.Constant):
        nist_ids = [
            str(v)
            for node in graph.objects(s, schema.identifier)
            if (node, schema.propertyID, rdflib.Literal("NIST")) in graph
            for v in graph.objects(node, schema.value)
        ]
        compared += bool(nist_ids)
        cases: dict[str, set[str]] = {}
        for nist_id in nist_ids:
            for ref in names.get(nist_id, []):
                for tok in re.findall(r"[A-Za-z]+", ref):
                    if tok in NIST_SYMBOL_TOKENS:
                        cases.setdefault(tok.lower(), set()).add(tok)
        expected = {k: next(iter(v)) for k, v in cases.items() if len(v) == 1}
        for lbl in graph.objects(s, SKOS.prefLabel):
            if not isinstance(lbl, rdflib.Literal) or lbl.language != "en":
                continue
            for tok in re.findall(r"[A-Za-z]+", str(lbl)):
                want = expected.get(tok.lower())
                if want and tok != want:
                    bad.append(f"{s}: {lbl!r} has {tok!r}, NIST writes {want!r}")
    assert compared > 300
    assert not bad, "\n".join(bad)


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
        return float(str(val))

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


def test_computable_constants_and_two_source_rdf(graph: rdflib.Graph):
    """Verify computable roles, dependency edges, two-source values, and 34-digit decimal round-trip."""
    hbar = CONSTANT.ReducedPlanckConstant
    assert graph.value(hbar, MODEL.hasSymbol) == rdflib.Literal(r"\hbar")
    assert (hbar, MODEL.derivedFrom, CONSTANT.PlanckConstant) in graph

    hbar_2022 = CONSTANT["ReducedPlanckConstant/2022"]
    assert graph.value(hbar_2022, MODEL.adjustmentRole) == rdflib.Literal("computed_exact")
    assert graph.value(hbar_2022, MODEL.isComputed) == rdflib.Literal(True)
    assert graph.value(hbar_2022, MODEL.valueSource) == rdflib.Literal("computed")
    assert graph.value(hbar_2022, MODEL.nistValue) == rdflib.Literal("1.054571817e-34")
    assert graph.value(hbar_2022, MODEL.isNistTruncated) == rdflib.Literal(True)
    assert graph.value(hbar_2022, MODEL.isTruncated) == rdflib.Literal(True)
    assert graph.value(hbar_2022, MODEL.recommendedNumericType) == rdflib.Literal("decimal")
    assert graph.value(hbar_2022, MODEL.fitsFloat64) == rdflib.Literal(False)

    with localcontext() as ctx:
        ctx.prec = 100
        str_dec = Decimal(str(graph.value(hbar_2022, MODEL.value)))
        xsd_dec = Decimal(str(graph.value(hbar_2022, MODEL.valueDecimal)))
        assert str_dec == xsd_dec

    faraday_2022 = CONSTANT["FaradayConstant/2022"]
    assert graph.value(faraday_2022, MODEL.value) == rdflib.Literal(
        "96485.3321233100184", datatype=rdflib.XSD.string
    )
    assert graph.value(faraday_2022, MODEL.nistValue) == rdflib.Literal("96485.33212")
    assert graph.value(faraday_2022, MODEL.isNistTruncated) == rdflib.Literal(True)
    assert (faraday_2022, MODEL.isTruncated, None) not in graph


def test_distributed_rdf_model_completeness_and_datatypes(graph: rdflib.Graph):
    """Verify 1:1 ontology-to-data alignment, xsd:double datatypes, and complete YAML metadata emission."""
    ont = rdflib.Graph().parse(ONTOLOGY_PATH, format="turtle")
    model_ns = str(MODEL)

    # 1. Every codata: predicate used in data is declared in codata.ttl, and every declared property is used
    data_preds = {str(p) for _, p, _ in graph if str(p).startswith(model_ns)}
    ont_props = {
        str(s)
        for s in set(ont.subjects(RDF.type, OWL.ObjectProperty)) | set(ont.subjects(RDF.type, OWL.DatatypeProperty))
        if str(s).startswith(model_ns)
    }
    assert data_preds - ont_props == set(), f"Undeclared codata: predicates in data: {data_preds - ont_props}"
    assert ont_props - data_preds == set(), f"Unused codata: predicates in ontology: {ont_props - data_preds}"

    # 2. All valueFloat and uncertaintyFloat literals parse back strictly as xsd:double
    for pred in (MODEL.valueFloat, MODEL.uncertaintyFloat):
        objs = list(graph.objects(None, pred))
        assert len(objs) > 0
        bad = [o for o in objs if not (isinstance(o, rdflib.Literal) and o.datatype == rdflib.XSD.double)]
        assert not bad, f"Non-xsd:double literals found on {pred}: {bad[:5]}"

    # 3. isTruncated is emitted symmetrically (never false)
    assert (None, MODEL.isTruncated, rdflib.Literal(False)) not in graph

    # 4. Concept/Quantity flags, definitions, Constant isComputed, and Constant UCUM codes are present
    assert len(list(graph.subjects(MODEL.isRatio, rdflib.Literal(True)))) == 80
    assert len(list(graph.subjects(MODEL.isRelationship, rdflib.Literal(True)))) == 56
    assert len(list(graph.triples((None, SKOS.definition, None)))) >= 14
    hbar_val_2022 = CONSTANT["ReducedPlanckConstant/2022"]
    c_val_2022 = CONSTANT["SpeedOfLight/2022"]
    h_val_2014 = CONSTANT["PlanckConstant/2014"]
    h_val_2022 = CONSTANT["PlanckConstant/2022"]
    assert graph.value(hbar_val_2022, MODEL.isComputed) == rdflib.Literal(True)
    assert graph.value(c_val_2022, MODEL.isComputed) == rdflib.Literal(False)
    assert graph.value(h_val_2014, MODEL.adjustmentRole) == rdflib.Literal("adjusted")
    assert graph.value(h_val_2014, MODEL.isComputed) == rdflib.Literal(False)
    assert graph.value(h_val_2022, MODEL.adjustmentRole) == rdflib.Literal("defining")
    assert graph.value(h_val_2022, MODEL.isComputed) == rdflib.Literal(False)
    ucum_ns = rdflib.Namespace("https://w3id.org/uom/")
    assert graph.value(CONSTANT.SpeedOfLight, ucum_ns.ucum) == rdflib.Literal("[c]")
