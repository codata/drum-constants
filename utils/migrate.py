"""One-time migration from legacy CSV/JSON snapshots and NIST JSONs into modular YAML files."""

from __future__ import annotations

import csv
import json
import logging
from datetime import date
from pathlib import Path
from typing import Any

from utils.dataset import DATA_DIR, ROOT_DIR, save_dataset
from utils.models import (
    ConceptModel,
    ConstantModel,
    ConstantValueModel,
    DatasetModel,
    QuantityModel,
    UnitModel,
    VersionModel,
)

logger = logging.getLogger(__name__)


def _parse_bool(raw: Any) -> bool:
    if isinstance(raw, bool):
        return raw
    if raw is None:
        return False
    return str(raw).strip().lower() in {"1", "true", "yes"}


def _split_csv_list(raw: str | None) -> list[str]:
    if not raw or not raw.strip():
        return []
    return [item.strip() for item in raw.split(",") if item.strip()]


def _opt_str(raw: str | None) -> str | None:
    if raw is None:
        return None
    val = raw.strip()
    return val if val else None


def _load_nist_index(nist_dir: Path, years: list[str]) -> dict[tuple[str, str], dict[str, Any]]:
    index: dict[tuple[str, str], dict[str, Any]] = {}
    for year in years:
        json_path = nist_dir / year / f"allascii_{year}.json"
        if not json_path.exists():
            raise FileNotFoundError(f"Missing authoritative NIST JSON: {json_path}")
        with open(json_path, encoding="utf-8") as handle:
            for item in json.load(handle):
                nid = item.get("nist_id")
                if nid:
                    index[(year, nid)] = item
    return index


def build_dataset_from_legacy(
    csv_dir: Path = ROOT_DIR / "utils" / "csv",
    legacy_json_path: Path = ROOT_DIR / "utils" / "codata_constants.json",
    nist_dir: Path = ROOT_DIR / "nist",
) -> DatasetModel:
    """Build a clean, validated DatasetModel from legacy CSVs, JSON, and authoritative NIST JSONs."""
    # 1. Versions
    versions: list[VersionModel] = []
    with open(csv_dir / "Versions.csv", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            versions.append(
                VersionModel(
                    id=row["id"].strip(),
                    published=date.fromisoformat(row["published"].strip()),
                    description=_opt_str(row.get("description")),
                )
            )
    version_years = [v.id for v in versions]

    # 2. Units
    units: list[UnitModel] = []
    with open(csv_dir / "Units.csv", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            ids: dict[str, str] = {}
            if si_id := _opt_str(row.get("si_id")):
                ids["SI"] = si_id
            if ucum_id := _opt_str(row.get("ucum_id")):
                ids["UCUM"] = ucum_id
            if wikidata_id := _opt_str(row.get("wikidata_id")):
                ids["WIKIDATA"] = wikidata_id
            units.append(
                UnitModel(
                    id=row["id"].strip(),
                    name=_opt_str(row.get("name")),
                    parts=_split_csv_list(row.get("parts")),
                    si_expression=_opt_str(row.get("si_expression")),
                    ids=ids,
                    wikipedia=_opt_str(row.get("wikipedia")),
                )
            )

            if not any(u.id == "Hz_V-1" for u in units):
                units.append(
                    UnitModel(
                        id="Hz_V-1",
                        name="hertz per volt",
                        parts=["Hz", "V"],
                        si_expression="Hz.V-1",
                        ids={"SI": "hertz.volt-1", "UCUM": "Hz.V-1"},
                    )
                )

    # 3. Concepts (remove self-loops and Acceleration/Relationship errant taxonomy flags)
    concepts: list[ConceptModel] = []
    with open(csv_dir / "Concepts.csv", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            cid = row["id"].strip()
            ids = {}
            if wikidata_id := _opt_str(row.get("wikidata_id")):
                ids["WIKIDATA"] = wikidata_id
            broader = [b for b in _split_csv_list(row.get("broader")) if b != cid]
            parts = [p for p in _split_csv_list(row.get("parts")) if p != cid]
            is_ratio = _parse_bool(row.get("is_ratio"))
            is_relationship = _parse_bool(row.get("is_relationship"))
            if cid == "Acceleration":
                is_ratio = False
                parts = [p for p in parts if p != "Ratio"]
            if cid == "Relationship":
                is_relationship = False
                parts = [p for p in parts if p != "Relationship"]
            if is_ratio and cid != "Ratio" and "Ratio" not in parts:
                parts.append("Ratio")
            if is_relationship and cid != "Relationship" and "Relationship" not in parts:
                parts.append("Relationship")

            concepts.append(
                ConceptModel(
                    id=cid,
                    name=row["name"].strip(),
                    name_fr=_opt_str(row.get("name_fr")),
                    definition=_opt_str(row.get("definition")),
                    definition_fr=_opt_str(row.get("definition_fr")),
                    notation_tex=_opt_str(row.get("notation_tex")),
                    is_ratio=is_ratio,
                    is_relationship=is_relationship,
                    broader=broader,
                    parts=parts,
                    related=_split_csv_list(row.get("related")),
                    same_as=_split_csv_list(row.get("same_as")),
                    groups=_split_csv_list(row.get("groups")),
                    ids=ids,
                )
            )

    # 4. Quantities
    quantities: list[QuantityModel] = []
    with open(csv_dir / "Quantities.csv", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            notation_raw = row.get("notation ") if "notation " in row else row.get("notation")
            quantities.append(
                QuantityModel(
                    id=row["id"].strip(),
                    name=row["name"].strip(),
                    notation=_opt_str(notation_raw),
                )
            )

    # 5. Load legacy JSON for ConstantValue entries (units & cleaned historical names)
    with open(legacy_json_path, encoding="utf-8") as handle:
        legacy_json = json.load(handle)

    legacy_values_by_const: dict[str, list[dict[str, Any]]] = {}
    for q in legacy_json.get("quantities", []):
        for c in q.get("constants", []):
            legacy_values_by_const[c["id"]] = c.get("values", [])

    nist_index = _load_nist_index(nist_dir, version_years)

    # 6. Constants + authoritative NIST ConstantValues
    constants: list[ConstantModel] = []
    with open(csv_dir / "Constants.csv", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            cid = row["id"].strip()
            nist_id = row["nist_id"].strip()
            name = row["name"].strip()
            name_bipm_en = _opt_str(row.get("name_bipm_en"))
            if nist_id == "mnmmpu" and name == "Neutron - Muon Mass Ratio In U":
                name = "Neutron - Proton Mass Difference In U"
            if nist_id == "mnmmpu" and name_bipm_en == "neutron - muon mass ratio in u":
                name_bipm_en = "neutron - proton mass difference in u"

            ids: dict[str, str] = {"NIST": nist_id}
            if qudt_id := _opt_str(row.get("qudt_id")):
                ids["QUDT"] = qudt_id
            if si_id := _opt_str(row.get("si_id")):
                ids["SI"] = si_id
            if ucum_id := _opt_str(row.get("ucum_id")):
                ids["UCUM"] = ucum_id

            values: list[ConstantValueModel] = []
            for raw_val in legacy_values_by_const.get(cid, []):
                version = str(raw_val["version"])
                nist_entry = nist_index[(version, nist_id)]

                # Use authoritative NIST uncertainty, is_exact, and is_truncated
                # (fixes 1998-2006 spreadsheet 10^k uncertainty bug, pre-2010 exact flag, and 2022 truncation)
                is_exact = bool(nist_entry["is_exact"])
                is_truncated = bool(nist_entry["is_truncated"])
                uncertainty = None if is_exact else nist_entry["str_uncertainty"]
                exp_raw = raw_val.get("exponent")
                exponent = int(exp_raw) if exp_raw not in (None, "") else None

                values.append(
                    ConstantValueModel(
                        version=version,
                        name=raw_val["name"],
                        value=nist_entry["str_value"],
                        uncertainty=uncertainty,
                        exponent=exponent,
                        units=_opt_str(raw_val.get("units")),
                        is_exact=is_exact,
                        is_truncated=is_truncated,
                    )
                )

            unit_id = _opt_str(row.get("unit_id"))
            if cid == "FaradayConstantConventionalElectricCurrent" and unit_id == "C90_mol-1":
                unit_id = "CXC_mol-1"
            elif cid == "ConventionalValueOfCoulomb90" and unit_id == "CXC_mol-1":
                unit_id = "CXC"

            constants.append(
                ConstantModel(
                    id=cid,
                    quantity_id=row["quantity_id"].strip(),
                    unit_id=unit_id,
                    unit_nist=_opt_str(row.get("unit_nist")),
                    name=name,
                    name_fr=_opt_str(row.get("name_fr")),
                    name_bipm_en=name_bipm_en,
                    name_bipm_fr=_opt_str(row.get("name_bipm_fr")),
                    ids=ids,
                    values=values,
                )
            )

    return DatasetModel(
        versions=versions,
        units=units,
        concepts=concepts,
        quantities=quantities,
        constants=constants,
    )


def migrate(data_dir: Path = DATA_DIR) -> dict[str, Path]:
    """Run one-time migration and save modular YAML files to data/."""
    dataset = build_dataset_from_legacy()
    written = save_dataset(dataset, data_dir)
    total_values = sum(len(c.values) for c in dataset.constants)
    logger.info(
        "Migrated %d versions, %d units, %d concepts, %d quantities, %d constants (%d values) -> %s",
        len(dataset.versions),
        len(dataset.units),
        len(dataset.concepts),
        len(dataset.quantities),
        len(dataset.constants),
        total_values,
        data_dir,
    )
    return written


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    migrate()
