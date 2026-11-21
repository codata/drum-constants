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
        f"| Validation Errors | {report.error_count} |",
        f"| Validation Warnings | {report.warning_count} |",
        "",
        "## 2. CODATA Release Coverage Matrix",
        "",
        "| Release | Published | Constants | Exact | Measured | Truncated | Added vs Prev | Retired vs Prev |",
        "|---|---|---:|---:|---:|---:|---:|---:|",
    ]

    chrono_versions = sorted(dataset.versions, key=lambda v: v.id)
    prev_ids: set[str] | None = None
    release_rows: list[str] = []
    for ver in chrono_versions:
        present_ids: set[str] = set()
        exact_cnt = 0
        measured_cnt = 0
        trunc_cnt = 0
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

        if prev_ids is None:
            added_str = "—"
            retired_str = "—"
        else:
            added_str = str(len(present_ids - prev_ids))
            retired_str = str(len(prev_ids - present_ids))
        prev_ids = present_ids

        release_rows.append(
            f"| `{ver.id}` | {ver.published.isoformat()} | {len(present_ids)} | {exact_cnt} | "
            f"{measured_cnt} | {trunc_cnt} | {added_str} | {retired_str} |"
        )

    lines.extend(reversed(release_rows))
    lines.append("")

    # 3. External Vocabulary Alignment & Label Coverage
    nist_mapped = sum(1 for c in dataset.constants if c.ids.get("NIST"))
    qudt_mapped = sum(1 for c in dataset.constants if c.ids.get("QUDT"))
    si_const_mapped = sum(1 for c in dataset.constants if c.ids.get("SI"))
    ucum_const_mapped = sum(1 for c in dataset.constants if c.ids.get("UCUM"))
    fr_const_mapped = sum(1 for c in dataset.constants if c.name_fr)

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
        ("SI Digital Framework (`si_id`)", "Units", si_unit_mapped, total_units),
        ("UCUM Unit Codes (`ucum_id`)", "Units", ucum_unit_mapped, total_units),
        ("Wikidata (`wikidata_id`)", "Units", wd_unit_mapped, total_units),
        ("Wikidata (`wikidata_id`)", "Concepts", wd_concept_mapped, total_concepts),
        ("Definitions (`definition`)", "Concepts", def_concept_mapped, total_concepts),
    ]

    lines.extend([
        "## 3. External Vocabulary & Curation Coverage",
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

    # 4. Deprecated Constants
    lines.extend([
        f"## 4. Deprecated Constants (Absent in `{latest}`)",
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

    # 5. Metrological Identity Verification
    lines.extend([
        f"## 5. Metrological Identity Verification (`{latest}`)",
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

    # 6. Validation Diagnostics Audit
    lines.extend([
        "## 6. Validation Audit",
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
