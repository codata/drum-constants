"""Pydantic v2 data models and computed-field helpers for CODATA DRUM constants."""

from __future__ import annotations

import re
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any, Literal
from urllib.parse import quote

from pydantic import BaseModel, Field, computed_field, field_validator, model_validator

from utils.formulas import (
    check_fits_float32,
    check_fits_float64,
    count_significant_digits,
    extract_dependencies,
    get_recommended_numeric_type,
    validate_formula_syntax,
)

AdjustmentRole = Literal["defining", "computed_exact", "adjusted", "computed_derived"]
ValueSource = Literal["nist", "computed"]

# Case-sensitive scientific tokens preserved when deriving Constant.name from name_bipm_en
_SI_TOKEN_MAP: dict[str, str] = {
    "ev": "eV",
    "mev": "MeV",
    "gev": "GeV",
    "kev": "keV",
    "tev": "TeV",
    "kpa": "kPa",
    "mhz": "MHz",
    "ghz": "GHz",
    "khz": "kHz",
    "hz": "Hz",
    "fm": "fm",
    "pm": "pm",
    "nm": "nm",
    "mm": "mm",
    "cm": "cm",
    "km": "km",
    "kg": "kg",
    "mol": "mol",
    "rms": "rms",
    "hd": "HD",
    "ht": "HT",
    "bohr": "Bohr",
    "planck": "Planck",
    "rydberg": "Rydberg",
    "faraday": "Faraday",
    "avogadro": "Avogadro",
    "boltzmann": "Boltzmann",
    "stefan": "Stefan",
    "wien": "Wien",
    "josephson": "Josephson",
    "klitzing": "Klitzing",
    "hartree": "Hartree",
    "compton": "Compton",
    "thomson": "Thomson",
    "loschmidt": "Loschmidt",
    "angstrom": "Angstrom",
    "fermi": "Fermi",
    "larmor": "Larmor",
    "zeeman": "Zeeman",
    "newtonian": "Newtonian",
    "coulomb": "Coulomb",
    "sackur": "Sackur",
    "tetrode": "Tetrode",
    "einstein": "Einstein",
    "dirac": "Dirac",
    "curie": "Curie",
    "debye": "Debye",
    "u": "u",
}


# Symbols written exactly as given (case-sensitive) in English constant names
_KEEP_CASE_TOKENS: frozenset[str] = frozenset(
    {"c", "h", "hc", "s", "m", "e", "k", "K", "J", "T", "V", "W", "C", "A", "N", "F", "H"}
    | {"u", "g", "x", "d", "p", "t", "pi", "bar"}
    | {"Si", "SI"}  # silicon vs. the SI: case decides, so never map one onto the other
)


def default_constant_name_en(name_bipm_en: str) -> str:
    """Derive title-cased English Constant.name from BIPM lowercase text while preserving symbol case.

    Every run of letters is treated as one token, so symbols next to punctuation or
    hyphens (``kPa)``, ``h-bar``, ``MeV/c``) keep their case too. Symbols such as
    u, g, c, hc, pi, d, p, t, x, HD, HT are never title-cased.
    """
    if not name_bipm_en:
        return ""

    def _replace_part(part: str) -> str:
        low = part.lower()
        if low in _SI_TOKEN_MAP:
            return _SI_TOKEN_MAP[low]
        if part in _KEEP_CASE_TOKENS:
            return part
        return part[:1].upper() + part[1:].lower() if part else part

    return re.sub(r"[A-Za-z]+", lambda m: _replace_part(m.group(0)), name_bipm_en)


def default_constant_name_fr(name_bipm_fr: str) -> str:
    """Derive sentence-capitalized French Constant.name_fr from name_bipm_fr."""
    s = name_bipm_fr.strip()
    if not s:
        return ""
    return s[0].upper() + s[1:]


def default_unit_id(unit_nist: str) -> str:
    """Derive canonical Unit.id from NIST unit expression (spreadsheet formula equivalent)."""
    if not unit_nist:
        return ""
    return unit_nist.strip().replace("^", "").replace(" ", "_")


def default_si_expression(unit_id: str) -> str:
    """Derive UCUM/SI dot-separated expression from Unit.id (spreadsheet formula equivalent)."""
    if not unit_id or "XC" in unit_id:
        return ""
    return unit_id.replace("_", ".")


def _validate_decimal_str(raw: str, field_name: str) -> str:
    """Validate that a string represents a finite decimal number without whitespace or ellipses."""
    if not isinstance(raw, str):
        raise ValueError(f"{field_name} must be a string to preserve exact precision, got {type(raw).__name__}")
    if raw != raw.strip() or " " in raw or "..." in raw:
        raise ValueError(f"{field_name} must be normalized without spaces or ellipses: {raw!r}")
    try:
        dec = Decimal(raw)
    except InvalidOperation as exc:
        raise ValueError(f"{field_name} is not a valid decimal literal: {raw!r}") from exc
    if not dec.is_finite():
        raise ValueError(f"{field_name} must be finite: {raw!r}")
    return raw


class VersionModel(BaseModel):
    """A CODATA fundamental physical constants release version."""

    id: str
    published: date
    description: str | None = None

    @field_validator("id")
    @classmethod
    def _validate_year_id(cls, v: str) -> str:
        if not re.fullmatch(r"\d{4}", v):
            raise ValueError(f"Version id must be a 4-digit year string, got {v!r}")
        return v


class UnitModel(BaseModel):
    """A physical unit of measurement linked to SI Digital Framework and UCUM."""

    id: str
    name: str | None = None
    parts: list[str] = Field(default_factory=list)
    si_expression: str | None = None
    ids: dict[str, str] = Field(default_factory=dict)
    wikipedia: str | None = None

    @field_validator("id")
    @classmethod
    def _validate_id(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Unit id cannot be empty")
        return v

    @computed_field
    @property
    def si_uri(self) -> str | None:
        si_id = self.ids.get("SI")
        return f"https://si-digital-framework.org/SI/units/{si_id}" if si_id else None

    @computed_field
    @property
    def ucum_uri(self) -> str | None:
        ucum_id = self.ids.get("UCUM")
        if not ucum_id or ucum_id == "?":
            return None
        return f"https://w3id.org/uom/{quote(ucum_id)}"

    @property
    def display_name(self) -> str | None:
        if self.name:
            return self.name
        si_id = self.ids.get("SI")
        if si_id:
            return si_id.replace(".", " ")
        return None


class ConceptModel(BaseModel):
    """A taxonomic concept organizing physical quantities and constants."""

    id: str
    name: str
    name_fr: str | None = None
    definition: str | None = None
    definition_fr: str | None = None
    notation_tex: str | None = None
    is_ratio: bool = False
    is_relationship: bool = False
    broader: list[str] = Field(default_factory=list)
    parts: list[str] = Field(default_factory=list)
    related: list[str] = Field(default_factory=list)
    same_as: list[str] = Field(default_factory=list)
    groups: list[str] = Field(default_factory=list)
    ids: dict[str, str] = Field(default_factory=dict)

    @field_validator("id", "name")
    @classmethod
    def _non_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Concept id and name must be non-empty")
        return v

    @computed_field
    @property
    def wikidata_url(self) -> str | None:
        wid = self.ids.get("WIKIDATA")
        return f"https://www.wikidata.org/wiki/{wid}" if wid else None

    @property
    def effective_parts(self) -> list[str]:
        """Return parts list augmented with Ratio/Relationship markers when flagged."""
        result = list(self.parts)
        if self.is_ratio and self.id != "Ratio" and "Ratio" not in result:
            result.append("Ratio")
        if self.is_relationship and self.id != "Relationship" and "Relationship" not in result:
            result.append("Relationship")
        return result


class QuantityModel(BaseModel):
    """A physical measurable property grouping one or more constants."""

    id: str
    name: str
    notation: str | None = None
    definition: str | None = None
    is_ratio: bool = False
    is_relationship: bool = False
    has_parts: list[str] = Field(default_factory=list)
    same_as: list[str] = Field(default_factory=list)
    ids: dict[str, str] = Field(default_factory=dict)

    @field_validator("id", "name")
    @classmethod
    def _non_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Quantity id and name must be non-empty")
        return v

    @computed_field
    @property
    def uri(self) -> str:
        return f"https://w3id.org/codata/quantities/{self.id}"


class ConstantValueModel(BaseModel):
    """A versioned numerical value and standard uncertainty for a constant."""

    version: str
    name: str
    value: str
    value_nist: str | None = None
    value_source: ValueSource = "nist"
    uncertainty: str | None = None
    nist_exponent: int | None = None
    units: str | None = None
    is_exact: bool = False
    is_truncated: bool = False
    is_nist_truncated: bool = False
    adjustment_role: AdjustmentRole | None = None

    @field_validator("version")
    @classmethod
    def _validate_version(cls, v: str) -> str:
        if not isinstance(v, str) or not re.fullmatch(r"\d{4}", v):
            raise ValueError(f"ConstantValue version must be a 4-digit string, got {v!r}")
        return v

    @field_validator("value")
    @classmethod
    def _validate_value(cls, v: str) -> str:
        return _validate_decimal_str(v, "value")

    @field_validator("value_nist")
    @classmethod
    def _validate_value_nist(cls, v: str | None) -> str | None:
        if v is None:
            return None
        return _validate_decimal_str(v, "value_nist")

    @field_validator("uncertainty")
    @classmethod
    def _validate_uncertainty(cls, v: str | None) -> str | None:
        if v is None:
            return None
        cleaned = _validate_decimal_str(v, "uncertainty")
        if Decimal(cleaned) <= 0:
            raise ValueError(f"uncertainty must be strictly positive, got {cleaned!r}")
        return cleaned

    @model_validator(mode="after")
    def _check_exactness_invariant(self) -> ConstantValueModel:
        if self.is_exact and self.uncertainty is not None:
            raise ValueError(
                f"Version {self.version}: exact constant value cannot have uncertainty ({self.uncertainty!r})"
            )
        if not self.is_exact and self.uncertainty is None:
            raise ValueError(f"Version {self.version}: non-exact constant value must specify uncertainty")
        if self.value_source == "computed" and self.value_nist is None:
            raise ValueError(
                f"Version {self.version}: computed constant value must preserve original NIST string in value_nist"
            )
        if self.adjustment_role in {"defining", "computed_exact"} and not self.is_exact:
            raise ValueError(
                f"Version {self.version}: constant value with role {self.adjustment_role!r} must be exact (is_exact=True)"
            )
        if self.adjustment_role in {"adjusted", "computed_derived"} and self.is_exact:
            raise ValueError(
                f"Version {self.version}: constant value with role {self.adjustment_role!r} cannot be exact (is_exact=False)"
            )
        return self

    @computed_field
    @property
    def is_computed(self) -> bool:
        """Return True if this versioned value was computed from an algebraic formula."""
        return self.adjustment_role in {"computed_exact", "computed_derived"}

    @computed_field
    @property
    def significant_digits(self) -> int:
        """Number of significant base-10 digits in `value`."""
        return count_significant_digits(self.value)

    @computed_field
    @property
    def fits_float32(self) -> bool:
        """Return True if IEEE 754 single precision (float32) holds `value` without loss."""
        return check_fits_float32(self.value, is_truncated=self.is_truncated)

    @computed_field
    @property
    def fits_float64(self) -> bool:
        """Return True if IEEE 754 double precision (float64) holds `value` without loss."""
        return check_fits_float64(self.value, is_truncated=self.is_truncated)

    @computed_field
    @property
    def recommended_numeric_type(self) -> Literal["float32", "float64", "decimal"]:
        """Smallest standard numeric type capable of holding `value` without loss."""
        return get_recommended_numeric_type(self.value, is_truncated=self.is_truncated)


class ConstantModel(BaseModel):
    """A fundamental physical constant with multilingual labels, formulas, external IDs, and historical values."""

    id: str
    quantity_id: str
    unit_id: str | None = None
    unit_nist: str | None = None
    name: str
    name_fr: str | None = None
    name_bipm_en: str | None = None
    name_bipm_fr: str | None = None
    symbol_tex: str | None = None
    formula: str | None = None
    formula_tex: str | None = None
    ids: dict[str, str] = Field(default_factory=dict)
    values: list[ConstantValueModel] = Field(default_factory=list)

    @field_validator("id", "quantity_id", "name")
    @classmethod
    def _non_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Constant id, quantity_id, and name must be non-empty")
        return v

    @field_validator("formula")
    @classmethod
    def _check_formula(cls, v: str | None) -> str | None:
        if v is None:
            return None
        cleaned = v.strip()
        if not cleaned:
            return None
        validate_formula_syntax(cleaned)
        return cleaned

    @computed_field
    @property
    def derived_from(self) -> list[str]:
        """Sorted list of Constant.id dependencies extracted from `formula`."""
        return extract_dependencies(self.formula)

    @property
    def current_adjustment_role(self) -> AdjustmentRole | None:
        """Adjustment role in the current official CODATA release (2022), or None if deprecated."""
        v = self.value_for_version("2022")
        return v.adjustment_role if v else None

    @property
    def adjustment_role(self) -> AdjustmentRole | None:
        """Backward-compatible access to the latest adjustment role."""
        return self.current_adjustment_role

    @property
    def is_computed(self) -> bool:
        """Return True if this constant has an algebraic formula."""
        return bool(self.formula)

    @computed_field
    @property
    def is_base(self) -> bool:
        return self.id == self.quantity_id

    @computed_field
    @property
    def is_qudt(self) -> bool:
        return bool(self.ids.get("QUDT"))

    @computed_field
    @property
    def qudt_url(self) -> str | None:
        qid = self.ids.get("QUDT")
        return f"https://qudt.org/vocab/constant/{qid}.html" if qid else None

    @computed_field
    @property
    def si_url(self) -> str | None:
        sid = self.ids.get("SI")
        return f"https://si-digital-framework.org/constants/{sid}" if sid else None

    @computed_field
    @property
    def nist_url(self) -> str | None:
        nid = self.ids.get("NIST")
        return f"https://pml.nist.gov/cgi-bin/cuu/Value?{nid}" if nid else None

    @property
    def version_ids(self) -> list[str]:
        return [v.version for v in self.values]

    @computed_field
    @property
    def version_count(self) -> int:
        return len(self.values)

    def value_for_version(self, version_id: str) -> ConstantValueModel | None:
        """Return the ConstantValueModel matching the given release year, if present."""
        for v in self.values:
            if v.version == version_id:
                return v
        return None


class DatasetModel(BaseModel):
    """Complete CODATA DRUM dataset loaded from modular YAML files."""

    schema_version: str = "0.4.0"
    versions: list[VersionModel] = Field(default_factory=list)
    units: list[UnitModel] = Field(default_factory=list)
    concepts: list[ConceptModel] = Field(default_factory=list)
    quantities: list[QuantityModel] = Field(default_factory=list)
    constants: list[ConstantModel] = Field(default_factory=list)

    def latest_version_id(self) -> str:
        """Return the newest CODATA release version ID (e.g., '2022')."""
        return max((v.id for v in self.versions), default="2022")

    def quantity_ids(self) -> set[str]:
        """Return all Quantity IDs (used to compute Concept.is_quantity dynamically)."""
        return {q.id for q in self.quantities}

    def quantity_constant_counts(self) -> dict[str, int]:
        """Return count of constants linked to each Quantity ID."""
        counts: dict[str, int] = {q.id: 0 for q in self.quantities}
        for const in self.constants:
            counts[const.quantity_id] = counts.get(const.quantity_id, 0) + 1
        return counts

    def unit_constant_counts(self) -> dict[str, int]:
        """Return count of constants using each Unit ID."""
        counts: dict[str, int] = {u.id: 0 for u in self.units}
        for const in self.constants:
            if const.unit_id:
                counts[const.unit_id] = counts.get(const.unit_id, 0) + 1
        return counts

    def is_deprecated(self, constant: ConstantModel) -> bool:
        """Return True if a constant lacks a value in the latest CODATA release."""
        latest = self.latest_version_id()
        return constant.value_for_version(latest) is None

    def deprecated_ids(self) -> list[str]:
        """Return sorted IDs of constants discontinued before the latest CODATA release."""
        return sorted(c.id for c in self.constants if self.is_deprecated(c))

    def to_legacy_json(self) -> dict[str, Any]:
        """Serialize the dataset to the legacy utils/codata_constants.json structure."""
        q_ids = self.quantity_ids()

        concepts_out: list[dict[str, Any]] = []
        for concept in sorted(self.concepts, key=lambda c: c.id):
            c_dict: dict[str, Any] = {
                "type": "Concept",
                "id": concept.id,
                "ids": dict(concept.ids),
                "name": concept.name,
                "is_quantity": concept.id in q_ids,
                "is_ratio": concept.is_ratio,
                "is_relationship": concept.is_relationship,
                "broader": list(concept.broader),
                "groups": list(concept.groups),
                "parts": concept.effective_parts,
                "related": list(concept.related),
                "same_as": list(concept.same_as),
            }
            if concept.name_fr:
                c_dict["name_fr"] = concept.name_fr
            if concept.definition:
                c_dict["definition"] = concept.definition
            if concept.definition_fr:
                c_dict["definition_fr"] = concept.definition_fr
            concepts_out.append(c_dict)

        units_out: list[dict[str, Any]] = []
        for unit in sorted(self.units, key=lambda u: u.id):
            u_dict: dict[str, Any] = {
                "type": "Unit",
                "id": unit.id,
            }
            if unit.display_name:
                u_dict["name"] = unit.display_name
            if unit.si_expression:
                u_dict["si_expression"] = unit.si_expression
            if unit.wikipedia:
                u_dict["wikipedia"] = unit.wikipedia
            u_dict["ids"] = dict(unit.ids)
            units_out.append(u_dict)

        versions_out: list[dict[str, Any]] = []
        for version in sorted(self.versions, key=lambda v: v.id, reverse=True):
            v_dict: dict[str, Any] = {
                "type": "Version",
                "id": version.id,
                "published": version.published.isoformat(),
            }
            if version.description:
                v_dict["description"] = version.description
            versions_out.append(v_dict)

        consts_by_qty: dict[str, list[ConstantModel]] = {}
        for const in sorted(self.constants, key=lambda c: c.id):
            consts_by_qty.setdefault(const.quantity_id, []).append(const)

        quantities_out: list[dict[str, Any]] = []
        for qty in sorted(self.quantities, key=lambda q: q.id):
            q_consts: list[dict[str, Any]] = []
            for const in consts_by_qty.get(qty.id, []):
                vals_out: list[dict[str, Any]] = []
                for val in sorted(const.values, key=lambda x: x.version, reverse=True):
                    val_dict: dict[str, Any] = {
                        "type": "ConstantVersion",
                        "ids": {},
                        "version": val.version,
                        "name": val.name,
                        "value": val.value,
                        "value_source": val.value_source,
                        "uncertainty": val.uncertainty,
                    }
                    if val.value_nist is not None:
                        val_dict["value_nist"] = val.value_nist
                    if val.nist_exponent is not None:
                        val_dict["nist_exponent"] = val.nist_exponent
                    if val.units:
                        val_dict["units"] = val.units
                    val_dict["is_exact"] = val.is_exact
                    val_dict["is_truncated"] = val.is_truncated
                    val_dict["is_nist_truncated"] = val.is_nist_truncated
                    val_dict["significant_digits"] = val.significant_digits
                    val_dict["fits_float32"] = val.fits_float32
                    val_dict["fits_float64"] = val.fits_float64
                    val_dict["recommended_numeric_type"] = val.recommended_numeric_type
                    if val.adjustment_role:
                        val_dict["adjustment_role"] = val.adjustment_role
                    val_dict["is_computed"] = val.is_computed
                    vals_out.append(val_dict)

                const_dict: dict[str, Any] = {
                    "type": "Constant",
                    "id": const.id,
                    "ids": dict(const.ids),
                    "name": const.name,
                }
                if const.name_fr:
                    const_dict["name_fr"] = const.name_fr
                if const.name_bipm_en:
                    const_dict["name_bipm_en"] = const.name_bipm_en
                if const.name_bipm_fr:
                    const_dict["name_bipm_fr"] = const.name_bipm_fr
                if const.symbol_tex:
                    const_dict["symbol_tex"] = const.symbol_tex
                if const.formula:
                    const_dict["formula"] = const.formula
                if const.formula_tex:
                    const_dict["formula_tex"] = const.formula_tex
                if const.derived_from:
                    const_dict["derived_from"] = const.derived_from
                if const.unit_id:
                    const_dict["unit_id"] = const.unit_id
                const_dict["values"] = vals_out
                q_consts.append(const_dict)

            qty_dict: dict[str, Any] = {
                "type": "Quantity",
                "id": qty.id,
                "ids": dict(qty.ids),
                "name": qty.name,
            }
            if qty.definition:
                qty_dict["definition"] = qty.definition
            if qty.same_as:
                qty_dict["same_as"] = list(qty.same_as)
            if qty.has_parts:
                qty_dict["has_parts"] = list(qty.has_parts)
            if qty.is_ratio:
                qty_dict["is_ratio"] = True
            if qty.is_relationship:
                qty_dict["is_relationship"] = True
            qty_dict["constants"] = q_consts
            quantities_out.append(qty_dict)

        return {
            "version": self.schema_version,
            "concepts": concepts_out,
            "units": units_out,
            "versions": versions_out,
            "quantities": quantities_out,
        }
