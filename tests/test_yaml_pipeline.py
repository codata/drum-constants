"""Automated tests for the YAML-first CODATA DRUM pipeline, validation, reporting, and editor."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from utils.dataset import DATA_DIR, ROOT_DIR, export_csv, export_json, load_dataset, save_dataset
from utils.editor import create_app
from utils.models import (
    ConstantValueModel,
    default_constant_name_en,
    default_constant_name_fr,
    default_si_expression,
    default_unit_id,
)
from utils.report import generate_markdown_report
from utils.validate import validate_dataset


def test_load_yaml_dataset_counts():
    """Verify migrated YAML files load cleanly with expected entity counts."""
    dataset = load_dataset(DATA_DIR)
    assert len(dataset.versions) == 7
    assert len(dataset.units) == 84
    assert len(dataset.concepts) == 442
    assert len(dataset.quantities) == 306
    assert len(dataset.constants) == 359
    assert sum(len(c.values) for c in dataset.constants) == 2313


def test_full_four_layer_validation():
    """Verify full 4-layer validation passes with 0 errors and verifies all 2313 NIST values."""
    dataset = load_dataset(DATA_DIR)
    report = validate_dataset(dataset, nist_dir=ROOT_DIR / "nist")
    assert report.passed, f"Validation errors: {[d for d in report.diagnostics if d.severity == 'error']}"
    assert report.error_count == 0
    assert report.stats["nist_checked_values"] == 2313
    assert len(report.identity_checks) == 9
    assert all(chk.passed for chk in report.identity_checks)


def test_yaml_round_trip_precision_and_quoting(tmp_path: Path):
    """Verify saving and reloading YAML preserves trailing zeros and string scalar types."""
    original = load_dataset(DATA_DIR)
    save_dataset(original, tmp_path)

    constants_yaml = (tmp_path / "constants.yaml").read_text(encoding="utf-8")
    assert '"6.6446573450e-27"' in constants_yaml
    assert 'version: "2022"' in constants_yaml

    reloaded = load_dataset(tmp_path)
    assert reloaded == original

    alpha = next(c for c in reloaded.constants if c.id == "AlphaParticleMass")
    val_2022 = alpha.value_for_version("2022")
    assert val_2022 is not None
    assert val_2022.value == "6.6446573450e-27"
    assert val_2022.uncertainty == "0.0000000021e-27"
    assert val_2022.exponent == -27


def test_computed_fields_and_category_b_helpers():
    """Verify dynamically computed Category A fields and Category B formula helpers."""
    dataset = load_dataset(DATA_DIR)

    q_ids = dataset.quantity_ids()
    assert "AlphaParticleMass" in q_ids
    assert "AlphaParticle" not in q_ids

    qty_counts = dataset.quantity_constant_counts()
    assert qty_counts["AlphaParticleMass"] == 2

    unit_counts = dataset.unit_constant_counts()
    assert unit_counts["kg"] > 0
    assert unit_counts["Hz_V-1"] == 1

    c_speed = next(c for c in dataset.constants if c.id == "SpeedOfLight")
    assert c_speed.is_base is True
    assert c_speed.version_count == 7
    assert c_speed.is_qudt is True

    u_j = next(u for u in dataset.units if u.id == "J_s")
    assert u_j.si_uri == "https://si-digital-framework.org/SI/units/joule.second"
    assert u_j.ucum_uri == "https://w3id.org/uom/J.s"

    assert default_constant_name_en("alpha particle mass energy equivalent in MeV") == (
        "Alpha Particle Mass Energy Equivalent In MeV"
    )
    assert default_constant_name_en("shielded proton gyromagnetic ratio in MHz/T") == (
        "Shielded Proton Gyromagnetic Ratio In MHz/T"
    )
    assert default_constant_name_fr("masse de la particule alpha") == "Masse de la particule alpha"
    assert default_unit_id("kg mol^-1") == "kg_mol-1"
    assert default_si_expression("kg_mol-1") == "kg.mol-1"


def test_negative_validation_cases():
    """Verify validation rejects broken FKs, taxonomy cycles, exactness violations, and bad SI casing."""
    with pytest.raises(ValidationError):
        ConstantValueModel(
            version="2022",
            name="test",
            value="1.0",
            uncertainty="0.1",
            is_exact=True,
        )

    dataset = load_dataset(DATA_DIR)

    # 1. Broken quantity_id FK
    broken_fk = dataset.model_copy(deep=True)
    broken_fk.constants[0].quantity_id = "NonExistentQuantity"
    rep_fk = validate_dataset(broken_fk, skip_nist=True)
    assert not rep_fk.passed
    assert (
        any(d.code == "UNKNOWN_QUANTITY_REF" for d in rep_fk.errors)
        if hasattr(rep_fk, "errors")
        else any(d.code == "UNKNOWN_QUANTITY_REF" and d.severity == "error" for d in rep_fk.diagnostics)
    )

    # 2. Cycle in Concept.broader
    cycle_ds = dataset.model_copy(deep=True)
    c_a = next(c for c in cycle_ds.concepts if c.id == "Particle")
    c_b = next(c for c in cycle_ds.concepts if c.id == "AlphaParticle")
    c_a.broader = ["AlphaParticle"]
    assert "Particle" in c_b.broader
    rep_cycle = validate_dataset(cycle_ds, skip_nist=True)
    assert any(d.code == "CONCEPT_BROADER_CYCLE" and d.severity == "error" for d in rep_cycle.diagnostics)

    # 3. Bad SI casing
    casing_ds = dataset.model_copy(deep=True)
    casing_ds.constants[0].name = "Alpha Particle Energy In Mev"
    rep_casing = validate_dataset(casing_ds, skip_nist=True)
    assert any(d.code == "BAD_SI_CASING" and d.severity == "error" for d in rep_casing.diagnostics)

    # 4. Exactness invariant via model_construct
    exact_ds = dataset.model_copy(deep=True)
    bad_val = ConstantValueModel.model_construct(
        version="2022",
        name="bad",
        value="1.0",
        uncertainty="0.1",
        is_exact=True,
        is_truncated=False,
    )
    exact_ds.constants[0].values = [bad_val]
    rep_exact = validate_dataset(exact_ds, skip_nist=True)
    assert any(d.code == "EXACT_WITH_UNCERTAINTY" and d.severity == "error" for d in rep_exact.diagnostics)


def test_markdown_report_and_legacy_exports(tmp_path: Path):
    """Verify Markdown report generation and JSON/CSV export parity."""
    dataset = load_dataset(DATA_DIR)
    report = validate_dataset(dataset, nist_dir=ROOT_DIR / "nist")
    md = generate_markdown_report(dataset, report)

    assert "# CODATA DRUM Constants — Dataset & Validation Report" in md
    assert "| Physical Constants (Total) | 359 |" in md
    assert "| Measurement Units | 84 |" in md
    assert "FaradayConstantConventionalElectricCurrent" in md
    assert "Molar Gas Constant" in md

    json_out = export_json(dataset, tmp_path / "codata_constants.json")
    csv_files = export_csv(dataset, tmp_path / "csv")
    assert json_out.exists()
    assert len(csv_files) == 12  # 5 entity tables + 7 version tables (no nist_names_ids.csv)


def test_fastapi_editor_endpoints(tmp_path: Path):
    """Verify FastAPI editor endpoints against an isolated temporary data directory."""
    temp_data = tmp_path / "data"
    shutil.copytree(DATA_DIR, temp_data)

    api = create_app(
        data_dir=temp_data,
        nist_dir=ROOT_DIR / "nist",
        json_path=tmp_path / "codata.json",
        csv_dir=tmp_path / "csv",
        rdf_dir=tmp_path / "rdf",
        report_path=tmp_path / "REPORT.md",
    )
    client = TestClient(api)

    # Serve HTML UI
    r_root = client.get("/")
    assert r_root.status_code == 200
    assert "CODATA DRUM YAML Editor" in r_root.text

    # Serve favicon assets without 404
    r_fav = client.get("/favicon.ico")
    assert r_fav.status_code == 200
    assert r_fav.headers["content-type"] in {"image/x-icon", "image/vnd.microsoft.icon"}

    r_fav_svg = client.get("/favicon.svg")
    assert r_fav_svg.status_code == 200
    assert "image/svg+xml" in r_fav_svg.headers["content-type"]

    # Health check
    r_health = client.get("/api/health")
    assert r_health.status_code == 200
    assert r_health.json()["mode"] == "server"

    # Load dataset
    r_ds = client.get("/api/dataset")
    assert r_ds.status_code == 200
    payload = r_ds.json()
    assert len(payload["constants"]) == 359
    assert payload["computed"]["latest_version"] == "2022"

    # Validate endpoint
    r_val = client.post("/api/validate")
    assert r_val.status_code == 200
    val_json = r_val.json()
    assert val_json["passed"] is True
    assert val_json["error_count"] == 0
    assert "markdown_report" in val_json

    # Reject invalid FK save with 422
    bad_payload = dict(payload)
    bad_payload.pop("computed", None)
    bad_payload["constants"] = [dict(c) for c in payload["constants"]]
    bad_payload["constants"][0]["quantity_id"] = "InvalidQuantityID"
    r_bad = client.put("/api/dataset", json=bad_payload)
    assert r_bad.status_code == 422
    assert any(d["code"] == "UNKNOWN_QUANTITY_REF" for d in r_bad.json()["diagnostics"])

    # Valid save persists cleanly
    good_payload = dict(payload)
    good_payload.pop("computed", None)
    good_payload["versions"] = [dict(v) for v in payload["versions"]]
    good_payload["versions"][0]["description"] = "CODATA 2022 adjustment"
    r_good = client.put("/api/dataset", json=good_payload)
    assert r_good.status_code == 200
    assert r_good.json()["status"] == "saved"
    assert load_dataset(temp_data).versions[0].description == "CODATA 2022 adjustment"
