"""Automated Markdown dataset and validation report generator for CODATA DRUM."""

from __future__ import annotations

from pathlib import Path

import typer

from utils.dataset import DATA_DIR, ROOT_DIR, load_dataset
from utils.models import DatasetModel
from utils.validate import ValidationReport, validate_dataset

app = typer.Typer(help="Generate Markdown summary and validation report for the CODATA YAML dataset.")


def _progress_bar(count: int, total: int, width: int = 12) -> str:
    if total <= 0:
        return "`" + ("░" * width) + "`"
    filled = round((count / total) * width)
    return "`" + ("█" * filled) + ("░" * (width - filled)) + "`"


def _pct(count: int, total: int) -> str:
    if total <= 0:
        return "0.0%"
    return f"{(count / total) * 100:.1f}%"


def generate_markdown_report(dataset: DatasetModel, report: ValidationReport | None = None) -> str:
    """Build a comprehensive GitHub-flavored Markdown report for dataset coverage and validation."""
    if report is None:
        report = validate_dataset(dataset)

    latest = dataset.latest_version_id()
    deprecated_ids = set(dataset.deprecated_ids())
    total_constants = len(dataset.constants)
    active_constants = total_constants - len(deprecated_ids)
    total_values = sum(len(c.values) for c in dataset.constants)

    if not report.passed:
        status_label = f"❌ FAIL ({report.error_count} errors, {report.warning_count} warnings)"
    elif report.warning_count > 0:
        status_label = f"⚠️ PASS WITH WARNINGS (0 errors, {report.warning_count} warnings)"
    else:
        status_label = "✅ PASS (0 errors, 0 warnings)"

    lines: list[str] = [
        "# CODATA DRUM Constants — Dataset & Validation Report",
        "",
        f"> **Validation Status**: {status_label}  ",
        f"> **Latest CODATA Release**: `{latest}`  ",
        f"> **Schema Version**: `{dataset.schema_version}`",
        "",
        "## 1. Executive Summary",
        "",
        "| Metric | Count |",
        "|---|---:|",
        f"| CODATA Release Versions | {len(dataset.versions)} |",
        f"| Physical Constants (Total) | {total_constants} |",
        f"| Physical Constants (Active in `{latest}`) | {active_constants} |",
        f"| Physical Constants (Deprecated / Historical) | {len(deprecated_ids)} |",
        f"| Versioned Constant Values | {total_values} |",
        f"| Physical Quantities | {len(dataset.quantities)} |",
        f"| Taxonomic Concepts | {len(dataset.concepts)} |",
        f"| Measurement Units | {len(dataset.units)} |",
        f"| NIST Values Cross-Checked | {report.stats.get('nist_checked_values', 0)} |",
        f"| Formula DAG Checks Passed | {report.stats.get('formulas_passed', 0)} / {report.stats.get('formulas_checked', 0)} |",
        f"| Computed-Exact Upgrades (`value_source=computed`) | {report.stats.get('computed_exact_upgraded', 0)} ({report.stats.get('computed_exact_upgraded_latest', 0)} in `{latest}`) |",
        f"| Terminating Exact Rationals Recovered | {report.stats.get('terminating_exact_recovered', 0)} ({report.stats.get('terminating_exact_recovered_latest', 0)} in `{latest}`) |",
        f"| Validation Errors | {report.error_count} |",
        f"| Validation Warnings | {report.warning_count} |",
        "",
        "## 2. CODATA Release Coverage Matrix",
        "",
        "| Release | Published | Constants | Exact | Measured | Truncated (DRUM) | NIST Truncated | Computed Upgrades | Added vs Prev | Retired vs Prev |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]

    chrono_versions = sorted(dataset.versions, key=lambda v: v.id)
    prev_ids: set[str] | None = None
    release_rows: list[str] = []
    for ver in chrono_versions:
        present_ids: set[str] = set()
        exact_cnt = 0
        measured_cnt = 0
        trunc_cnt = 0
        nist_trunc_cnt = 0
        upgraded_cnt = 0
        for const in dataset.constants:
            val = const.value_for_version(ver.id)
            if val is None:
                continue
            present_ids.add(const.id)
            if val.is_exact:
                exact_cnt += 1
            else:
                measured_cnt += 1
            if val.is_truncated:
                trunc_cnt += 1
            if val.is_nist_truncated:
                nist_trunc_cnt += 1
            if val.value_source == "computed":
                upgraded_cnt += 1

        if prev_ids is None:
            added_str = "—"
            retired_str = "—"
        else:
            added_str = str(len(present_ids - prev_ids))
            retired_str = str(len(prev_ids - present_ids))
        prev_ids = present_ids

        release_rows.append(
            f"| `{ver.id}` | {ver.published.isoformat()} | {len(present_ids)} | {exact_cnt} | "
            f"{measured_cnt} | {trunc_cnt} | {nist_trunc_cnt} | {upgraded_cnt} | {added_str} | {retired_str} |"
        )

    lines.extend(reversed(release_rows))
    lines.append("")

    # 3. Determination Role Breakdown
    role_descriptions = {
        "defining": "Exact SI defining & conventional baseline constants (`u = 0`, independent)",
        "computed_exact": "Exact algebraic functions of SI defining constants & π / Wien roots (`u = 0` since May 2019)",
        "adjusted": "Independent CODATA least-squares adjustment (LSA) & theoretical input variables (`u > 0`)",
        "computed_derived": "Algebraically derived from defining + adjusted constants (`u > 0`)",
    }
    latest_role_counts = {
        role: sum(
            1 for c in dataset.constants if (v := c.value_for_version(latest)) is not None and v.adjustment_role == role
        )
        for role in ("defining", "computed_exact", "adjusted", "computed_derived")
    }
    role_2014_counts = {
        role: sum(
            1 for c in dataset.constants if (v := c.value_for_version("2014")) is not None and v.adjustment_role == role
        )
        for role in ("defining", "computed_exact", "adjusted", "computed_derived")
    }
    lines.extend([
        f"## 3. Determination Role Breakdown (`{latest}`)",
        "",
        "| Role (`adjustment_role`) | Active Count | Share | Exact (`is_exact`) | Semantic Description |",
        "|---|---:|---:|:---:|---|",
    ])
    for role in ("defining", "computed_exact", "adjusted", "computed_derived"):
        cnt = latest_role_counts[role]
        exact_mark = "Yes" if role in {"defining", "computed_exact"} else "No"
        lines.append(
            f"| `{role}` | {cnt} | {_pct(cnt, active_constants)} | {exact_mark} | {role_descriptions[role]} |"
        )
    lines.extend([
        f"| *Deprecated (absent in `{latest}`)* | {len(deprecated_ids)} | — | Historical | Retired in or before `{latest}` (`adjustment_role: null`) |",
        "",
        "### Historical Shift Across SI Regimes (2014 Pre-2019 vs 2022 Current SI)",
        "",
        "Because `adjustment_role` and `is_computed` are scoped to `ConstantValue` per release rather than static on `Constant`, the 2019 SI redefinition is represented with historical fidelity across CODATA adjustments:",
        "",
        "| Role (`adjustment_role`) | 2014 (Pre-2019 SI) | 2022 (Current SI) | Net Change | Key Metrological Transitions |",
        "|---|---:|---:|---:|---|",
        f"| `defining` | {role_2014_counts['defining']} | {latest_role_counts['defining']} | {latest_role_counts['defining'] - role_2014_counts['defining']:+d} | $h, e, k, N_{{\\text{{A}}}}$ became defining; $\\mu_0, M(^{{12}}\\text{{C}}), M_{{\\text{{u}}}}$ lost defining status |",
        f"| `computed_exact` | {role_2014_counts['computed_exact']} | {latest_role_counts['computed_exact']} | {latest_role_counts['computed_exact'] - role_2014_counts['computed_exact']:+d} | $F, R, \\hbar, K_{{\\text{{J}}}}, R_{{\\text{{K}}}}, c_1, c_2, \\sigma$ gained exactness; $\\varepsilon_0, Z_0, 4\\pi\\varepsilon_0$ lost exactness |",
        f"| `adjusted` | {role_2014_counts['adjusted']} | {latest_role_counts['adjusted']} | {latest_role_counts['adjusted'] - role_2014_counts['adjusted']:+d} | Primary experimental least-squares adjustment inputs |",
        f"| `computed_derived` | {role_2014_counts['computed_derived']} | {latest_role_counts['computed_derived']} | {latest_role_counts['computed_derived'] - role_2014_counts['computed_derived']:+d} | Quantities derived from adjusted inputs with propagated uncertainty |",
        "",
    ])

    # 4. Two-Source Precision Upgrades & IEEE 754 Numeric Storage Sufficiency
    latest_values = [(c, v) for c in dataset.constants if (v := c.value_for_version(latest)) is not None]
    upgraded_latest = sorted(
        [(c, v) for c, v in latest_values if v.value_source == "computed"],
        key=lambda item: item[0].id,
    )
    terminating_latest = [(c, v) for c, v in upgraded_latest if not v.is_truncated]
    all_vals = [v for c in dataset.constants for v in c.values]

    type_specs = [
        ("float32", "IEEE 754 binary32 (`24`-bit significand, ~6-7 exact decimal digits)"),
        ("float64", "IEEE 754 binary64 (`53`-bit significand, ~15-17 exact decimal digits)"),
        ("decimal", "Arbitrary-precision Decimal / BigDecimal (`> float64` precision or infinite expansion)"),
    ]
    latest_num_counts = report.stats.get("numeric_type_counts", {})
    all_num_counts = report.stats.get("all_numeric_type_counts", {})
    lines.extend([
        "## 4. Two-Source Precision Upgrades & IEEE 754 Storage Sufficiency",
        "",
        f"When NIST SP 961 / SRD 121 truncates an exact constant (`is_nist_truncated: true`) with `...`, "
        f"`drum-constants` retains the verbatim NIST string in `value_nist` and elevates `value` to either its "
        f"complete terminating rational expansion (`is_truncated: false`, **{len(terminating_latest)}** constants in `{latest}`) "
        f"or its 34-significant-digit IEEE 754 `decimal128` truncation (`is_truncated: true`, "
        f"**{len(upgraded_latest) - len(terminating_latest)}** constants in `{latest}`).",
        "",
        "| Recommended Numeric Type | "
        f"`{latest}` Values | Share (`{latest}`) | All Releases | Storage Precision Requirement |",
        "|---|---:|---:|---:|---|",
    ])
    for ntype, desc in type_specs:
        l_cnt = latest_num_counts.get(ntype, sum(1 for _, v in latest_values if v.recommended_numeric_type == ntype))
        a_cnt = all_num_counts.get(ntype, sum(1 for v in all_vals if v.recommended_numeric_type == ntype))
        lines.append(
            f"| `{ntype}` | {l_cnt} | {_pct(l_cnt, len(latest_values))} | {a_cnt} | {desc} |"
        )
    lines.append("")

    if terminating_latest:
        lines.extend([
            f"### Terminating Exact Rationals Recovered in `{latest}` ({len(terminating_latest)} constants)",
            "",
            "| Constant ID | Formula | NIST Truncated (`value_nist`) | Exact Value (`value`) | Digits |",
            "|---|---|---|---|---:|",
        ])
        for c, v in terminating_latest:
            lines.append(
                f"| `{c.id}` | `{c.formula}` | `{v.value_nist}` | `{v.value}` | {v.significant_digits} |"
            )
        lines.append("")

    if upgraded_latest:
        lines.extend([
            f"<details><summary>All {len(upgraded_latest)} computed-exact precision upgrades in {latest}</summary>",
            "",
            "| Constant ID | Source | NIST (`value_nist`) | Primary (`value`) | Sig. Digits | NIST Trunc. | DRUM Trunc. | Storage |",
            "|---|---|---|---|---:|:---:|:---:|---|",
        ])
        for c, v in upgraded_latest:
            lines.append(
                f"| `{c.id}` | `{v.value_source}` | `{v.value_nist}` | `{v.value}` | "
                f"{v.significant_digits} | {v.is_nist_truncated} | {v.is_truncated} | `{v.recommended_numeric_type}` |"
            )
        lines.extend(["", "</details>", ""])

    # 5. External Vocabulary Alignment & Label Coverage
    nist_mapped = sum(1 for c in dataset.constants if c.ids.get("NIST"))
    qudt_mapped = sum(1 for c in dataset.constants if c.ids.get("QUDT"))
    si_const_mapped = sum(1 for c in dataset.constants if c.ids.get("SI"))
    ucum_const_mapped = sum(1 for c in dataset.constants if c.ids.get("UCUM"))
    fr_const_mapped = sum(1 for c in dataset.constants if c.name_fr)
    tex_symbol_mapped = sum(1 for c in dataset.constants if c.symbol_tex)
    formula_mapped = sum(1 for c in dataset.constants if c.formula)

    total_units = len(dataset.units)
    si_unit_mapped = sum(1 for u in dataset.units if u.ids.get("SI"))
    ucum_unit_mapped = sum(1 for u in dataset.units if u.ids.get("UCUM"))
    wd_unit_mapped = sum(1 for u in dataset.units if u.ids.get("WIKIDATA"))

    total_concepts = len(dataset.concepts)
    wd_concept_mapped = sum(1 for c in dataset.concepts if c.ids.get("WIKIDATA"))
    def_concept_mapped = sum(1 for c in dataset.concepts if c.definition)

    coverage_specs = [
        ("NIST Identifiers", "Constants", nist_mapped, total_constants),
        ("QUDT Constants (`qudt_id`)", "Constants", qudt_mapped, total_constants),
        ("SI Digital Framework (`si_id`)", "Constants", si_const_mapped, total_constants),
        ("UCUM Constant Codes (`ucum_id`)", "Constants", ucum_const_mapped, total_constants),
        ("French Labels (`name_fr`)", "Constants", fr_const_mapped, total_constants),
        ("LaTeX Symbols (`symbol_tex`)", "Constants", tex_symbol_mapped, total_constants),
        ("Computable Formulas (`formula`)", "Constants", formula_mapped, total_constants),
        ("SI Digital Framework (`si_id`)", "Units", si_unit_mapped, total_units),
        ("UCUM Unit Codes (`ucum_id`)", "Units", ucum_unit_mapped, total_units),
        ("Wikidata (`wikidata_id`)", "Units", wd_unit_mapped, total_units),
        ("Wikidata (`wikidata_id`)", "Concepts", wd_concept_mapped, total_concepts),
        ("Definitions (`definition`)", "Concepts", def_concept_mapped, total_concepts),
    ]

    lines.extend([
        "## 5. External Vocabulary & Curation Coverage",
        "",
        "| Alignment / Field | Entity Scope | Mapped | Total | Coverage | Progress |",
        "|---|---|---:|---:|---:|---|",
    ])
    for label, scope, cnt, tot in coverage_specs:
        lines.append(f"| {label} | {scope} | {cnt} | {tot} | {_pct(cnt, tot)} | {_progress_bar(cnt, tot)} |")
    lines.append("")

    unmapped_qudt = sorted((c for c in dataset.constants if not c.ids.get("QUDT")), key=lambda c: c.id)
    if unmapped_qudt:
        lines.extend([
            f"<details><summary>Constants without QUDT mapping ({len(unmapped_qudt)})</summary>",
            "",
            "| Constant ID | Name | NIST ID |",
            "|---|---|---|",
        ])
        for c in unmapped_qudt:
            lines.append(f"| `{c.id}` | {c.name} | `{c.ids.get('NIST', '')}` |")
        lines.extend(["", "</details>", ""])

    unmapped_ucum_units = sorted((u for u in dataset.units if not u.ids.get("UCUM")), key=lambda u: u.id)
    if unmapped_ucum_units:
        lines.extend([
            f"<details><summary>Units without UCUM code ({len(unmapped_ucum_units)})</summary>",
            "",
            "| Unit ID | Name | Parts |",
            "|---|---|---|",
        ])
        for u in unmapped_ucum_units:
            lines.append(f"| `{u.id}` | {u.name or '—'} | {', '.join(u.parts) or '—'} |")
        lines.extend(["", "</details>", ""])

    # 6. Deprecated Constants
    lines.extend([
        f"## 6. Deprecated Constants (Absent in `{latest}`)",
        "",
    ])
    if deprecated_ids:
        lines.extend([
            "| Constant ID | Name | NIST ID | Active Releases | Last Release |",
            "|---|---|---|---|---|",
        ])
        for cid in sorted(deprecated_ids):
            c = next(x for x in dataset.constants if x.id == cid)
            vers = sorted(c.version_ids)
            lines.append(
                f"| `{c.id}` | {c.name} | `{c.ids.get('NIST', '')}` | {', '.join(vers)} | `{vers[-1] if vers else '—'}` |"
            )
    else:
        lines.append(f"All constants have recommended values in `{latest}`.")
    lines.append("")

    # 7. Formula DAG & Metrological Identity Verification
    lines.extend([
        f"## 7. Formula DAG & Metrological Identity Verification (`{latest}`)",
        "",
        f"All **{report.stats.get('formulas_passed', 0)} / {report.stats.get('formulas_checked', 0)}** "
        "formula evaluations across exact (`evaluate_exact_dag`) and derived (`evaluate_formula_decimal`) "
        "constants passed Layer 4 consistency checks, alongside key metrological identity anchors:",
        "",
        "| Check | Formula | CODATA Value | Computed | Rel. Error | Tolerance | Status |",
        "|---|---|---:|---:|---:|---:|---|",
    ])
    for chk in report.identity_checks:
        badge = "✅ PASS" if chk.passed else "❌ FAIL"
        lines.append(
            f"| {chk.name} | `{chk.formula}` | `{chk.expected:.12g}` | `{chk.computed:.12g}` | "
            f"`{chk.rel_error:.2e}` | `{chk.tolerance:.0e}` | {badge} |"
        )
    lines.append("")

    # 8. Validation Diagnostics Audit
    lines.extend([
        "## 8. Validation Audit",
        "",
        f"- **Layer 1 (Schema & Precision)**: {sum(1 for d in report.diagnostics if d.layer == 1)} issues",
        f"- **Layer 2 (Referential Integrity & Topology)**: {sum(1 for d in report.diagnostics if d.layer == 2)} issues",
        f"- **Layer 3 (Domain, Labels & SI Hygiene)**: {sum(1 for d in report.diagnostics if d.layer == 3)} issues",
        f"- **Layer 4 (NIST Cross-Check & Identities)**: {sum(1 for d in report.diagnostics if d.layer == 4)} issues",
        "",
    ])
    if report.diagnostics:
        lines.extend([
            "| Layer | Severity | Entity | Code | Message |",
            "|---:|---|---|---|---|",
        ])
        for d in report.diagnostics:
            sev_badge = "❌ ERROR" if d.severity == "error" else "⚠️ WARNING"
            lines.append(f"| L{d.layer} | {sev_badge} | `{d.entity_type}:{d.entity_id}` | `{d.code}` | {d.message} |")
        lines.append("")
    else:
        lines.append("No validation errors or warnings detected.\n")

    # 9. Primary Bibliographic References
    lines.extend([
        "## 9. Primary Bibliographic References",
        "",
        "- **CODATA 2022 Adjustment**: Mohr, P. J., Newell, D. B., Taylor, B. N., & Tiesinga, E. (2025). "
        "\"CODATA recommended values of the fundamental physical constants: 2022.\" "
        "*Reviews of Modern Physics*, 97(2), 025002. DOI: `10.1103/RevModPhys.97.025002`",
        "- **CODATA 2018 Adjustment**: Tiesinga, E., Mohr, P. J., Newell, D. B., & Taylor, B. N. (2021). "
        "\"CODATA recommended values of the fundamental physical constants: 2018.\" "
        "*Reviews of Modern Physics*, 93(2), 025010 / *Journal of Physical and Chemical Reference Data*, 50(3), 033105. "
        "DOI: `10.1103/RevModPhys.93.025010`",
        "- **NIST 2022 Reference Publications**: NIST Special Publication 961 (May 2024), "
        "NIST Special Publication 959 (May 2024), and NIST Standard Reference Database 121 "
        "(`https://physics.nist.gov/cuu/Constants/`).",
        "- **SI Redefinition & BIPM 9th Brochure**: BIPM (2019). *The International System of Units (SI)*, 9th ed.; "
        "Mohr, P. J., Newell, D. B., Taylor, B. N., & Tiesinga, E. (2018). "
        "\"Data and analysis for the CODATA 2017 special fundamental constants adjustment.\" "
        "*Metrologia*, 55(1), 125; Newell, D. B., et al. (2018). "
        "\"The CODATA 2017 values of h, e, k, and N_A for the revision of the SI.\" *Metrologia*, 55(1), L13.",
        "",
    ])

    return "\n".join(lines)


@app.command()
def main(
    data_dir: Path = typer.Option(DATA_DIR, "--data-dir", help="Path to data/ YAML directory"),
    output: Path = typer.Option(
        ROOT_DIR / "docs" / "DATASET_REPORT.md",
        "--output",
        "-o",
        help="Destination path for Markdown report",
    ),
    skip_nist: bool = typer.Option(False, "--skip-nist", help="Skip Layer 4 NIST JSON cross-check"),
) -> None:
    """Generate docs/DATASET_REPORT.md from data/*.yaml and validation results."""
    dataset = load_dataset(data_dir)
    report = validate_dataset(dataset, nist_dir=ROOT_DIR / "nist", skip_nist=skip_nist)
    md = generate_markdown_report(dataset, report)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(md, encoding="utf-8")
    typer.echo(f"Generated Markdown report at {output} ({report.error_count} errors, {report.warning_count} warnings)")


if __name__ == "__main__":
    app()
