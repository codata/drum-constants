"""Four-layer validation engine and CLI for CODATA DRUM YAML datasets."""

from __future__ import annotations

import json
import re
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Literal

import typer
from pydantic import BaseModel, Field, computed_field

from utils.dataset import DATA_DIR, ROOT_DIR, load_dataset
from utils.models import DatasetModel

app = typer.Typer(help="Validate CODATA DRUM YAML dataset integrity and NIST alignment.")

_BAD_SI_TOKENS = {"Mev", "Ev", "Kpa", "Gev", "Mhz", "Fm"}
_WORD_RE = re.compile(r"\b[A-Za-z]+\b")


class Diagnostic(BaseModel):
    """Single validation diagnostic emitted by one of the four validation layers."""

    layer: int
    severity: Literal["error", "warning"]
    entity_type: str
    entity_id: str
    code: str
    message: str


class IdentityCheck(BaseModel):
    """Result of a fundamental physical constant metrological identity check."""

    name: str
    formula: str
    expected: float
    computed: float
    rel_error: float
    tolerance: float
    passed: bool


class ValidationReport(BaseModel):
    """Aggregated multi-layer validation report."""

    diagnostics: list[Diagnostic] = Field(default_factory=list)
    identity_checks: list[IdentityCheck] = Field(default_factory=list)
    stats: dict[str, Any] = Field(default_factory=dict)

    @computed_field
    @property
    def error_count(self) -> int:
        return sum(1 for d in self.diagnostics if d.severity == "error")

    @computed_field
    @property
    def warning_count(self) -> int:
        return sum(1 for d in self.diagnostics if d.severity == "warning")

    @computed_field
    @property
    def passed(self) -> bool:
        return self.error_count == 0


def _find_cycles(adjacency: dict[str, list[str]]) -> list[list[str]]:
    visited: set[str] = set()
    stack: set[str] = set()
    cycles: list[list[str]] = []

    def dfs(node: str, path: list[str]) -> None:
        visited.add(node)
        stack.add(node)
        for nxt in adjacency.get(node, []):
            if nxt in stack:
                idx = path.index(nxt)
                cycles.append([*path[idx:], nxt])
            elif nxt not in visited and nxt in adjacency:
                dfs(nxt, [*path, nxt])
        stack.remove(node)

    for start in sorted(adjacency):
        if start not in visited:
            dfs(start, [start])
    return cycles


def _validate_layer1_schema_and_precision(dataset: DatasetModel, diags: list[Diagnostic]) -> None:
    for const in dataset.constants:
        if not const.values:
            diags.append(
                Diagnostic(
                    layer=1,
                    severity="error",
                    entity_type="Constant",
                    entity_id=const.id,
                    code="EMPTY_VALUES",
                    message="Constant has no versioned values",
                )
            )
        seen_versions: set[str] = set()
        for val in const.values:
            if val.version in seen_versions:
                diags.append(
                    Diagnostic(
                        layer=1,
                        severity="error",
                        entity_type="Constant",
                        entity_id=const.id,
                        code="DUPLICATE_VERSION_VALUE",
                        message=f"Duplicate ConstantValue for version {val.version}",
                    )
                )
            seen_versions.add(val.version)
            try:
                dec = Decimal(val.value)
                if not dec.is_finite():
                    raise InvalidOperation("non-finite")
            except InvalidOperation:
                diags.append(
                    Diagnostic(
                        layer=1,
                        severity="error",
                        entity_type="Constant",
                        entity_id=const.id,
                        code="INVALID_DECIMAL_VALUE",
                        message=f"Version {val.version} value {val.value!r} is not a valid decimal",
                    )
                )
            if val.is_exact and val.uncertainty is not None:
                diags.append(
                    Diagnostic(
                        layer=1,
                        severity="error",
                        entity_type="Constant",
                        entity_id=const.id,
                        code="EXACT_WITH_UNCERTAINTY",
                        message=f"Version {val.version} marked exact but has uncertainty {val.uncertainty!r}",
                    )
                )
            if not val.is_exact and val.uncertainty is None:
                diags.append(
                    Diagnostic(
                        layer=1,
                        severity="error",
                        entity_type="Constant",
                        entity_id=const.id,
                        code="MISSING_UNCERTAINTY",
                        message=f"Version {val.version} not marked exact but has no uncertainty",
                    )
                )


def _check_unique_ids(items: list[Any], entity_type: str, diags: list[Diagnostic]) -> dict[str, Any]:
    by_id: dict[str, Any] = {}
    for item in items:
        if item.id in by_id:
            diags.append(
                Diagnostic(
                    layer=2,
                    severity="error",
                    entity_type=entity_type,
                    entity_id=item.id,
                    code="DUPLICATE_ID",
                    message=f"Duplicate {entity_type} id {item.id!r}",
                )
            )
        by_id[item.id] = item
    return by_id


def _validate_layer2_integrity(dataset: DatasetModel, diags: list[Diagnostic]) -> None:
    versions_by_id = _check_unique_ids(dataset.versions, "Version", diags)
    units_by_id = _check_unique_ids(dataset.units, "Unit", diags)
    concepts_by_id = _check_unique_ids(dataset.concepts, "Concept", diags)
    quantities_by_id = _check_unique_ids(dataset.quantities, "Quantity", diags)
    _check_unique_ids(dataset.constants, "Constant", diags)

    seen_nist: dict[str, str] = {}
    for const in dataset.constants:
        nist_id = const.ids.get("NIST")
        if not nist_id:
            diags.append(
                Diagnostic(
                    layer=2,
                    severity="error",
                    entity_type="Constant",
                    entity_id=const.id,
                    code="MISSING_NIST_ID",
                    message="Constant is missing ids.NIST",
                )
            )
        elif nist_id in seen_nist:
            diags.append(
                Diagnostic(
                    layer=2,
                    severity="error",
                    entity_type="Constant",
                    entity_id=const.id,
                    code="DUPLICATE_NIST_ID",
                    message=f"ids.NIST {nist_id!r} also used by {seen_nist[nist_id]}",
                )
            )
        else:
            seen_nist[nist_id] = const.id

        if const.quantity_id not in quantities_by_id:
            diags.append(
                Diagnostic(
                    layer=2,
                    severity="error",
                    entity_type="Constant",
                    entity_id=const.id,
                    code="UNKNOWN_QUANTITY_REF",
                    message=f"quantity_id {const.quantity_id!r} not found in quantities.yaml",
                )
            )
        if const.unit_id and const.unit_id not in units_by_id:
            diags.append(
                Diagnostic(
                    layer=2,
                    severity="error",
                    entity_type="Constant",
                    entity_id=const.id,
                    code="UNKNOWN_UNIT_REF",
                    message=f"unit_id {const.unit_id!r} not found in units.yaml",
                )
            )
        for val in const.values:
            if val.version not in versions_by_id:
                diags.append(
                    Diagnostic(
                        layer=2,
                        severity="error",
                        entity_type="Constant",
                        entity_id=const.id,
                        code="UNKNOWN_VERSION_REF",
                        message=f"ConstantValue version {val.version!r} not found in versions.yaml",
                    )
                )

    referenced_concepts: set[str] = set()
    for qty in dataset.quantities:
        referenced_concepts.add(qty.id)
        concept = concepts_by_id.get(qty.id)
        if concept is None:
            diags.append(
                Diagnostic(
                    layer=2,
                    severity="error",
                    entity_type="Quantity",
                    entity_id=qty.id,
                    code="QUANTITY_MISSING_CONCEPT",
                    message="Quantity has no matching entry in concepts.yaml",
                )
            )
        elif concept.name != qty.name:
            diags.append(
                Diagnostic(
                    layer=2,
                    severity="warning",
                    entity_type="Quantity",
                    entity_id=qty.id,
                    code="QUANTITY_CONCEPT_NAME_MISMATCH",
                    message=f"Quantity name {qty.name!r} differs from Concept name {concept.name!r}",
                )
            )
        for ref in [*qty.has_parts, *qty.same_as]:
            referenced_concepts.add(ref)
            if ref not in concepts_by_id:
                diags.append(
                    Diagnostic(
                        layer=2,
                        severity="error",
                        entity_type="Quantity",
                        entity_id=qty.id,
                        code="UNKNOWN_CONCEPT_REF",
                        message=f"Referenced concept {ref!r} not found in concepts.yaml",
                    )
                )

    broader_adj: dict[str, list[str]] = {}
    parts_adj: dict[str, list[str]] = {}
    for concept in dataset.concepts:
        broader_adj[concept.id] = list(concept.broader)
        parts_adj[concept.id] = list(concept.parts)
        for rel_name, refs in (
            ("broader", concept.broader),
            ("parts", concept.parts),
            ("related", concept.related),
            ("same_as", concept.same_as),
        ):
            for ref in refs:
                referenced_concepts.add(ref)
                if ref not in concepts_by_id:
                    diags.append(
                        Diagnostic(
                            layer=2,
                            severity="error",
                            entity_type="Concept",
                            entity_id=concept.id,
                            code="UNKNOWN_CONCEPT_REF",
                            message=f"{rel_name} reference {ref!r} not found in concepts.yaml",
                        )
                    )

    for cycle in _find_cycles(broader_adj):
        diags.append(
            Diagnostic(
                layer=2,
                severity="error",
                entity_type="Concept",
                entity_id=cycle[0],
                code="CONCEPT_BROADER_CYCLE",
                message=f"Cycle detected in skos:broader: {' -> '.join(cycle)}",
            )
        )
    for cycle in _find_cycles(parts_adj):
        diags.append(
            Diagnostic(
                layer=2,
                severity="error",
                entity_type="Concept",
                entity_id=cycle[0],
                code="CONCEPT_PARTS_CYCLE",
                message=f"Cycle detected in dcterms:hasPart: {' -> '.join(cycle)}",
            )
        )

    unit_counts = dataset.unit_constant_counts()
    for uid, count in sorted(unit_counts.items()):
        if count == 0:
            diags.append(
                Diagnostic(
                    layer=2,
                    severity="warning",
                    entity_type="Unit",
                    entity_id=uid,
                    code="ORPHAN_UNIT",
                    message="Unit is not referenced by any constant",
                )
            )

    for concept in dataset.concepts:
        if concept.id not in referenced_concepts and not concept.broader and not concept.parts:
            diags.append(
                Diagnostic(
                    layer=2,
                    severity="warning",
                    entity_type="Concept",
                    entity_id=concept.id,
                    code="ORPHAN_CONCEPT",
                    message="Concept is neither a Quantity nor linked in concept relationships",
                )
            )


def _validate_layer3_hygiene(dataset: DatasetModel, diags: list[Diagnostic]) -> None:
    for const in dataset.constants:
        words = set(_WORD_RE.findall(const.name))
        bad_overlap = sorted(words.intersection(_BAD_SI_TOKENS))
        if bad_overlap:
            diags.append(
                Diagnostic(
                    layer=3,
                    severity="error",
                    entity_type="Constant",
                    entity_id=const.id,
                    code="BAD_SI_CASING",
                    message=f"Bad SI symbol casing {bad_overlap} in Constant.name {const.name!r}",
                )
            )
        if "Momentum" in const.id and "Momentum" not in const.name:
            diags.append(
                Diagnostic(
                    layer=3,
                    severity="error",
                    entity_type="Constant",
                    entity_id=const.id,
                    code="TRUNCATED_MOMENTUM",
                    message=f"Momentum constant has truncated label {const.name!r}",
                )
            )
        if not const.name_fr:
            diags.append(
                Diagnostic(
                    layer=3,
                    severity="warning",
                    entity_type="Constant",
                    entity_id=const.id,
                    code="MISSING_FRENCH_LABEL",
                    message="Constant is missing name_fr",
                )
            )
        if not const.name_bipm_en or not const.name_bipm_fr:
            diags.append(
                Diagnostic(
                    layer=3,
                    severity="warning",
                    entity_type="Constant",
                    entity_id=const.id,
                    code="MISSING_BIPM_LABEL",
                    message="Constant is missing BIPM altLabel (name_bipm_en or name_bipm_fr)",
                )
            )

    for unit in dataset.units:
        if "XC" in unit.id:
            continue
        if not unit.ids.get("UCUM"):
            diags.append(
                Diagnostic(
                    layer=3,
                    severity="error",
                    entity_type="Unit",
                    entity_id=unit.id,
                    code="MISSING_UCUM_ID",
                    message="Non-conventional SI unit missing ids.UCUM",
                )
            )
        if not unit.si_expression:
            diags.append(
                Diagnostic(
                    layer=3,
                    severity="error",
                    entity_type="Unit",
                    entity_id=unit.id,
                    code="MISSING_SI_EXPRESSION",
                    message="Non-conventional SI unit missing si_expression",
                )
            )


def _validate_layer4_nist_and_identities(
    dataset: DatasetModel,
    nist_dir: Path | None,
    diags: list[Diagnostic],
    identity_checks: list[IdentityCheck],
) -> dict[str, Any]:
    nist_checked_values = 0
    nist_versions_checked: list[str] = []

    if nist_dir is not None:
        const_by_nist = {c.ids["NIST"]: c for c in dataset.constants if c.ids.get("NIST")}
        for ver in sorted(dataset.versions, key=lambda v: v.id, reverse=True):
            nist_json_path = nist_dir / ver.id / f"allascii_{ver.id}.json"
            if not nist_json_path.exists():
                continue
            nist_versions_checked.append(ver.id)
            with open(nist_json_path, encoding="utf-8") as handle:
                nist_rows = json.load(handle)
            nist_by_id = {row["nist_id"]: row for row in nist_rows if row.get("nist_id")}

            for nist_id, nrow in nist_by_id.items():
                const = const_by_nist.get(nist_id)
                if const is None:
                    diags.append(
                        Diagnostic(
                            layer=4,
                            severity="error",
                            entity_type="Constant",
                            entity_id=nist_id,
                            code="NIST_MISSING_CONSTANT",
                            message=f"NIST {ver.id} id {nist_id!r} ({nrow.get('quantity')!r}) not found in constants.yaml",
                        )
                    )
                    continue
                cval = const.value_for_version(ver.id)
                if cval is None:
                    diags.append(
                        Diagnostic(
                            layer=4,
                            severity="error",
                            entity_type="Constant",
                            entity_id=const.id,
                            code="NIST_MISSING_VERSION_VALUE",
                            message=f"Missing {ver.id} value for NIST id {nist_id!r}",
                        )
                    )
                    continue
                nist_checked_values += 1
                expected_val = nrow["str_value"]
                expected_exact = bool(nrow["is_exact"])
                expected_unc = None if expected_exact else nrow["str_uncertainty"]
                expected_trunc = bool(nrow["is_truncated"])
                expected_exp_raw = nrow.get("exponent")
                expected_exp = int(expected_exp_raw[1:]) if expected_exp_raw else None

                mismatches: list[str] = []
                if cval.value != expected_val:
                    mismatches.append(f"value {cval.value!r} != {expected_val!r}")
                if cval.uncertainty != expected_unc:
                    mismatches.append(f"uncertainty {cval.uncertainty!r} != {expected_unc!r}")
                if cval.is_exact != expected_exact:
                    mismatches.append(f"is_exact {cval.is_exact} != {expected_exact}")
                if cval.is_truncated != expected_trunc:
                    mismatches.append(f"is_truncated {cval.is_truncated} != {expected_trunc}")
                if cval.exponent != expected_exp:
                    mismatches.append(f"exponent {cval.exponent!r} != {expected_exp!r}")
                if mismatches:
                    diags.append(
                        Diagnostic(
                            layer=4,
                            severity="error",
                            entity_type="Constant",
                            entity_id=const.id,
                            code="NIST_MISMATCH",
                            message=f"NIST {ver.id} mismatch ({nist_id}): {'; '.join(mismatches)}",
                        )
                    )

    # Metrological identities on latest version
    latest = dataset.latest_version_id()
    const_map = {c.id: c for c in dataset.constants}

    def _get_latest_float(const_id: str) -> float | None:
        const = const_map.get(const_id)
        if not const:
            return None
        val = const.value_for_version(latest)
        return float(val.value) if val else None

    c = _get_latest_float("SpeedOfLight")
    h = _get_latest_float("PlanckConstant")
    e = _get_latest_float("ElementaryCharge")
    k = _get_latest_float("BoltzmannConstant")
    n_a = _get_latest_float("AvogadroConstant")
    r_gas = _get_latest_float("MolarGasConstant")
    faraday = _get_latest_float("FaradayConstant")
    alpha = _get_latest_float("FineStructureConstant")
    m_e = _get_latest_float("ElectronMass")
    rydberg = _get_latest_float("RydbergConstant")
    hartree = _get_latest_float("HartreeEnergy")

    checks_spec: list[tuple[str, str, float | None, float | None, float]] = [
        ("Speed of Light (exact)", "c == 299792458", c, 299792458.0, 1e-15),
        ("Planck Constant (exact)", "h == 6.62607015e-34", h, 6.62607015e-34, 1e-15),
        ("Elementary Charge (exact)", "e == 1.602176634e-19", e, 1.602176634e-19, 1e-15),
        ("Boltzmann Constant (exact)", "k == 1.380649e-23", k, 1.380649e-23, 1e-15),
        ("Avogadro Constant (exact)", "N_A == 6.02214076e23", n_a, 6.02214076e23, 1e-15),
        (
            "Molar Gas Constant",
            "R = k * N_A",
            r_gas,
            (k * n_a) if (k is not None and n_a is not None) else None,
            1e-9,
        ),
        (
            "Faraday Constant",
            "F = N_A * e",
            faraday,
            (n_a * e) if (n_a is not None and e is not None) else None,
            1e-9,
        ),
        (
            "Hartree Energy (Rydberg)",
            "E_h = 2 * R_inf * h * c",
            hartree,
            (2.0 * rydberg * h * c) if (rydberg is not None and h is not None and c is not None) else None,
            1e-9,
        ),
        (
            "Hartree Energy (Fine Structure)",
            "E_h = alpha^2 * m_e * c^2",
            hartree,
            ((alpha**2) * m_e * (c**2)) if (alpha is not None and m_e is not None and c is not None) else None,
            1e-9,
        ),
    ]

    for name, formula, expected, computed, tol in checks_spec:
        if expected is None or computed is None:
            diags.append(
                Diagnostic(
                    layer=4,
                    severity="error",
                    entity_type="Dataset",
                    entity_id=latest,
                    code="METROLOGICAL_IDENTITY_MISSING",
                    message=f"Cannot evaluate {name} ({formula}): missing constant value in {latest}",
                )
            )
            continue
        rel_err = abs(expected - computed) / abs(expected) if expected != 0 else abs(expected - computed)
        passed = rel_err <= tol
        identity_checks.append(
            IdentityCheck(
                name=name,
                formula=formula,
                expected=expected,
                computed=computed,
                rel_error=rel_err,
                tolerance=tol,
                passed=passed,
            )
        )
        if not passed:
            diags.append(
                Diagnostic(
                    layer=4,
                    severity="error",
                    entity_type="Dataset",
                    entity_id=latest,
                    code="METROLOGICAL_IDENTITY_FAILED",
                    message=f"{name} ({formula}) failed: rel_error={rel_err:.3e} > tol={tol:.1e}",
                )
            )

    return {
        "nist_versions_checked": nist_versions_checked,
        "nist_checked_values": nist_checked_values,
    }


def validate_dataset(
    dataset: DatasetModel,
    *,
    nist_dir: Path | None = ROOT_DIR / "nist",
    skip_nist: bool = False,
) -> ValidationReport:
    """Run all four validation layers against a loaded DatasetModel."""
    diagnostics: list[Diagnostic] = []
    identity_checks: list[IdentityCheck] = []

    _validate_layer1_schema_and_precision(dataset, diagnostics)
    _validate_layer2_integrity(dataset, diagnostics)
    _validate_layer3_hygiene(dataset, diagnostics)
    layer4_stats = _validate_layer4_nist_and_identities(
        dataset,
        None if skip_nist else nist_dir,
        diagnostics,
        identity_checks,
    )

    deprecated = dataset.deprecated_ids()
    stats: dict[str, Any] = {
        "latest_version": dataset.latest_version_id(),
        "versions": len(dataset.versions),
        "units": len(dataset.units),
        "concepts": len(dataset.concepts),
        "quantities": len(dataset.quantities),
        "constants": len(dataset.constants),
        "active_constants": len(dataset.constants) - len(deprecated),
        "deprecated_constants": len(deprecated),
        "constant_values": sum(len(c.values) for c in dataset.constants),
        **layer4_stats,
    }

    return ValidationReport(
        diagnostics=diagnostics,
        identity_checks=identity_checks,
        stats=stats,
    )


@app.command()
def main(
    data_dir: Path = typer.Option(DATA_DIR, "--data-dir", help="Path to data/ YAML directory"),
    nist_dir: Path = typer.Option(ROOT_DIR / "nist", "--nist-dir", help="Path to nist/ directory"),
    strict: bool = typer.Option(False, "--strict", help="Treat warnings as failures"),
    as_json: bool = typer.Option(False, "--json", help="Emit validation report as JSON"),
    skip_nist: bool = typer.Option(False, "--skip-nist", help="Skip Layer 4 NIST JSON cross-check"),
) -> None:
    """Validate CODATA YAML dataset across schema, integrity, hygiene, and NIST alignment."""
    dataset = load_dataset(data_dir)
    report = validate_dataset(dataset, nist_dir=nist_dir, skip_nist=skip_nist)

    if as_json:
        typer.echo(report.model_dump_json(indent=2))
    else:
        status = "PASS" if report.passed else "FAIL"
        typer.echo(
            f"Validation {status}: {report.error_count} errors, {report.warning_count} warnings "
            f"({report.stats['constants']} constants, {report.stats['constant_values']} values, "
            f"{report.stats['nist_checked_values']} NIST values verified)"
        )
        for diag in report.diagnostics:
            typer.echo(
                f"  [L{diag.layer} {diag.severity.upper()}] {diag.entity_type}:{diag.entity_id} "
                f"({diag.code}) - {diag.message}"
            )

    if not report.passed or (strict and report.warning_count > 0):
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
