"""FastAPI backend and CLI launcher for the hybrid CODATA DRUM YAML HTML editor."""

from __future__ import annotations

import threading
import webbrowser
from pathlib import Path
from typing import Any

import typer
import uvicorn
from fastapi import Body, FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import ValidationError

from utils.codata_constants import build_all
from utils.dataset import DATA_DIR, ENTITY_FILES, ROOT_DIR, load_dataset, save_dataset, save_entity_file
from utils.models import (
    ConceptModel,
    ConstantModel,
    DatasetModel,
    QuantityModel,
    UnitModel,
    VersionModel,
)
from utils.report import generate_markdown_report
from utils.validate import Diagnostic, validate_dataset

app = typer.Typer(help="Launch the hybrid web editor for CODATA DRUM YAML files.")

_EDITOR_HTML_PATH = Path(__file__).resolve().parent / "editor" / "index.html"


def _strip_computed(model: Any) -> dict[str, Any]:
    computed = set(type(model).model_computed_fields.keys())
    return model.model_dump(mode="json", exclude=computed)


def _dataset_payload(dataset: DatasetModel) -> dict[str, Any]:
    return {
        "schema_version": dataset.schema_version,
        "versions": [_strip_computed(v) for v in sorted(dataset.versions, key=lambda x: x.id, reverse=True)],
        "units": [_strip_computed(u) for u in sorted(dataset.units, key=lambda x: x.id)],
        "concepts": [_strip_computed(c) for c in sorted(dataset.concepts, key=lambda x: x.id)],
        "quantities": [_strip_computed(q) for q in sorted(dataset.quantities, key=lambda x: x.id)],
        "constants": [
            {
                **_strip_computed(c),
                "values": [v.model_dump(mode="json") for v in sorted(c.values, key=lambda x: x.version, reverse=True)],
            }
            for c in sorted(dataset.constants, key=lambda x: x.id)
        ],
        "computed": {
            "latest_version": dataset.latest_version_id(),
            "quantity_ids": sorted(dataset.quantity_ids()),
            "quantity_counts": dataset.quantity_constant_counts(),
            "unit_counts": dataset.unit_constant_counts(),
            "deprecated_ids": dataset.deprecated_ids(),
        },
    }


def _pydantic_error_response(exc: ValidationError) -> JSONResponse:
    diagnostics = [
        Diagnostic(
            layer=1,
            severity="error",
            entity_type="Dataset",
            entity_id=".".join(str(p) for p in err["loc"]),
            code="PYDANTIC_VALIDATION_ERROR",
            message=err["msg"],
        ).model_dump()
        for err in exc.errors()
    ]
    return JSONResponse(
        status_code=422,
        content={
            "detail": "Schema validation failed",
            "error_count": len(diagnostics),
            "warning_count": 0,
            "diagnostics": diagnostics,
        },
    )


def create_app(
    *,
    data_dir: Path = DATA_DIR,
    nist_dir: Path = ROOT_DIR / "nist",
    json_path: Path | None = None,
    csv_dir: Path | None = None,
    rdf_dir: Path | None = None,
    report_path: Path | None = None,
) -> FastAPI:
    """Create the FastAPI application bound to the target data/ directory."""
    resolved_data = data_dir.resolve()
    resolved_nist = nist_dir.resolve()
    out_json = json_path or (ROOT_DIR / "utils" / "codata_constants.json")
    out_csv = csv_dir or (ROOT_DIR / "utils" / "csv")
    out_rdf = rdf_dir or (ROOT_DIR / "dist" / "rdf")
    out_report = report_path or (ROOT_DIR / "docs" / "DATASET_REPORT.md")

    api = FastAPI(title="CODATA DRUM YAML Editor", version="0.3.0")

    @api.get("/", response_class=HTMLResponse)
    def serve_editor() -> HTMLResponse:
        if not _EDITOR_HTML_PATH.exists():
            raise HTTPException(status_code=404, detail="Editor HTML bundle missing")
        return HTMLResponse(content=_EDITOR_HTML_PATH.read_text(encoding="utf-8"))

    @api.get("/api/health")
    def health() -> dict[str, Any]:
        return {
            "status": "ok",
            "mode": "server",
            "data_dir": str(resolved_data),
        }

    @api.get("/api/dataset")
    def get_dataset() -> dict[str, Any]:
        dataset = load_dataset(resolved_data)
        return _dataset_payload(dataset)

    def _validate_l1_l2(candidate: DatasetModel) -> JSONResponse | None:
        report = validate_dataset(candidate, nist_dir=resolved_nist, skip_nist=True)
        l1_l2_errors = [d for d in report.diagnostics if d.severity == "error" and d.layer in {1, 2}]
        if l1_l2_errors:
            return JSONResponse(
                status_code=422,
                content={
                    "detail": f"Dataset validation failed with {len(l1_l2_errors)} error(s)",
                    "error_count": len(l1_l2_errors),
                    "warning_count": report.warning_count,
                    "diagnostics": [d.model_dump() for d in report.diagnostics],
                },
            )
        return None

    @api.put("/api/dataset")
    def put_dataset(payload: dict[str, Any] = Body(...)) -> Any:
        try:
            candidate = DatasetModel.model_validate(payload)
        except ValidationError as exc:
            return _pydantic_error_response(exc)

        err_resp = _validate_l1_l2(candidate)
        if err_resp is not None:
            return err_resp

        written = save_dataset(candidate, resolved_data)
        report = validate_dataset(candidate, nist_dir=resolved_nist, skip_nist=False)
        return {
            "status": "saved",
            "written": [str(p) for p in written.values()],
            "validation": report.model_dump(mode="json"),
            "computed": _dataset_payload(candidate)["computed"],
        }

    @api.put("/api/dataset/{entity_type}")
    def put_entity_file(entity_type: str, payload: Any = Body(...)) -> Any:
        if entity_type not in ENTITY_FILES:
            raise HTTPException(status_code=404, detail=f"Unknown entity type: {entity_type}")

        items_raw = payload.get("items") if isinstance(payload, dict) else payload
        if not isinstance(items_raw, list):
            raise HTTPException(status_code=422, detail="Expected a JSON list or {'items': [...]} payload")

        model_cls_map: dict[str, Any] = {
            "versions": VersionModel,
            "units": UnitModel,
            "concepts": ConceptModel,
            "quantities": QuantityModel,
            "constants": ConstantModel,
        }
        model_cls = model_cls_map[entity_type]
        try:
            parsed_items = [model_cls.model_validate(item) for item in items_raw]
        except ValidationError as exc:
            return _pydantic_error_response(exc)

        current = load_dataset(resolved_data)
        candidate = current.model_copy(update={entity_type: parsed_items})
        err_resp = _validate_l1_l2(candidate)
        if err_resp is not None:
            return err_resp

        out_path = save_entity_file(entity_type, parsed_items, resolved_data)
        report = validate_dataset(candidate, nist_dir=resolved_nist, skip_nist=False)
        return {
            "status": "saved",
            "written": [str(out_path)],
            "validation": report.model_dump(mode="json"),
            "computed": _dataset_payload(candidate)["computed"],
        }

    @api.post("/api/validate")
    async def post_validate(request: Request) -> Any:
        raw_body = await request.body()
        if raw_body.strip():
            try:
                payload = await request.json()
                dataset = DatasetModel.model_validate(payload)
            except ValidationError as exc:
                return _pydantic_error_response(exc)
        else:
            dataset = load_dataset(resolved_data)

        report = validate_dataset(dataset, nist_dir=resolved_nist, skip_nist=False)
        markdown_report = generate_markdown_report(dataset, report)
        return {
            **report.model_dump(mode="json"),
            "markdown_report": markdown_report,
        }

    @api.post("/api/package")
    def post_package() -> Any:
        try:
            report, written = build_all(
                data_dir=resolved_data,
                json_path=out_json,
                csv_dir=out_csv,
                rdf_dir=out_rdf,
                report_path=out_report,
                nist_dir=resolved_nist,
                run_validate=True,
            )
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

        return {
            "status": "packaged",
            "artifacts": [str(p) for p in written],
            "error_count": report.error_count if report else 0,
            "warning_count": report.warning_count if report else 0,
        }

    return api


@app.command()
def main(
    host: str = typer.Option("127.0.0.1", "--host", help="Bind host address"),
    port: int = typer.Option(8080, "--port", "-p", help="Bind TCP port"),
    data_dir: Path = typer.Option(DATA_DIR, "--data-dir", help="Path to data/ YAML directory"),
    open_browser: bool = typer.Option(True, "--open/--no-open", help="Open editor in default browser"),
) -> None:
    """Start the local FastAPI YAML editor server."""
    fastapi_app = create_app(data_dir=data_dir)
    url = f"http://{host}:{port}"
    typer.echo(f"Starting CODATA DRUM YAML Editor at {url} (data_dir={data_dir})")
    if open_browser:
        threading.Timer(0.8, lambda: webbrowser.open(url)).start()
    uvicorn.run(fastapi_app, host=host, port=port, log_level="info")


if __name__ == "__main__":
    app()
