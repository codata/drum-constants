"""YAML storage, deterministic serialization, and JSON/CSV export for CODATA DRUM constants."""

from __future__ import annotations

import csv
import json
import os
import re
import tempfile
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel

from utils.models import (
    ConceptModel,
    ConstantModel,
    DatasetModel,
    QuantityModel,
    UnitModel,
    VersionModel,
)

ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data"

ENTITY_FILES: dict[str, str] = {
    "versions": "versions.yaml",
    "units": "units.yaml",
    "concepts": "concepts.yaml",
    "quantities": "quantities.yaml",
    "constants": "constants.yaml",
}

_NUMERIC_RE = re.compile(r"^[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?$")
_ISO_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_AMBIGUOUS_WORDS = {
    "true",
    "false",
    "yes",
    "no",
    "on",
    "off",
    "y",
    "n",
    "null",
    "~",
    ".inf",
    "+.inf",
    "-.inf",
    ".nan",
    "inf",
    "-inf",
    "nan",
}


def _needs_yaml_quotes(value: str) -> bool:
    """Return True if a scalar string could be coerced to a non-string by YAML/js-yaml."""
    if value == "":
        return True
    if value.lower() in _AMBIGUOUS_WORDS:
        return True
    if _NUMERIC_RE.match(value) or _ISO_DATE_RE.match(value):
        return True
    if value.startswith(("0x", "0o", "0b")):
        return True
    return False


class CodataYamlDumper(yaml.SafeDumper):
    """Custom PyYAML SafeDumper preserving exact numeric/date/boolean strings."""

    def increase_indent(self, flow: bool = False, indentless: bool = False) -> None:
        return super().increase_indent(flow, False)


def _represent_codata_str(dumper: yaml.SafeDumper, data: str) -> yaml.ScalarNode:
    style = '"' if _needs_yaml_quotes(data) else None
    return dumper.represent_scalar("tag:yaml.org,2002:str", data, style=style)


CodataYamlDumper.add_representer(str, _represent_codata_str)


def _clean_record(model: BaseModel, *, keep_false_fields: set[str] | None = None) -> dict[str, Any]:
    """Dump a Pydantic model excluding computed fields, None values, and empty/default fields."""
    computed = set(type(model).model_computed_fields.keys())
    raw = model.model_dump(mode="json", exclude=computed, exclude_none=True)
    return _prune_dict(raw, keep_false_fields=keep_false_fields or set())


def _prune_dict(data: dict[str, Any], *, keep_false_fields: set[str]) -> dict[str, Any]:
    cleaned: dict[str, Any] = {}
    for key, val in data.items():
        if val is None:
            continue
        if isinstance(val, bool) and not val and key not in keep_false_fields:
            continue
        if isinstance(val, (list, dict)) and len(val) == 0:
            continue
        if key == "values" and isinstance(val, list):
            cleaned[key] = [_prune_dict(item, keep_false_fields={"is_exact", "is_truncated"}) for item in val]
        else:
            cleaned[key] = val
    return cleaned


def _atomic_write_text(path: Path, content: str) -> None:
    """Atomically write UTF-8 text to a file via a temporary file in the same directory."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(content)
        os.replace(tmp_name, path)
    except Exception:
        if os.path.exists(tmp_name):
            os.unlink(tmp_name)
        raise


def serialize_yaml_records(records: list[dict[str, Any]]) -> str:
    """Serialize a list of dictionaries to deterministic, human-readable YAML."""
    return yaml.dump(
        records,
        Dumper=CodataYamlDumper,
        allow_unicode=True,
        sort_keys=False,
        default_flow_style=False,
        width=120,
    )


def _load_yaml_list(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(f"Missing dataset YAML file: {path}")
    with open(path, encoding="utf-8") as handle:
        loaded = yaml.safe_load(handle)
    if loaded is None:
        return []
    if not isinstance(loaded, list):
        raise ValueError(f"Expected top-level YAML sequence in {path}, got {type(loaded).__name__}")
    return loaded


def load_dataset(data_dir: Path = DATA_DIR) -> DatasetModel:
    """Load and Pydantic-validate the complete dataset from modular YAML files."""
    versions = [VersionModel.model_validate(item) for item in _load_yaml_list(data_dir / ENTITY_FILES["versions"])]
    units = [UnitModel.model_validate(item) for item in _load_yaml_list(data_dir / ENTITY_FILES["units"])]
    concepts = [ConceptModel.model_validate(item) for item in _load_yaml_list(data_dir / ENTITY_FILES["concepts"])]
    quantities = [QuantityModel.model_validate(item) for item in _load_yaml_list(data_dir / ENTITY_FILES["quantities"])]
    constants = [ConstantModel.model_validate(item) for item in _load_yaml_list(data_dir / ENTITY_FILES["constants"])]

    return DatasetModel(
        versions=versions,
        units=units,
        concepts=concepts,
        quantities=quantities,
        constants=constants,
    )


def _prepare_sorted_records(entity_type: str, items: list[Any]) -> list[dict[str, Any]]:
    if entity_type == "versions":
        ordered = sorted(items, key=lambda v: v.id, reverse=True)
        return [_clean_record(item) for item in ordered]
    if entity_type == "constants":
        ordered = sorted(items, key=lambda c: c.id)
        records: list[dict[str, Any]] = []
        for const in ordered:
            sorted_vals = sorted(const.values, key=lambda x: x.version, reverse=True)
            const_copy = const.model_copy(update={"values": sorted_vals})
            records.append(_clean_record(const_copy))
        return records
    ordered = sorted(items, key=lambda item: item.id)
    return [_clean_record(item) for item in ordered]


def save_entity_file(entity_type: str, items: list[Any], data_dir: Path = DATA_DIR) -> Path:
    """Deterministically sort and atomically save one entity YAML file."""
    if entity_type not in ENTITY_FILES:
        raise ValueError(f"Unknown entity type {entity_type!r}; expected one of {list(ENTITY_FILES)}")
    records = _prepare_sorted_records(entity_type, items)
    yaml_text = serialize_yaml_records(records)
    out_path = data_dir / ENTITY_FILES[entity_type]
    _atomic_write_text(out_path, yaml_text)
    return out_path


def save_dataset(dataset: DatasetModel, data_dir: Path = DATA_DIR) -> dict[str, Path]:
    """Deterministically sort and atomically save all five YAML dataset files."""
    data_dir.mkdir(parents=True, exist_ok=True)
    written: dict[str, Path] = {}
    written["versions"] = save_entity_file("versions", dataset.versions, data_dir)
    written["units"] = save_entity_file("units", dataset.units, data_dir)
    written["concepts"] = save_entity_file("concepts", dataset.concepts, data_dir)
    written["quantities"] = save_entity_file("quantities", dataset.quantities, data_dir)
    written["constants"] = save_entity_file("constants", dataset.constants, data_dir)
    return written


def export_json(dataset: DatasetModel, json_path: Path) -> Path:
    """Export legacy codata_constants.json from the authoritative YAML DatasetModel."""
    payload = dataset.to_legacy_json()
    _atomic_write_text(json_path, json.dumps(payload, indent=4, ensure_ascii=False) + "\n")
    return json_path


def _write_csv(path: Path, headers: list[str], rows: list[list[Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow(headers)
            writer.writerows(rows)
        os.replace(tmp_name, path)
    except Exception:
        if os.path.exists(tmp_name):
            os.unlink(tmp_name)
        raise


def export_csv(dataset: DatasetModel, csv_dir: Path) -> list[Path]:
    """Export legacy Git-tracked CSV snapshots (with computed columns) from DatasetModel."""
    csv_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []

    q_ids = dataset.quantity_ids()
    c_ids = {c.id for c in dataset.concepts}
    u_ids = {u.id for u in dataset.units}
    qty_counts = dataset.quantity_constant_counts()
    unit_counts = dataset.unit_constant_counts()
    version_ids = [v.id for v in sorted(dataset.versions, key=lambda x: x.id, reverse=True)]

    # Concepts.csv
    concepts_path = csv_dir / "Concepts.csv"
    concept_rows = []
    for c in sorted(dataset.concepts, key=lambda x: x.id):
        wid = c.ids.get("WIKIDATA", "")
        concept_rows.append([
            c.id,
            c.name,
            1 if c.id in q_ids else 0,
            c.is_ratio,
            c.is_relationship,
            ",".join(c.groups),
            ",".join(c.broader),
            ",".join(c.parts),
            ",".join(c.related),
            ",".join(c.same_as),
            "",
            c.notation_tex or "",
            wid,
            wid,
            c.definition or "",
            c.name_fr or "",
            c.definition_fr or "",
        ])
    _write_csv(
        concepts_path,
        [
            "id",
            "name",
            "is_quantity",
            "is_ratio",
            "is_relationship",
            "groups",
            "broader",
            "parts",
            "related",
            "same_as",
            "other_properties",
            "notation_tex",
            "wikidata_id",
            "wikidata_url",
            "definition",
            "name_fr",
            "definition_fr",
        ],
        concept_rows,
    )
    written.append(concepts_path)

    # Quantities.csv
    quantities_path = csv_dir / "Quantities.csv"
    qty_rows = [
        [
            q.id,
            q.name,
            q.notation or "",
            1 if q.id in c_ids else 0,
            qty_counts.get(q.id, 0),
            q.uri,
        ]
        for q in sorted(dataset.quantities, key=lambda x: x.id)
    ]
    _write_csv(quantities_path, ["id", "name", "notation", "has_concept", "n_constants", "uri"], qty_rows)
    written.append(quantities_path)

    # Units.csv
    units_path = csv_dir / "Units.csv"
    unit_rows = [
        [
            u.id,
            u.name or "",
            ",".join(u.parts),
            u.si_expression or "",
            u.ids.get("SI", ""),
            u.si_uri or "",
            u.ids.get("UCUM", ""),
            u.ucum_uri or "",
            unit_counts.get(u.id, 0),
            u.ids.get("WIKIDATA", ""),
            u.wikipedia or "",
        ]
        for u in sorted(dataset.units, key=lambda x: x.id)
    ]
    _write_csv(
        units_path,
        [
            "id",
            "name",
            "parts",
            "si_expression",
            "si_id",
            "si_uri",
            "ucum_id",
            "ucum_uri",
            "n_constants",
            "wikidata_id",
            "wikipedia",
        ],
        unit_rows,
    )
    written.append(units_path)

    # Versions.csv
    versions_path = csv_dir / "Versions.csv"
    version_rows = [
        [v.id, v.published.isoformat(), v.description or ""]
        for v in sorted(dataset.versions, key=lambda x: x.id, reverse=True)
    ]
    _write_csv(versions_path, ["id", "published", "description"], version_rows)
    written.append(versions_path)

    # Constants.csv
    constants_path = csv_dir / "Constants.csv"
    const_headers = [
        "nist_id",
        "id",
        "name",
        "name_fr",
        "name_bipm_en",
        "name_bipm_fr",
        "unit_nist",
        "unit_id",
        "unit_id_lookup",
        "quantity_id",
        "quantity_id_lookup",
        "is_base",
        "qudt_id",
        "qudt_url",
        "is_qudt",
        "ucum_id",
        "si_id",
        "si_url",
        "versions",
        *[f"is_{vid}" for vid in version_ids],
    ]
    const_rows = []
    for c in sorted(dataset.constants, key=lambda x: x.id):
        present = {v.version for v in c.values}
        qudt_id = c.ids.get("QUDT", "")
        si_id = c.ids.get("SI", "")
        const_rows.append([
            c.ids.get("NIST", ""),
            c.id,
            c.name,
            c.name_fr or "",
            c.name_bipm_en or "",
            c.name_bipm_fr or "",
            c.unit_nist or "",
            c.unit_id or "",
            (1 if c.unit_id in u_ids else 0) if c.unit_id else "",
            c.quantity_id,
            1 if c.quantity_id in q_ids else 0,
            c.is_base,
            qudt_id,
            "qudt" if qudt_id else "",
            c.is_qudt,
            c.ids.get("UCUM", ""),
            si_id,
            "SI" if si_id else "",
            len(present),
            *[1 if vid in present else 0 for vid in version_ids],
        ])
    _write_csv(constants_path, const_headers, const_rows)
    written.append(constants_path)

    # v<year>.csv per version
    for vid in version_ids:
        v_path = csv_dir / f"v{vid}.csv"
        v_rows: list[list[Any]] = []
        entries: list[tuple[str, ConstantModel, Any]] = []
        for c in dataset.constants:
            val = c.value_for_version(vid)
            if val is not None:
                entries.append((val.name.lower(), c, val))
        for _, c, val in sorted(entries, key=lambda x: (x[0], x[1].id)):
            nist_id = c.ids.get("NIST", "")
            unc_display = "(exact)" if val.is_exact else (val.uncertainty or "")
            unc_num = "" if val.is_exact or val.uncertainty is None else float(val.uncertainty)
            v_rows.append([
                val.name,
                val.value,
                unc_display,
                val.units or "",
                nist_id,
                1,
                val.value,
                float(val.value),
                unc_display,
                unc_num,
                val.is_exact,
                val.is_truncated,
                val.exponent if val.exponent is not None else "",
            ])
        _write_csv(
            v_path,
            [
                "name",
                "value_nist",
                "uncertainty_nist",
                "units",
                "id",
                "id_lookup",
                "value_str",
                "value_num",
                "uncertainty_str",
                "uncertainty_n",
                "is_exact",
                "is_truncated",
                "exponent",
            ],
            v_rows,
        )
        written.append(v_path)

    return written
