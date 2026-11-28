"""Automated tests for the YAML-first CODATA DRUM pipeline, validation, reporting, and editor."""

from __future__ import annotations

import re
import shutil
from decimal import Decimal, localcontext
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from utils.dataset import DATA_DIR, ROOT_DIR, export_csv, export_json, load_dataset, save_dataset
from utils.editor import create_app
from utils.formulas import (
    evaluate_exact_formula,
    extract_dependencies,
    format_canonical_decimal,
    validate_formula_syntax,
)
from utils.models import (
    ConstantModel,
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
    assert report.stats["formulas_checked"] == 380
    assert report.stats["formulas_passed"] == 380
    assert report.stats["computed_exact_upgraded"] == 124
    assert report.stats["terminating_exact_recovered"] == 20
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
    assert val_2022.nist_exponent == -27


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
    # Symbols keep their case, also next to punctuation and hyphens (issue #10)
    assert default_constant_name_en("molar volume of ideal gas (273.15 K, 100 kPa)") == (
        "Molar Volume Of Ideal Gas (273.15 K, 100 kPa)"
    )
    assert default_constant_name_en("newtonian constant of gravitation over h-bar c") == (
        "Newtonian Constant Of Gravitation Over h-bar c"
    )
    assert default_constant_name_en("electron g factor") == "Electron g Factor"
    assert default_constant_name_en("proton mass in u") == "Proton Mass In u"
    assert default_constant_name_en("shielding difference of d and p in hd") == (
        "Shielding Difference Of d And p In HD"
    )
    assert default_constant_name_en("natural unit of momentum in MeV/c") == "Natural Unit Of Momentum In MeV/c"
    # Si (silicon) and SI (the system) are distinguished by case alone
    assert default_constant_name_en("lattice spacing of ideal Si (220)") == "Lattice Spacing Of Ideal Si (220)"
    assert default_constant_name_en("SI value") == "SI Value"
    # Already-correct symbols are kept, including ones that differ from a symbol only by case
    assert default_constant_name_en("charge in C, temperature 1 K") == "Charge In C, Temperature 1 K"
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

    # 5. Unsafe formula rejection and formula DAG cycle detection
    with pytest.raises(ValueError):
        validate_formula_syntax("__import__('os').system('ls')")
    with pytest.raises(ValidationError):
        ConstantModel(
            id="BadConst",
            quantity_id="PlanckConstant",
            name="Bad Const",
            formula="foo(bar)",
        )

    cycle_formula_ds = dataset.model_copy(deep=True)
    c_h = next(c for c in cycle_formula_ds.constants if c.id == "PlanckConstant")
    c_h.formula = "ReducedPlanckConstant * 2 * pi"
    rep_formula_cycle = validate_dataset(cycle_formula_ds, skip_nist=True)
    assert any(d.code == "FORMULA_CYCLE" and d.severity == "error" for d in rep_formula_cycle.diagnostics)


def test_derived_formula_tolerance_is_relative_standard_uncertainty():
    """A computed_derived value off by much more than u_r but less than 1e-7 must fail the formula check."""
    dataset = load_dataset(DATA_DIR)
    latest = dataset.latest_version_id()

    report = validate_dataset(dataset, skip_nist=True)
    assert not any(d.code == "FORMULA_MISMATCH" for d in report.diagnostics)

    # Bohr radius 2022: 5.29177210544(82)e-11, u_r ~ 1.6e-10. Change the 9th significant digit:
    # relative error ~ 8.4e-9, about 54 u_r but below the former fixed floor of 1e-7.
    mutated = dataset.model_copy(deep=True)
    bohr = next(c for c in mutated.constants if c.id == "BohrRadius")
    val = bohr.value_for_version(latest)
    assert val is not None and val.adjustment_role == "computed_derived"
    val.value = "5.29177215e-11"
    rep = validate_dataset(mutated, skip_nist=True)
    assert any(d.code == "FORMULA_MISMATCH" and d.entity_id == "BohrRadius" for d in rep.diagnostics)


def test_computable_precision_and_ieee754_sufficiency():
    """Verify determination roles, exact rational recovery, 34-digit precision, and IEEE 754 flags."""
    dataset = load_dataset(DATA_DIR)
    by_id = {c.id: c for c in dataset.constants}

    roles = [c.adjustment_role for c in dataset.constants]
    assert roles.count("defining") == 12
    assert roles.count("computed_exact") == 69
    assert roles.count("adjusted") == 32
    assert roles.count("computed_derived") == 242
    assert roles.count(None) == 4

    # Historical 2014 roles across SI regimes
    roles_2014 = [v.adjustment_role for c in dataset.constants if (v := c.value_for_version("2014"))]
    assert roles_2014.count("defining") == 9
    assert roles_2014.count("computed_exact") == 8
    assert roles_2014.count("adjusted") == 23
    assert roles_2014.count("computed_derived") == 295

    # Terminating exact rational recovery (FaradayConstant, A_90, W_90, MolarGasConstant)
    faraday = by_id["FaradayConstant"]
    assert faraday.formula == "AvogadroConstant * ElementaryCharge"
    assert faraday.derived_from == ["AvogadroConstant", "ElementaryCharge"]
    assert faraday.is_computed is True
    f22 = faraday.value_for_version("2022")
    assert f22 is not None
    assert f22.adjustment_role == "computed_exact"
    assert f22.is_computed is True
    assert f22.value == "96485.3321233100184"
    assert f22.value_nist == "96485.33212"
    assert f22.value_source == "computed"
    assert f22.is_nist_truncated is True
    assert f22.is_truncated is False
    assert f22.significant_digits == 18
    assert f22.fits_float64 is False

    # Historical FaradayConstant in 2014 was computed_derived with uncertainty
    f14 = faraday.value_for_version("2014")
    assert f14 is not None
    assert f14.adjustment_role == "computed_derived"
    assert f14.is_computed is True
    assert f14.is_exact is False
    assert f14.uncertainty is not None
    assert f22.recommended_numeric_type == "decimal"

    a90_22 = by_id["ConventionalValueOfAmpere90"].value_for_version("2022")
    assert a90_22 is not None
    assert a90_22.value == "1.00000008887143810491801"
    assert a90_22.is_nist_truncated is True
    assert a90_22.is_truncated is False
    assert a90_22.significant_digits == 24

    r22 = by_id["MolarGasConstant"].value_for_version("2022")
    assert r22 is not None
    assert r22.value == "8.31446261815324"
    assert r22.value_nist == "8.314462618"
    assert r22.is_truncated is False
    assert r22.significant_digits == 15
    assert r22.fits_float64 is True
    assert r22.recommended_numeric_type == "float64"

    # 34-digit IEEE 754 decimal128 upgrade on non-terminating exact constants
    hbar_22 = by_id["ReducedPlanckConstant"].value_for_version("2022")
    assert hbar_22 is not None
    assert hbar_22.value_source == "computed"
    assert hbar_22.value_nist == "1.054571817e-34"
    assert hbar_22.is_nist_truncated is True
    assert hbar_22.is_truncated is True
    # 34th digit is 0 and must be kept (h/2pi = 1.054571817646156391262428003302280744...e-34)
    assert hbar_22.value == "1.054571817646156391262428003302280e-34"
    assert hbar_22.significant_digits == 34
    assert hbar_22.fits_float64 is False
    assert hbar_22.recommended_numeric_type == "decimal"
    with localcontext() as ctx:
        ctx.prec = 100
        assert hbar_22.value.startswith("1.054571817")
        assert Decimal(hbar_22.value) > Decimal(hbar_22.value_nist)

    # IEEE 754 float32 vs float64 fit checks
    k22 = by_id["BoltzmannConstant"].value_for_version("2022")
    assert k22 is not None
    assert k22.significant_digits == 7
    assert k22.fits_float32 is True
    assert k22.recommended_numeric_type == "float32"

    h22 = by_id["PlanckConstant"].value_for_version("2022")
    assert h22 is not None
    assert h22.significant_digits == 9
    assert h22.fits_float32 is False
    assert h22.fits_float64 is True
    assert h22.recommended_numeric_type == "float64"

    # Direct formula engine unit sanity check
    assert extract_dependencies("2 * PlanckConstant / (ElementaryCharge * pi)") == [
        "ElementaryCharge",
        "PlanckConstant",
    ]
    res_str, is_trunc, _, _ = evaluate_exact_formula(
        "AvogadroConstant * BoltzmannConstant",
        {"AvogadroConstant": "6.02214076e23", "BoltzmannConstant": "1.380649e-23"},
    )
    assert res_str == "8.31446261815324"
    assert is_trunc is False


def test_truncated_values_keep_trailing_zeros():
    """A 34-digit truncation whose last digit is 0 keeps all 34 digits (no normalize())."""
    assert format_canonical_decimal(Decimal("1.054571817646156391262428003302280E-34"), keep_trailing_zeros=True) == (
        "1.054571817646156391262428003302280e-34"
    )
    assert format_canonical_decimal(Decimal("1836.152673400"), keep_trailing_zeros=True) == "1836.152673400"
    # Default (complete exact expansions): trailing zeros carry no information and are dropped
    assert format_canonical_decimal(Decimal("1836.152673400")) == "1836.1526734"
    assert format_canonical_decimal(Decimal("9192631770")) == "9192631770"

    res_str, is_trunc, _, _ = evaluate_exact_formula("PlanckConstant / (2 * pi)", {"PlanckConstant": "6.62607015e-34"})
    assert is_trunc is True
    assert res_str == "1.054571817646156391262428003302280e-34"

    dataset = load_dataset(DATA_DIR)
    for c in dataset.constants:
        for v in c.values:
            if v.value_source == "computed" and v.is_truncated:
                assert v.significant_digits == 34, (c.id, v.version, v.value)


def test_markdown_report_and_legacy_exports(tmp_path: Path):
    """Verify Markdown report generation and JSON/CSV export parity."""
    dataset = load_dataset(DATA_DIR)
    report = validate_dataset(dataset, nist_dir=ROOT_DIR / "nist")
    md = generate_markdown_report(dataset, report)

    assert "# CODATA DRUM Constants — Dataset & Validation Report" in md
    assert "| Physical Constants (Total) | 359 |" in md
    assert "| Measurement Units | 84 |" in md
    assert "## 3. Determination Role Breakdown (`2022`)" in md
    assert "## 4. Two-Source Precision Upgrades & IEEE 754 Storage Sufficiency" in md
    assert "96485.3321233100184" in md
    assert "10.1103/RevModPhys.97.025002" in md
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
    hbar_payload = next(c for c in payload["constants"] if c["id"] == "ReducedPlanckConstant")
    assert hbar_payload["adjustment_role"] == "computed_exact"
    assert hbar_payload["symbol_tex"] == r"\hbar"
    assert hbar_payload["derived_from"] == ["PlanckConstant"]
    assert hbar_payload["is_computed"] is True
    hbar_2022 = next(v for v in hbar_payload["values"] if v["version"] == "2022")
    assert hbar_2022["adjustment_role"] == "computed_exact"
    assert hbar_2022["is_computed"] is True
    assert hbar_2022["value_source"] == "computed"
    assert hbar_2022["value_nist"] == "1.054571817e-34"
    assert hbar_2022["is_nist_truncated"] is True
    assert hbar_2022["recommended_numeric_type"] == "decimal"

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


def _yaml_bytes(data_dir: Path) -> dict[str, bytes]:
    return {p.name: p.read_bytes() for p in sorted(data_dir.glob("*.yaml"))}


def _sync(*args: str):
    from typer.testing import CliRunner

    from utils.codata_constants import app

    return CliRunner().invoke(app, ["sync-nist", "--year", "2022", *args])


def test_sync_nist_keeps_adjustment_role(tmp_path: Path):
    """sync-nist must not drop curated fields (review item 1)."""
    data_copy = tmp_path / "data"
    shutil.copytree(DATA_DIR, data_copy)
    nist_dir = str(ROOT_DIR / "nist")

    dry = _sync("--data-dir", str(data_copy), "--nist-dir", nist_dir)
    assert dry.exit_code == 0, dry.output
    assert "355 unchanged, 0 updated" in dry.output

    applied = _sync("--apply", "--data-dir", str(data_copy), "--nist-dir", nist_dir)
    assert applied.exit_code == 0, applied.output
    assert _yaml_bytes(data_copy) == _yaml_bytes(DATA_DIR)


def test_sync_nist_persists_a_changed_value_and_keeps_its_role(tmp_path: Path):
    """A real NIST value change is saved; the curated adjustment_role and all other values are kept."""
    import json

    data_copy = tmp_path / "data"
    nist_copy = tmp_path / "nist"
    shutil.copytree(DATA_DIR, data_copy)
    shutil.copytree(ROOT_DIR / "nist" / "2022", nist_copy / "2022")
    nist_json = nist_copy / "2022" / "allascii_2022.json"
    rows = json.loads(nist_json.read_text(encoding="utf-8"))
    (row,) = [r for r in rows if r["nist_id"] == "gf"]
    assert row["str_value"] == "1.1663787e-5"
    row["str_value"] = "1.1663788e-5"  # one unit in the last digit, within u
    row["nist_value"] = "1.166 3788 e-5"
    row["numeric_value"] = 1.1663788e-5
    nist_json.write_text(json.dumps(rows, indent=4, ensure_ascii=False) + "\n", encoding="utf-8")

    result = _sync("--apply", "--data-dir", str(data_copy), "--nist-dir", str(nist_copy))
    assert result.exit_code == 0, result.output
    assert "354 unchanged, 1 updated" in result.output

    before, after = load_dataset(DATA_DIR), load_dataset(data_copy)
    before_by_id = {c.id: c for c in before.constants}
    old_val = before_by_id["FermiCouplingConstant"].value_for_version("2022")
    new_val = next(c for c in after.constants if c.id == "FermiCouplingConstant").value_for_version("2022")
    assert old_val is not None and new_val is not None
    assert new_val.value == "1.1663788e-5"
    assert new_val.adjustment_role == old_val.adjustment_role == "adjusted"
    assert new_val.model_dump(exclude={"value"}) == old_val.model_dump(exclude={"value"})
    changed = [
        (c.id, v.version)
        for c in after.constants
        for v in c.values
        if v != before_by_id[c.id].value_for_version(v.version)
    ]
    assert changed == [("FermiCouplingConstant", "2022")]
    assert validate_dataset(after, nist_dir=nist_copy).passed


def test_sync_nist_refuses_to_save_an_invalid_dataset(tmp_path: Path):
    """With --apply nothing is written when validation fails; --allow-missing-roles does not change that
    for errors other than missing roles of the synced release."""
    nist_dir = str(ROOT_DIR / "nist")
    cases = {
        # a 2018 value without role: not part of the 2022 sync, so never allowed
        "other_release_role": ("", ""),
        # a corrupted computed_exact 2022 value (FORMULA_MISMATCH)
        "formula_mismatch": (
            'value: "1.054571817646156391262428003302280e-34"',
            'value: "1.054571817646156391262428003302281e-34"',
        ),
    }
    for name, (old, new) in cases.items():
        data_copy = tmp_path / name
        shutil.copytree(DATA_DIR, data_copy)
        constants_yaml = data_copy / "constants.yaml"
        text = constants_yaml.read_text(encoding="utf-8")
        if name == "other_release_role":
            # first role line of a 2018 value
            start = text.index('    - version: "2018"\n')
            end = text.index("    - version:", start + 1)
            role = re.search(r"      adjustment_role: \w+\n", text[start:end])
            assert role is not None
            text = text[: start + role.start()] + text[start + role.end() :]
        else:
            if old not in text:  # before the trailing-zero fix the value had 33 digits
                old, new = (
                    'value: "1.05457181764615639126242800330228e-34"',
                    'value: "1.05457181764615639126242800330229e-34"',
                )
            text = text.replace(old, new, 1)
        constants_yaml.write_text(text, encoding="utf-8")
        before = _yaml_bytes(data_copy)

        for extra in ([], ["--allow-missing-roles"]):
            result = _sync("--apply", *extra, "--data-dir", str(data_copy), "--nist-dir", nist_dir)
            assert result.exit_code == 1, (name, extra, result.output)
            assert "nothing saved" in result.output
            assert {"other_release_role": "MISSING_ADJUSTMENT_ROLE", "formula_mismatch": "FORMULA_MISMATCH"}[
                name
            ] in result.output
            assert _yaml_bytes(data_copy) == before, (name, extra)


def test_sync_nist_new_release_needs_allow_missing_roles(tmp_path: Path):
    """Importing a release that is not in the dataset yet: its values have no roles. That is refused
    by default and saved with --allow-missing-roles."""
    data_copy = tmp_path / "data"
    shutil.copytree(DATA_DIR, data_copy)
    ds = load_dataset(data_copy)
    for c in ds.constants:
        c.values = [v for v in c.values if v.version != "2022"]
    ds.versions = [v for v in ds.versions if v.id != "2022"]
    save_dataset(ds, data_copy)
    before = _yaml_bytes(data_copy)
    args = ["--apply", "--published", "2024-05-30", "--data-dir", str(data_copy), "--nist-dir", str(ROOT_DIR / "nist")]

    refused = _sync(*args)
    assert refused.exit_code == 1, refused.output
    assert "MISSING_ADJUSTMENT_ROLE" in refused.output
    assert "--allow-missing-roles" in refused.output
    assert _yaml_bytes(data_copy) == before

    saved = _sync(*args, "--allow-missing-roles")
    assert saved.exit_code == 0, saved.output
    after = load_dataset(data_copy)
    new_values = [v for c in after.constants for v in c.values if v.version == "2022"]
    assert len(new_values) == 355
    assert all(v.adjustment_role is None for v in new_values)
    assert "2022" in {v.id for v in after.versions}
