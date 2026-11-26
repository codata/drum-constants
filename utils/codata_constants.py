"""CLI and build pipeline for CODATA DRUM fundamental physical constants (YAML-first)."""

from __future__ import annotations

import json
import logging
from datetime import date
from pathlib import Path
from typing import Any

import typer

from utils.dataset import DATA_DIR, ROOT_DIR, export_csv, export_json, load_dataset, save_dataset
from utils.models import ConstantValueModel, VersionModel
from utils.package import package_rdf
from utils.report import generate_markdown_report
from utils.validate import ValidationReport, validate_dataset

app = typer.Typer(
    help="Manage, validate, report, sync, and package CODATA DRUM YAML datasets.",
    no_args_is_help=True,
)


def build_all(
    *,
    data_dir: Path = DATA_DIR,
    json_path: Path = ROOT_DIR / "utils" / "codata_constants.json",
    csv_dir: Path = ROOT_DIR / "utils" / "csv",
    rdf_dir: Path = ROOT_DIR / "dist" / "rdf",
    report_path: Path = ROOT_DIR / "docs" / "DATASET_REPORT.md",
    nist_dir: Path = ROOT_DIR / "nist",
    run_validate: bool = True,
    skip_nist: bool = False,
) -> tuple[ValidationReport | None, list[Path]]:
    """Run full YAML -> validate -> JSON + CSV + RDF + Markdown report pipeline."""
    dataset = load_dataset(data_dir)
    validation: ValidationReport | None = None
    if run_validate:
        validation = validate_dataset(dataset, nist_dir=nist_dir, skip_nist=skip_nist)
        if not validation.passed:
            raise ValueError(f"Validation failed with {validation.error_count} error(s)")

    written: list[Path] = []
    written.append(export_json(dataset, json_path))
    written.extend(export_csv(dataset, csv_dir))
    written.extend(package_rdf(dataset=dataset, data_dir=data_dir, output_dir=rdf_dir))

    if validation is None:
        validation = validate_dataset(dataset, nist_dir=nist_dir, skip_nist=skip_nist)
    md = generate_markdown_report(dataset, validation)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(md, encoding="utf-8")
    written.append(report_path)

    return validation, written


@app.command()
def build(
    data_dir: Path = typer.Option(DATA_DIR, "--data-dir", help="Path to data/ YAML directory"),
    json_path: Path = typer.Option(
        ROOT_DIR / "utils" / "codata_constants.json", "--json-out", help="Output path for legacy JSON"
    ),
    csv_dir: Path = typer.Option(ROOT_DIR / "utils" / "csv", "--csv-dir", help="Output directory for CSV snapshots"),
    rdf_dir: Path = typer.Option(ROOT_DIR / "dist" / "rdf", "--rdf-dir", help="Output directory for RDF products"),
    report_path: Path = typer.Option(
        ROOT_DIR / "docs" / "DATASET_REPORT.md", "--report-out", help="Output path for Markdown report"
    ),
    no_validate: bool = typer.Option(False, "--no-validate", help="Skip pre-build validation gate"),
    skip_nist: bool = typer.Option(False, "--skip-nist", help="Skip Layer 4 NIST JSON cross-check"),
    debug: bool = typer.Option(False, "--debug", help="Enable debug logging"),
) -> None:
    """Validate data/*.yaml and build JSON, CSV snapshots, RDF distributions, and Markdown report."""
    logging.basicConfig(
        level=logging.DEBUG if debug else logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )
    try:
        validation, written = build_all(
            data_dir=data_dir,
            json_path=json_path,
            csv_dir=csv_dir,
            rdf_dir=rdf_dir,
            report_path=report_path,
            run_validate=not no_validate,
            skip_nist=skip_nist,
        )
    except ValueError as exc:
        typer.secho(f"Build aborted: {exc}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from exc

    err_cnt = validation.error_count if validation else 0
    warn_cnt = validation.warning_count if validation else 0
    typer.echo(f"Build complete: {len(written)} artifact(s) generated ({err_cnt} errors, {warn_cnt} warnings).")


@app.command("validate")
def validate_cmd(
    data_dir: Path = typer.Option(DATA_DIR, "--data-dir", help="Path to data/ YAML directory"),
    strict: bool = typer.Option(False, "--strict", help="Treat warnings as failures"),
    as_json: bool = typer.Option(False, "--json", help="Emit validation report as JSON"),
    skip_nist: bool = typer.Option(False, "--skip-nist", help="Skip Layer 4 NIST JSON cross-check"),
) -> None:
    """Validate YAML dataset across schema, integrity, hygiene, and NIST alignment."""
    from utils.validate import main as validate_main

    validate_main(
        data_dir=data_dir,
        nist_dir=ROOT_DIR / "nist",
        strict=strict,
        as_json=as_json,
        skip_nist=skip_nist,
    )


@app.command("report")
def report_cmd(
    data_dir: Path = typer.Option(DATA_DIR, "--data-dir", help="Path to data/ YAML directory"),
    output: Path = typer.Option(
        ROOT_DIR / "docs" / "DATASET_REPORT.md", "--output", "-o", help="Destination path for Markdown report"
    ),
    skip_nist: bool = typer.Option(False, "--skip-nist", help="Skip Layer 4 NIST JSON cross-check"),
) -> None:
    """Generate the Markdown dataset and validation report."""
    from utils.report import main as report_main

    report_main(data_dir=data_dir, output=output, skip_nist=skip_nist)


@app.command("sync-nist")
def sync_nist(
    year: str = typer.Option(..., "--year", "-y", help="CODATA release year to sync (e.g., 2022)"),
    apply: bool = typer.Option(False, "--apply", help="Apply NIST updates to data/ YAML files"),
    published: str | None = typer.Option(
        None, "--published", help="Publication date YYYY-MM-DD when adding a new version"
    ),
    data_dir: Path = typer.Option(DATA_DIR, "--data-dir", help="Path to data/ YAML directory"),
    nist_dir: Path = typer.Option(ROOT_DIR / "nist", "--nist-dir", help="Path to nist/ directory"),
    force: bool = typer.Option(
        False,
        "--force",
        help="With --apply, save even if the synchronized dataset fails validation "
        "(e.g. a new release whose adjustment_role values still have to be curated)",
    ),
) -> None:
    """Compare or synchronize a NIST allascii_<year>.json release into data/constants.yaml."""
    nist_json = nist_dir / year / f"allascii_{year}.json"
    if not nist_json.exists():
        typer.secho(f"Missing NIST JSON: {nist_json}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1)

    dataset = load_dataset(data_dir)
    with open(nist_json, encoding="utf-8") as handle:
        nist_rows: list[dict[str, Any]] = json.load(handle)

    const_by_nist = {c.ids["NIST"]: c for c in dataset.constants if c.ids.get("NIST")}

    added = 0
    updated = 0
    unchanged = 0
    unmapped: list[tuple[str | None, str]] = []

    for row in nist_rows:
        nist_id = row.get("nist_id")
        if not nist_id or nist_id not in const_by_nist:
            unmapped.append((nist_id, str(row.get("quantity", ""))))
            continue

        const = const_by_nist[nist_id]
        is_exact = bool(row["is_exact"])
        is_nist_truncated = bool(row["is_truncated"])
        uncertainty = None if is_exact else row["str_uncertainty"]
        exp_raw = row.get("exponent")
        nist_exponent = int(exp_raw[1:]) if exp_raw else None
        unit_raw = str(row.get("unit") or "").replace("{", "").replace("}", "").strip() or None

        existing = const.value_for_version(year)
        nist_str = str(row["str_value"])
        if existing and existing.value_source == "computed" and existing.value_nist == nist_str:
            new_val = ConstantValueModel(
                version=year,
                name=existing.name,
                value=existing.value,
                value_nist=nist_str,
                value_source="computed",
                uncertainty=uncertainty,
                nist_exponent=nist_exponent,
                units=existing.units,
                is_exact=is_exact,
                is_truncated=existing.is_truncated,
                is_nist_truncated=is_nist_truncated,
                adjustment_role=existing.adjustment_role,
            )
        else:
            new_val = ConstantValueModel(
                version=year,
                name=existing.name if existing else str(row["quantity"]),
                value=nist_str,
                value_source="nist",
                uncertainty=uncertainty,
                nist_exponent=nist_exponent,
                units=existing.units if existing else unit_raw,
                is_exact=is_exact,
                is_truncated=is_nist_truncated,
                is_nist_truncated=is_nist_truncated,
                # NIST files carry no determination role; keep the curated one
                adjustment_role=existing.adjustment_role if existing else None,
            )

        if existing is None:
            added += 1
            if apply:
                const.values.append(new_val)
        elif existing.model_dump() != new_val.model_dump():
            updated += 1
            if apply:
                const.values = [new_val if v.version == year else v for v in const.values]
        else:
            unchanged += 1

    typer.echo(
        f"NIST {year} sync summary: {unchanged} unchanged, {updated} updated, "
        f"{added} added, {len(unmapped)} unmapped in constants.yaml"
    )
    for nid, qty in unmapped:
        typer.echo(f"  [UNMAPPED] nist_id={nid!r} quantity={qty!r}")

    if apply:
        if not any(v.id == year for v in dataset.versions):
            pub_date = date.fromisoformat(published) if published else date.today()
            dataset.versions.append(VersionModel(id=year, published=pub_date))
        from utils.validate import validate_dataset

        report = validate_dataset(dataset, nist_dir=nist_dir)
        if not report.passed:
            errors = [d for d in report.diagnostics if d.severity == "error"]
            for diag in errors[:20]:
                typer.echo(
                    f"  [L{diag.layer} ERROR] {diag.entity_type}:{diag.entity_id} ({diag.code}) - {diag.message}"
                )
            if len(errors) > 20:
                typer.echo(f"  ... and {len(errors) - 20} more")
            if not force:
                typer.secho(
                    f"Synchronized dataset fails validation ({report.error_count} errors); nothing saved. "
                    "Use --force to save anyway.",
                    fg=typer.colors.RED,
                    err=True,
                )
                raise typer.Exit(code=1)
            typer.secho(
                f"Saving despite {report.error_count} validation errors (--force).", fg=typer.colors.YELLOW, err=True
            )
        save_dataset(dataset, data_dir)
        typer.echo(f"Saved synchronized YAML dataset to {data_dir}")
    elif added or updated:
        typer.echo("Run with --apply to write these changes to data/*.yaml.")


if __name__ == "__main__":
    app()
