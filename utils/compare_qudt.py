#!/usr/bin/env python3
"""
QUDT vs CODATA Constants Comparison Utility

Compares physical constant values published by QUDT in Turtle format (e.g. https://qudt.org/3.5.0/vocab/constant)
with the official values in codata_constants.json.

Side-by-side comparison highlights if QUDT values are outdated compared to CODATA 2022
and identifies which historical CODATA version QUDT matches.
"""

import argparse
import csv
import json
import logging
import math
import re
import urllib.request
from collections import defaultdict
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

import rdflib

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

QUDT_TTL_DEFAULT_URL = "https://qudt.org/3.5.0/vocab/constant"
DEFAULT_CACHE_DIR = Path(__file__).parent
DEFAULT_CODATA_JSON = Path(__file__).parent / "codata_constants.json"

HISTORICAL_VERSIONS = ["2022", "2018", "2014", "2010", "2006", "2002", "1998"]

# RDF Namespaces
QUDT_NS = rdflib.Namespace("http://qudt.org/schema/qudt/")
CONST_NS = rdflib.Namespace("http://qudt.org/vocab/constant/")
RDFS_NS = rdflib.Namespace("http://www.w3.org/2000/01/rdf-schema#")
XSD_NS = rdflib.Namespace("http://www.w3.org/2001/XMLSchema#")
SKOS_NS = rdflib.Namespace("http://www.w3.org/2004/02/skos/core#")
DCTERMS_NS = rdflib.Namespace("http://purl.org/dc/terms/")
OWL_NS = rdflib.Namespace("http://www.w3.org/2002/07/owl#")
VAEM_NS = rdflib.Namespace("http://www.linkedmodel.org/schema/vaem#")


def fetch_and_cache_qudt_ttl(url: str, cache_dir: Path, force_refresh: bool = False) -> Path:
    """
    Downloads and caches the QUDT Turtle file locally.
    """
    cache_dir.mkdir(parents=True, exist_ok=True)
    # Generate cache filename based on URL
    filename = url.rstrip("/").split("/")[-1]
    if not filename.endswith(".ttl"):
        filename = f"qudt_constants_{filename}.ttl"
    cache_file = cache_dir / filename

    if cache_file.exists() and not force_refresh:
        logging.info(f"Using cached QUDT Turtle file: {cache_file}")
        return cache_file

    logging.info(f"Fetching QUDT Turtle file from {url}...")
    req = urllib.request.Request(
        url,
        headers={
            "Accept": "text/turtle, application/x-turtle, text/plain, */*",
            "User-Agent": "CODATA-DRUM-Comparison-Utility/1.0",
        },
    )
    with urllib.request.urlopen(req) as response:
        content = response.read()

    with open(cache_file, "wb") as f:
        f.write(content)
    logging.info(f"Successfully cached QUDT Turtle file to {cache_file} ({len(content)} bytes)")

    return cache_file


def parse_qudt_graph(ttl_path: Path) -> tuple[dict, list[dict]]:
    """
    Parses the QUDT Turtle file using rdflib and extracts PhysicalConstant definitions.
    Returns (qudt_constants_map, multi_entry_groups).
    """
    logging.info(f"Parsing QUDT Turtle data from {ttl_path}...")
    g = rdflib.Graph()
    g.parse(ttl_path, format="turtle")

    qudt_constants = {}
    val_node_to_subjects = defaultdict(list)

    for subject in g.subjects(rdflib.RDF.type, QUDT_NS.PhysicalConstant):
        subject_str = str(subject)
        subj_local_id = subject_str.replace(str(CONST_NS), "").split("/")[-1]

        label = g.value(subject, RDFS_NS.label)
        val_uri = g.value(subject, QUDT_NS.quantityValue)

        val_str = None
        unc_str = None
        unit_str = None
        val_local_id = None

        if val_uri:
            v_str = str(val_uri).replace(str(CONST_NS), "").split("/")[-1]
            val_local_id = v_str[6:] if v_str.startswith("Value_") else v_str

            val_node = g.value(val_uri, QUDT_NS.value) or g.value(val_uri, QUDT_NS.valueSN)
            unc_node = g.value(val_uri, QUDT_NS.standardUncertainty) or g.value(val_uri, QUDT_NS.standardUncertaintySN)
            unit_node = g.value(val_uri, QUDT_NS.hasUnit)

            val_str = str(val_node) if val_node is not None else None
            unc_str = str(unc_node) if unc_node is not None else None
            unit_str = str(unit_node).replace("http://qudt.org/vocab/unit/", "") if unit_node else None

            val_node_to_subjects[val_local_id].append((subj_local_id, str(label) if label else subj_local_id))

        item = {
            "uri": subject_str,
            "id": subj_local_id,
            "val_id": val_local_id,
            "label": str(label) if label else subj_local_id,
            "value": val_str,
            "uncertainty": unc_str,
            "unit": unit_str,
            "has_quantity_value": val_uri is not None,
            "aliases": [subj_local_id],
        }

        # Primary key: Subject local ID (e.g., ReducedPlanckConstant)
        if subj_local_id not in qudt_constants:
            qudt_constants[subj_local_id] = item

        # Secondary key: Value node local ID (e.g., PlanckConstantOver2Pi)
        if val_local_id and val_local_id not in qudt_constants:
            qudt_constants[val_local_id] = item

    # Attach aliases to items
    for val_id, subjs in val_node_to_subjects.items():
        aliases = [s[0] for s in subjs]
        if val_id in qudt_constants:
            qudt_constants[val_id]["aliases"] = aliases
        for subj_id, _ in subjs:
            if subj_id in qudt_constants:
                qudt_constants[subj_id]["aliases"] = aliases

    multi_entry_alias_groups = []
    for val_id, subjs in sorted(val_node_to_subjects.items()):
        if len(subjs) > 1:
            primary = None
            for s_id, s_lbl in subjs:
                if s_id == val_id:
                    primary = (s_id, s_lbl)
                    break

            if not primary:
                kpa_match = [s for s in subjs if s[0].endswith("KPa")]
                if kpa_match:
                    primary = kpa_match[0]
                else:
                    primary = subjs[0]

            aliases = [s for s in subjs if s[0] != primary[0]]
            multi_entry_alias_groups.append({
                "val_id": val_id,
                "primary": primary,
                "aliases": aliases,
            })

    logging.info(f"Extracted QUDT physical constants ({len(multi_entry_alias_groups)} multi-entry alias groups).")
    return qudt_constants, multi_entry_alias_groups


def parse_codata_json(json_path: Path) -> tuple[dict, list]:
    """
    Parses codata_constants.json and extracts constants keyed by QUDT ID.
    Returns (qudt_map, all_constants_list).
    """
    logging.info(f"Loading CODATA constants JSON from {json_path}...")
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    codata_qudt_map = {}
    all_constants = []

    for quantity in data.get("quantities", []):
        q_id = quantity.get("id")
        for constant in quantity.get("constants", []):
            c_id = constant.get("id")
            c_name = constant.get("name")
            qudt_id = constant.get("ids", {}).get("QUDT")
            values = constant.get("values", [])

            # Create version lookup dict for values
            ver_dict = {}
            for v in values:
                ver_dict[v.get("version")] = v

            item = {
                "quantity_id": q_id,
                "constant_id": c_id,
                "name": c_name,
                "qudt_id": qudt_id,
                "values": values,
                "versions": ver_dict,
                "latest_value": values[0] if values else None,
            }

            all_constants.append(item)
            if qudt_id:
                codata_qudt_map[qudt_id] = item

    logging.info(f"Loaded {len(all_constants)} CODATA constants ({len(codata_qudt_map)} mapped to QUDT IDs).")
    return codata_qudt_map, all_constants


def compare_values(val1_str: str | None, val2_str: str | None, rel_tol: float = 1e-8, abs_tol: float = 1e-15) -> bool:
    """
    Compares two numerical values represented as strings.
    """
    if val1_str is None or val2_str is None:
        return val1_str == val2_str

    try:
        f1 = float(val1_str)
        f2 = float(val2_str)
        return math.isclose(f1, f2, rel_tol=rel_tol, abs_tol=abs_tol)
    except (ValueError, TypeError):
        return val1_str.strip() == val2_str.strip()


def find_matching_historical_version(qudt_val_str: str | None, codata_values: list) -> str | None:
    """
    Finds which historical CODATA release version matches the given QUDT value.
    """
    if not qudt_val_str or not codata_values:
        return None

    for v_entry in codata_values:
        c_val = v_entry.get("value")
        if compare_values(qudt_val_str, c_val):
            return v_entry.get("version")
    return None


def normalize_str(s: str | None) -> str:
    """
    Normalizes string for fuzzy pattern matching (lowercased, alphanumeric only, dot/kpa normalized).
    """
    if not s:
        return ""
    s = s.lower().replace("dot", "").replace("kilopa", "kpa")
    return re.sub(r"[^a-z0-9]", "", s)


def run_comparison(codata_map: dict, qudt_map: dict, all_codata_constants: list[dict] | None = None, target_version: str = "2022") -> list[dict]:
    """
    Performs side-by-side comparison of QUDT vs CODATA constants using dual-key crosswalk
    and a dynamic runtime alias detection engine.
    """
    results = []
    processed_qudt_keys = set()
    matched_qudt_uris = set()

    # Build runtime index of all CODATA release values for dynamic numerical matching
    codata_values_idx: list[tuple[float, dict, str]] = []
    if all_codata_constants:
        for c_item in all_codata_constants:
            for v_entry in c_item.get("values", []):
                val_str = v_entry.get("value")
                if val_str:
                    try:
                        fval = float(val_str)
                        codata_values_idx.append((fval, c_item, v_entry.get("version", "2022")))
                    except ValueError:
                        pass

    # 1. Process items mapped directly in CODATA JSON
    for qudt_id, c_data in codata_map.items():
        processed_qudt_keys.add(qudt_id)

        target_codata_entry = c_data["versions"].get(target_version) or c_data["latest_value"]
        codata_val_str = target_codata_entry.get("value") if target_codata_entry else None
        codata_unc_str = target_codata_entry.get("uncertainty") if target_codata_entry else None
        codata_is_exact = target_codata_entry.get("is_exact", False) if target_codata_entry else False

        qudt_entry = qudt_map.get(qudt_id)

        if not qudt_entry:
            results.append({
                "qudt_id": qudt_id,
                "constant_id": c_data["constant_id"],
                "name": c_data["name"],
                "status": "MISSING_IN_QUDT",
                "qudt_val": None,
                "qudt_unc": None,
                "codata_val": codata_val_str,
                "codata_unc": codata_unc_str,
                "codata_is_exact": codata_is_exact,
                "matched_version": None,
                "qudt_aliases": [qudt_id],
                "details": "QUDT ID referenced in CODATA JSON, but entity missing in QUDT TTL.",
            })
            continue

        matched_qudt_uris.add(qudt_entry["uri"])
        if qudt_entry.get("id"):
            processed_qudt_keys.add(qudt_entry["id"])
        if qudt_entry.get("val_id"):
            processed_qudt_keys.add(qudt_entry["val_id"])

        qudt_val_str = qudt_entry["value"]
        qudt_unc_str = qudt_entry["uncertainty"]
        qudt_aliases = qudt_entry.get("aliases", [qudt_id])

        if not qudt_entry["has_quantity_value"] or qudt_val_str is None:
            results.append({
                "qudt_id": qudt_id,
                "constant_id": c_data["constant_id"],
                "name": c_data["name"],
                "status": "MISSING_VALUE_IN_QUDT",
                "qudt_val": None,
                "qudt_unc": None,
                "codata_val": codata_val_str,
                "codata_unc": codata_unc_str,
                "codata_is_exact": codata_is_exact,
                "matched_version": None,
                "qudt_aliases": qudt_aliases,
                "details": "QUDT constant exists, but has no qudt:quantityValue / qudt:value node.",
            })
            continue

        # Compare values against target CODATA version (e.g. 2022)
        is_match = compare_values(qudt_val_str, codata_val_str)

        if is_match:
            results.append({
                "qudt_id": qudt_id,
                "constant_id": c_data["constant_id"],
                "name": c_data["name"],
                "status": "UP_TO_DATE",
                "qudt_val": qudt_val_str,
                "qudt_unc": qudt_unc_str,
                "codata_val": codata_val_str,
                "codata_unc": codata_unc_str,
                "codata_is_exact": codata_is_exact,
                "matched_version": target_version,
                "qudt_aliases": qudt_aliases,
                "details": f"Matches CODATA {target_version} value.",
            })
        else:
            # Value differs! Search historical releases
            matched_hist_ver = find_matching_historical_version(qudt_val_str, c_data["values"])
            details = (
                f"QUDT value differs from CODATA {target_version} ({codata_val_str}). "
                + (f"Matches historical CODATA {matched_hist_ver}." if matched_hist_ver else "Does not match any known CODATA release.")
            )
            results.append({
                "qudt_id": qudt_id,
                "constant_id": c_data["constant_id"],
                "name": c_data["name"],
                "status": "OUTDATED",
                "qudt_val": qudt_val_str,
                "qudt_unc": qudt_unc_str,
                "codata_val": codata_val_str,
                "codata_unc": codata_unc_str,
                "codata_is_exact": codata_is_exact,
                "matched_version": matched_hist_ver,
                "qudt_aliases": qudt_aliases,
                "details": details,
            })

    # 2. Process remaining QUDT constants using DYNAMIC RUNTIME ALIAS DETECTION ENGINE
    processed_uris = set()
    for qudt_key, qudt_entry in qudt_map.items():
        uri = qudt_entry["uri"]
        subj_id = qudt_entry["id"]
        val_id = qudt_entry["val_id"]
        val_str = qudt_entry["value"]
        label = qudt_entry["label"]

        if uri in matched_qudt_uris or uri in processed_uris or qudt_key in processed_qudt_keys:
            continue
        processed_uris.add(uri)

        # Dynamic Alias Detection Algorithm (Zero hardcoded aliases)
        matched_c_info = None
        match_reason = None

        # Layer 1: Shared Value Node Match
        if val_id and val_id in codata_map:
            matched_c_info = codata_map[val_id]
            match_reason = f"QUDT value node (Value_{val_id}) matches CODATA constant '{matched_c_info['constant_id']}'"

        # Layer 2: Dynamic Normalized ID / Name Match
        if not matched_c_info and all_codata_constants:
            norm_subj = normalize_str(subj_id)
            norm_lbl = normalize_str(label)
            for c_cand in all_codata_constants:
                norm_cid = normalize_str(c_cand["constant_id"])
                norm_cname = normalize_str(c_cand["name"])
                if norm_subj == norm_cid or norm_subj == norm_cname or norm_lbl == norm_cid or norm_lbl == norm_cname:
                    matched_c_info = c_cand
                    match_reason = f"Normalized name match with CODATA constant '{c_cand['constant_id']}'"
                    break

        # Layer 3: Dynamic Numerical Value Match across all CODATA releases
        if not matched_c_info and val_str and codata_values_idx:
            try:
                f_qudt = float(val_str)
                for f_codata, c_cand, ver in codata_values_idx:
                    if math.isclose(f_qudt, f_codata, rel_tol=1e-7, abs_tol=1e-15):
                        matched_c_info = c_cand
                        match_reason = f"Numerical value match ({val_str}) with CODATA constant '{c_cand['constant_id']}' ({ver} release)"
                        break
            except ValueError:
                pass

        if matched_c_info:
            target_val = matched_c_info.get("latest_value", {}).get("value") if matched_c_info.get("latest_value") else None
            results.append({
                "qudt_id": subj_id,
                "constant_id": matched_c_info["constant_id"],
                "name": f"{label} (Alias for {matched_c_info['name']})",
                "status": "QUDT_ALIAS",
                "qudt_val": val_str,
                "qudt_unc": qudt_entry["uncertainty"],
                "codata_val": target_val,
                "codata_unc": None,
                "codata_is_exact": False,
                "matched_version": None,
                "qudt_aliases": qudt_entry.get("aliases", [subj_id]),
                "details": f"QUDT Subject Entity Alias dynamically matched: {match_reason}.",
            })
        else:
            results.append({
                "qudt_id": subj_id,
                "constant_id": None,
                "name": label,
                "status": "UNMAPPED_IN_CODATA",
                "qudt_val": val_str,
                "qudt_unc": qudt_entry["uncertainty"],
                "codata_val": None,
                "codata_unc": None,
                "codata_is_exact": False,
                "matched_version": None,
                "qudt_aliases": qudt_entry.get("aliases", [subj_id]),
                "details": "Mathematical constant or entity not present in CODATA constants model.",
            })

    return results


def format_terminal_output(results: list[dict], multi_entry_groups: list[dict] | None = None, outdated_only: bool = False) -> str:
    """
    Renders terminal side-by-side table and multi-entry section.
    """
    filtered = [r for r in results if not outdated_only or r["status"] == "OUTDATED"]

    lines: list[str] = []
    lines.append("=" * 125)
    lines.append(f"{'QUDT ID / CONSTANT NAME':<40} | {'STATUS':<12} | {'QUDT VALUE':<22} | {'CODATA 2022 VALUE':<22} | {'MATCHED VER':<11}")
    lines.append("=" * 125)

    for r in filtered:
        name_disp = (r["qudt_id"][:38] + "..") if len(r["qudt_id"]) > 40 else r["qudt_id"]
        status = r["status"]
        q_val = (r["qudt_val"][:20] + "..") if r["qudt_val"] and len(r["qudt_val"]) > 22 else (r["qudt_val"] or "N/A")
        c_val = (r["codata_val"][:20] + "..") if r["codata_val"] and len(r["codata_val"]) > 22 else (r["codata_val"] or "N/A")
        m_ver = r["matched_version"] or "None"

        lines.append(f"{name_disp:<40} | {status:<12} | {q_val:<22} | {c_val:<22} | {m_ver:<11}")

    lines.append("=" * 125)

    # Summary
    total = len(results)
    up_to_date = sum(1 for r in results if r["status"] == "UP_TO_DATE")
    outdated = sum(1 for r in results if r["status"] == "OUTDATED")
    aliases_count = sum(1 for r in results if r["status"] == "QUDT_ALIAS")
    missing_q = sum(1 for r in results if r["status"] in ("MISSING_IN_QUDT", "MISSING_VALUE_IN_QUDT"))
    unmapped = sum(1 for r in results if r["status"] == "UNMAPPED_IN_CODATA")

    lines.append("\nSUMMARY STATISTICS:")
    lines.append(f"  Total Constants Evaluated: {total}")
    lines.append(f"  Up To Date (CODATA 2022): {up_to_date} ({up_to_date/total*100:.1f}%)")
    lines.append(f"  Outdated (Differs from 2022): {outdated} ({outdated/total*100:.1f}%)")
    lines.append(f"  QUDT Entity Aliases (Mapped): {aliases_count}")
    lines.append(f"  Missing / No Value in QUDT: {missing_q}")
    lines.append(f"  Truly Unmapped in CODATA:  {unmapped}")

    # Historical breakdown for outdated
    hist_counts = {}
    for r in results:
        if r["status"] == "OUTDATED":
            ver = r["matched_version"] or "Unknown/Custom"
            hist_counts[ver] = hist_counts.get(ver, 0) + 1

    lines.append("\nOUTDATED QUDT CONSTANTS BREAKDOWN BY MATCHED CODATA RELEASE:")
    for ver in sorted(hist_counts.keys(), reverse=True):
        lines.append(f"  CODATA {ver}: {hist_counts[ver]} constants")

    # Multi-entry / Aliases section (showing aliases only)
    if multi_entry_groups:
        lines.append("\nQUDT CONSTANTS WITH SUBJECT ALIASES (ALIAS SUBJECTS ONLY):")
        lines.append("-" * 125)
        lines.append(f"{'PRIMARY QUDT CONSTANT (EXACT MATCH)':<40} | {'QUDT SUBJECT ALIASES ONLY (EXCLUDING PRIMARY)'}")
        lines.append("-" * 125)
        for g in multi_entry_groups:
            p_id, p_lbl = g["primary"]
            aliases_formatted = " ; ".join(f"constant:{a[0]} ({a[1]!r})" for a in g["aliases"])
            lines.append(f"constant:{p_id:<31} | {aliases_formatted}")

    lines.append("\nTIP: Run with `--export-ttl` (or `--update-qudt`) to produce the updated Turtle file with documented changes.")

    return "\n".join(lines)


def format_markdown_output(results: list[dict], multi_entry_groups: list[dict] | None = None, outdated_only: bool = False) -> str:
    """
    Renders Markdown report with alias-only QUDT section.
    """
    filtered = [r for r in results if not outdated_only or r["status"] == "OUTDATED"]

    total = len(results)
    up_to_date = sum(1 for r in results if r["status"] == "UP_TO_DATE")
    outdated = sum(1 for r in results if r["status"] == "OUTDATED")
    aliases_count = sum(1 for r in results if r["status"] == "QUDT_ALIAS")
    missing_q = sum(1 for r in results if r["status"] in ("MISSING_IN_QUDT", "MISSING_VALUE_IN_QUDT"))
    unmapped = sum(1 for r in results if r["status"] == "UNMAPPED_IN_CODATA")

    lines: list[str] = []
    lines.append("# QUDT vs CODATA Physical Constants Comparison Report\n")
    lines.append("## Summary Statistics\n")
    lines.append(f"- **Total Evaluated**: {total}")
    lines.append(f"- **Up to Date (CODATA 2022)**: {up_to_date} ({up_to_date/total*100:.1f}%)")
    lines.append(f"- **Outdated QUDT Values**: {outdated} ({outdated/total*100:.1f}%)")
    lines.append(f"- **QUDT Subject Aliases (Mapped)**: {aliases_count}")
    lines.append(f"- **Missing in QUDT**: {missing_q}")
    lines.append(f"- **Truly Unmapped in CODATA**: {unmapped}\n")

    lines.append("### Outdated Constants Breakdown\n")
    hist_counts = {}
    for r in results:
        if r["status"] == "OUTDATED":
            ver = r["matched_version"] or "Unknown/Custom"
            hist_counts[ver] = hist_counts.get(ver, 0) + 1

    for ver in sorted(hist_counts.keys(), reverse=True):
        lines.append(f"- **CODATA {ver}**: {hist_counts[ver]} constants")

    if multi_entry_groups:
        lines.append("\n## QUDT Subject Aliases\n")
        lines.append("The following primary QUDT constants have additional subject entity aliases defined in the QUDT Turtle vocabulary (showing aliases only, excluding exact match primary entities):\n")
        lines.append("| Primary QUDT Constant (Exact Match) | Alias Subject ID | Alias Label / Preferred Name |")
        lines.append("|---|---|---|")
        for g in multi_entry_groups:
            p_id, p_lbl = g["primary"]
            for a_id, a_lbl in g["aliases"]:
                lines.append(f"| `{p_id}` | `{a_id}` | {a_lbl} |")

    lines.append("\n## Comparison Table\n")
    lines.append("| QUDT ID | Name | Status | QUDT Value | CODATA 2022 Value | Matched CODATA Version | Aliases / Entities |")
    lines.append("|---|---|---|---|---|---|---|")

    for r in filtered:
        status_badge = f"`{r['status']}`"
        if r['status'] == 'OUTDATED':
            status_badge = "⚠️ `OUTDATED`"
        elif r['status'] == 'UP_TO_DATE':
            status_badge = "✅ `UP_TO_DATE`"
        elif r['status'] == 'QUDT_ALIAS':
            status_badge = "🔗 `QUDT_ALIAS`"

        q_val = r["qudt_val"] if r["qudt_val"] is not None else "*N/A*"
        c_val = r["codata_val"] if r["codata_val"] is not None else "*N/A*"
        m_ver = f"CODATA {r['matched_version']}" if r["matched_version"] else "*None*"
        aliases_str = ", ".join(f"`{a}`" for a in r.get("qudt_aliases", [])) if len(r.get("qudt_aliases", [])) > 1 else "-"

        lines.append(f"| `{r['qudt_id']}` | {r['name']} | {status_badge} | `{q_val}` | `{c_val}` | {m_ver} | {aliases_str} |")

    return "\n".join(lines)


def format_html_output(results: list[dict], multi_entry_groups: list[dict] | None = None, outdated_only: bool = False) -> str:
    """
    Renders standalone interactive HTML report with alias-only section.
    """
    filtered = [r for r in results if not outdated_only or r["status"] == "OUTDATED"]

    total = len(results)
    up_to_date = sum(1 for r in results if r["status"] == "UP_TO_DATE")
    outdated = sum(1 for r in results if r["status"] == "OUTDATED")
    aliases_count = sum(1 for r in results if r["status"] == "QUDT_ALIAS")
    missing_q = sum(1 for r in results if r["status"] in ("MISSING_IN_QUDT", "MISSING_VALUE_IN_QUDT"))
    unmapped = sum(1 for r in results if r["status"] == "UNMAPPED_IN_CODATA")

    rows_html = []
    for r in filtered:
        status_cls = "status-outdated" if r["status"] == "OUTDATED" else ("status-match" if r["status"] == "UP_TO_DATE" else ("status-alias" if r["status"] == "QUDT_ALIAS" else "status-other"))
        status_label = r["status"]
        if r["status"] == "OUTDATED":
            status_label = "⚠️ OUTDATED"
        elif r["status"] == "UP_TO_DATE":
            status_label = "✅ UP TO DATE"
        elif r["status"] == "QUDT_ALIAS":
            status_label = "🔗 QUDT ALIAS"

        q_val = r["qudt_val"] or "N/A"
        c_val = r["codata_val"] or "N/A"
        m_ver = f"CODATA {r['matched_version']}" if r["matched_version"] else "None"
        aliases_html = "<br>".join(f"<code>{a}</code>" for a in r.get("qudt_aliases", [])) if len(r.get("qudt_aliases", [])) > 1 else "-"

        rows_html.append(f"""
        <tr class="{status_cls}">
            <td><code>{r['qudt_id']}</code></td>
            <td>{r['name']}</td>
            <td><span class="badge {status_cls}">{status_label}</span></td>
            <td><code>{q_val}</code></td>
            <td><code>{c_val}</code></td>
            <td><span class="version-tag">{m_ver}</span></td>
            <td>{aliases_html}</td>
        </tr>
        """)

    multi_html = ""
    if multi_entry_groups:
        m_rows = []
        for g in multi_entry_groups:
            p_id, p_lbl = g["primary"]
            for a_id, a_lbl in g["aliases"]:
                m_rows.append(f"<tr><td><code>{p_id}</code></td><td><code>{a_id}</code></td><td>{a_lbl}</td></tr>")

        multi_html = f"""
        <h2>QUDT Subject Aliases</h2>
        <p>The following primary QUDT constants have additional subject entity aliases defined in the QUDT Turtle vocabulary (showing aliases only, excluding exact match primary entities):</p>
        <table style="margin-bottom: 32px;">
            <thead>
                <tr>
                    <th>Primary QUDT Constant (Exact Match)</th>
                    <th>Alias Subject ID</th>
                    <th>Alias Label / Preferred Name</th>
                </tr>
            </thead>
            <tbody>
                {"".join(m_rows)}
            </tbody>
        </table>
        """

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>QUDT vs CODATA Physical Constants Comparison</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; margin: 0; padding: 24px; background: #f8fafc; color: #0f172a; }}
        h1, h2 {{ margin-top: 0; font-weight: 700; color: #1e293b; }}
        .stats-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 16px; margin-bottom: 24px; }}
        .stat-card {{ background: white; padding: 20px; border-radius: 12px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); border: 1px solid #e2e8f0; }}
        .stat-card .val {{ font-size: 28px; font-weight: 700; margin-top: 4px; }}
        .stat-card.outdated .val {{ color: #dc2626; }}
        .stat-card.match .val {{ color: #16a34a; }}
        .stat-card.alias .val {{ color: #7c3aed; }}
        table {{ width: 100%; border-collapse: collapse; background: white; border-radius: 12px; overflow: hidden; box-shadow: 0 1px 3px rgba(0,0,0,0.1); border: 1px solid #e2e8f0; }}
        th, td {{ padding: 12px 16px; text-align: left; border-bottom: 1px solid #e2e8f0; font-size: 14px; }}
        th {{ background: #f1f5f9; font-weight: 600; color: #475569; }}
        code {{ font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace; background: #f1f5f9; padding: 2px 6px; border-radius: 4px; font-size: 13px; }}
        .badge {{ padding: 4px 8px; border-radius: 6px; font-size: 12px; font-weight: 600; display: inline-block; }}
        .badge.status-outdated {{ background: #fee2e2; color: #991b1b; }}
        .badge.status-match {{ background: #dcfce7; color: #166534; }}
        .badge.status-alias {{ background: #f3e8ff; color: #6b21a8; }}
        .badge.status-other {{ background: #f1f5f9; color: #475569; }}
        .version-tag {{ background: #e0f2fe; color: #0369a1; padding: 2px 8px; border-radius: 9999px; font-size: 12px; font-weight: 500; }}
    </style>
</head>
<body>
    <h1>QUDT vs CODATA Physical Constants Comparison</h1>
    <div class="stats-grid">
        <div class="stat-card">
            <div>Total Constants</div>
            <div class="val">{total}</div>
        </div>
        <div class="stat-card match">
            <div>Up to Date (CODATA 2022)</div>
            <div class="val">{up_to_date}</div>
        </div>
        <div class="stat-card outdated">
            <div>Outdated QUDT Values</div>
            <div class="val">{outdated}</div>
        </div>
        <div class="stat-card alias">
            <div>QUDT Entity Aliases</div>
            <div class="val">{aliases_count}</div>
        </div>
        <div class="stat-card">
            <div>Missing in QUDT</div>
            <div class="val">{missing_q}</div>
        </div>
        <div class="stat-card">
            <div>Truly Unmapped in CODATA</div>
            <div class="val">{unmapped}</div>
        </div>
    </div>

    {multi_html}

    <h2>Comparison Table</h2>
    <table>
        <thead>
            <tr>
                <th>QUDT ID</th>
                <th>Constant Name</th>
                <th>Status</th>
                <th>QUDT Value</th>
                <th>CODATA 2022 Value</th>
                <th>Matched CODATA Version</th>
                <th>Aliases / Entities</th>
            </tr>
        </thead>
        <tbody>
            {"".join(rows_html)}
        </tbody>
    </table>
</body>
</html>
"""
    return html


def to_decimal_str(val_str: str | None) -> str | None:
    """
    Formats literal string to non-scientific decimal representation without precision loss.
    """
    if val_str is None:
        return None
    try:
        d = Decimal(val_str)
        return f"{d:f}"
    except Exception:
        return val_str


def to_sn_str(val_str: str | None) -> str | None:
    """
    Formats literal string to scientific notation representation without precision loss.
    """
    if val_str is None:
        return None
    try:
        d = Decimal(val_str)
        if d == 0:
            return "0.0e+00"
        return f"{d:e}"
    except Exception:
        return val_str


def generate_export_companion_md(
    output_md_path: Path,
    results: list[dict],
    target_version: str = "2022",
    ttl_file_name: str | None = None,
) -> Path:
    """
    Generates companion Markdown file (e.g., qudt_constants_constant.2022.md) documenting
    all physical constant value and uncertainty updates made during TTL export.
    """
    outdated_results = [r for r in results if r["status"] == "OUTDATED"]
    total = len(results)
    up_to_date = sum(1 for r in results if r["status"] == "UP_TO_DATE")
    aliases_count = sum(1 for r in results if r["status"] == "QUDT_ALIAS")

    ttl_name = ttl_file_name or output_md_path.with_suffix(".ttl").name
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    lines: list[str] = []
    lines.append(f"# QUDT Constants Vocabulary Update Log — CODATA {target_version}\n")
    lines.append(f"- **Target CODATA Release Version**: {target_version}")
    lines.append(f"- **Update Date**: {now_str}")
    lines.append(f"- **Updated Turtle Vocabulary**: [`{ttl_name}`]({ttl_name})")
    lines.append(f"- **Total Constants Evaluated**: {total}")
    lines.append(f"- **Total Constant Values Updated**: {len(outdated_results)}")
    lines.append(f"- **Constants Already Up to Date**: {up_to_date}")
    lines.append(f"- **QUDT Subject Aliases Mapped**: {aliases_count}\n")

    lines.append("## Historical Release Breakdown of Outdated Values\n")
    lines.append("Prior to this synchronization, many constants in QUDT were pinned to older CODATA recommendations:\n")
    hist_counts: dict[str, int] = {}
    for r in outdated_results:
        ver = r["matched_version"] or "Unknown/Custom"
        hist_counts[ver] = hist_counts.get(ver, 0) + 1

    for ver in sorted(hist_counts.keys(), reverse=True):
        lines.append(f"- **CODATA {ver}**: {hist_counts[ver]} constants")

    lines.append("\n## Updated Constant Values & Uncertainties\n")
    lines.append(f"The following {len(outdated_results)} physical constant values in QUDT differed from CODATA {target_version} and were updated to official NIST values:\n")
    lines.append(f"| QUDT ID | Constant Name | Previous QUDT Value | Updated CODATA {target_version} Value | Previous Uncertainty | Updated Uncertainty | Matched Previous Release | Delta (Relative %) |")
    lines.append("|---|---|---|---|---|---|---|---|")

    for r in outdated_results:
        q_id = f"`{r['qudt_id']}`"
        name = r["name"]
        old_val = f"`{r['qudt_val']}`" if r["qudt_val"] else "*N/A*"
        new_val = f"`{to_decimal_str(r['codata_val'])}`" if r["codata_val"] else "*N/A*"
        old_unc = f"`{r['qudt_unc']}`" if r.get("qudt_unc") else "*N/A*"
        new_unc = f"`{to_decimal_str(r['codata_unc'])}`" if r.get("codata_unc") else ("*Exact*" if r.get("codata_is_exact") else "*N/A*")
        matched_ver = f"CODATA {r['matched_version']}" if r["matched_version"] else "*None*"

        # Calculate relative delta percentage
        delta_str = "*N/A*"
        if r.get("qudt_val") and r.get("codata_val"):
            try:
                f_old = float(r["qudt_val"])
                f_new = float(r["codata_val"])
                if f_old != 0:
                    rel_diff = (f_new - f_old) / f_old * 100
                    delta_str = f"{rel_diff:+.6f}%"
            except (ValueError, TypeError, ZeroDivisionError):
                pass

        lines.append(f"| {q_id} | {name} | {old_val} | {new_val} | {old_unc} | {new_unc} | {matched_ver} | {delta_str} |")

    lines.append("\n## Semantic Annotations in Updated Turtle File\n")
    lines.append("Each updated physical constant entity in the exported Turtle file includes machine-readable provenance metadata:\n")
    lines.append("```turtle")
    lines.append("constant:AlphaParticleMassEnergyEquivalentInMeV a qudt:PhysicalConstant ;")
    lines.append(f"    dcterms:modified \"{now_str}\"^^xsd:date ;")
    lines.append("    skos:changeNote \"Updated to CODATA 2022 recommended value: value changed from 3727.379109 to 3727.3794118 (previously matched CODATA 2006).\"@en .")
    lines.append("```\n")

    lines.append("## SPARQL Query Example for Auditing Changes\n")
    lines.append("You can audit all updated constants in the Turtle file using the following SPARQL query:\n")
    lines.append("```sparql")
    lines.append("PREFIX constant: <http://qudt.org/vocab/constant/>")
    lines.append("PREFIX qudt: <http://qudt.org/schema/qudt/>")
    lines.append("PREFIX skos: <http://www.w3.org/2004/02/skos/core#>")
    lines.append("PREFIX dcterms: <http://purl.org/dc/terms/>")
    lines.append("")
    lines.append("SELECT ?constant ?label ?changeNote ?modified WHERE {")
    lines.append("    ?constant a qudt:PhysicalConstant ;")
    lines.append("              rdfs:label ?label ;")
    lines.append("              skos:changeNote ?changeNote ;")
    lines.append("              dcterms:modified ?modified .")
    lines.append("}")
    lines.append("ORDER BY ?constant")
    lines.append("```\n")

    output_md_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_md_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    logging.info(f"Companion update documentation written to {output_md_path}")
    return output_md_path


def export_updated_ttl(
    input_ttl_path: Path,
    output_ttl_path: Path,
    codata_map: dict,
    results: list[dict] | None = None,
    target_version: str = "2022",
    output_md_path: Path | None = None,
) -> tuple[Path, Path]:
    """
    Produces and exports an updated QUDT Turtle file with latest CODATA constant values
    and uncertainties for the specified target release version (e.g., qudt_constants_constant.2022.ttl)
    with the complete list of changes documented:
    1. Human-readable header comment block with changelog and summary at the top of the Turtle file.
    2. Machine-readable RDF annotations (skos:changeNote, dcterms:modified) on each updated constant & value node.
    3. Ontology-level metadata (owl:versionInfo, skos:changeNote, dcterms:modified) on the vocabulary graph.
    4. Comprehensive companion Markdown change document (qudt_constants_constant.2022.md).
    All original RDF properties, metadata, and language labels (@en, @en-US) are preserved intact.
    """
    logging.info(f"Loading QUDT Turtle graph from {input_ttl_path} for updated export...")
    g = rdflib.Graph()
    g.parse(input_ttl_path, format="turtle")

    g.bind("constant", CONST_NS)
    g.bind("qudt", QUDT_NS)
    g.bind("skos", SKOS_NS)
    g.bind("dcterms", DCTERMS_NS)
    g.bind("owl", OWL_NS)
    g.bind("vaem", VAEM_NS)
    g.bind("rdfs", RDFS_NS)
    g.bind("xsd", XSD_NS)

    now_utc = datetime.now(timezone.utc)
    current_date_str = now_utc.strftime("%Y-%m-%d")
    current_iso_datetime = now_utc.strftime("%Y-%m-%dT%H:%M:%SZ")

    # Filter outdated constants from comparison results
    if results is not None:
        outdated_items = [r for r in results if r.get("status") == "OUTDATED"]
    else:
        outdated_items = []

    updated_count = 0
    for r in outdated_items:
        qudt_id = r["qudt_id"]
        val_raw = r.get("codata_val")
        unc_raw = r.get("codata_unc")
        is_exact = r.get("codata_is_exact", False)
        old_val = r.get("qudt_val", "N/A")
        old_unc = r.get("qudt_unc") or ("Exact" if is_exact else "N/A")
        matched_hist = r.get("matched_version")

        subj = CONST_NS[qudt_id]
        val_uri = g.value(subj, QUDT_NS.quantityValue)
        if not val_uri and r.get("val_id"):
            v_node = CONST_NS[f"Value_{r['val_id']}"]
            if (v_node, None, None) in g:
                val_uri = v_node
        if not val_uri:
            v_node = CONST_NS[f"Value_{qudt_id}"]
            if (v_node, None, None) in g:
                val_uri = v_node

        if val_uri and val_raw is not None:
            # Update qudt:value and qudt:valueSN
            g.remove((val_uri, QUDT_NS.value, None))
            g.remove((val_uri, QUDT_NS.valueSN, None))

            dec_val = to_decimal_str(val_raw)
            sn_val = to_sn_str(val_raw)

            g.add((val_uri, QUDT_NS.value, rdflib.Literal(dec_val, datatype=XSD_NS.decimal)))
            g.add((val_uri, QUDT_NS.valueSN, rdflib.Literal(sn_val, datatype=XSD_NS.double)))

            # Update qudt:standardUncertainty and qudt:standardUncertaintySN
            g.remove((val_uri, QUDT_NS.standardUncertainty, None))
            g.remove((val_uri, QUDT_NS.standardUncertaintySN, None))

            if unc_raw is not None and not is_exact:
                dec_unc = to_decimal_str(str(unc_raw))
                sn_unc = to_sn_str(str(unc_raw))
                g.add((val_uri, QUDT_NS.standardUncertainty, rdflib.Literal(dec_unc, datatype=XSD_NS.decimal)))
                g.add((val_uri, QUDT_NS.standardUncertaintySN, rdflib.Literal(sn_unc, datatype=XSD_NS.double)))
            elif is_exact:
                dec_unc = "0.0"
                sn_unc = "0.0e+00"
                g.add((val_uri, QUDT_NS.standardUncertainty, rdflib.Literal("0.0", datatype=XSD_NS.decimal)))
                g.add((val_uri, QUDT_NS.standardUncertaintySN, rdflib.Literal("0.0e+00", datatype=XSD_NS.double)))
            else:
                dec_unc = "N/A"
                sn_unc = "N/A"

            # Create detailed change note
            hist_note = f"; previously matched CODATA {matched_hist}" if matched_hist else ""
            new_unc_str = "0.0 (Exact)" if is_exact else (dec_unc if dec_unc != "N/A" else "N/A")
            change_note_text = (
                f"Updated to CODATA {target_version} recommended value: "
                f"value changed from {old_val} to {dec_val}, "
                f"uncertainty changed from {old_unc} to {new_unc_str}{hist_note}."
            )

            # Annotate constant subject
            g.remove((subj, SKOS_NS.changeNote, None))
            g.add((subj, SKOS_NS.changeNote, rdflib.Literal(change_note_text, lang="en")))
            g.remove((subj, DCTERMS_NS.modified, None))
            g.add((subj, DCTERMS_NS.modified, rdflib.Literal(current_date_str, datatype=XSD_NS.date)))

            # Annotate quantity value node
            g.remove((val_uri, SKOS_NS.changeNote, None))
            g.add((val_uri, SKOS_NS.changeNote, rdflib.Literal(change_note_text, lang="en")))
            g.remove((val_uri, DCTERMS_NS.modified, None))
            g.add((val_uri, DCTERMS_NS.modified, rdflib.Literal(current_date_str, datatype=XSD_NS.date)))

            # Annotate any alias subjects
            for alias in r.get("qudt_aliases", []):
                if alias != qudt_id:
                    alias_subj = CONST_NS[alias]
                    if (alias_subj, rdflib.RDF.type, QUDT_NS.PhysicalConstant) in g:
                        g.remove((alias_subj, SKOS_NS.changeNote, None))
                        g.add((alias_subj, SKOS_NS.changeNote, rdflib.Literal(change_note_text, lang="en")))
                        g.remove((alias_subj, DCTERMS_NS.modified, None))
                        g.add((alias_subj, DCTERMS_NS.modified, rdflib.Literal(current_date_str, datatype=XSD_NS.date)))

            updated_count += 1

    # Update ontology-level metadata
    onto_uri = rdflib.URIRef("http://qudt.org/3.5.0/vocab/constant")
    g.remove((onto_uri, OWL_NS.versionInfo, None))
    g.add((onto_uri, OWL_NS.versionInfo, rdflib.Literal(f"3.5.0-codata{target_version}")))

    onto_change_note = (
        f"Updated {updated_count} physical constant values and standard uncertainties "
        f"to official CODATA {target_version} recommendations from NIST (CODATA-DRUM Task Group)."
    )
    g.remove((onto_uri, SKOS_NS.changeNote, None))
    g.add((onto_uri, SKOS_NS.changeNote, rdflib.Literal(onto_change_note, lang="en")))
    g.remove((onto_uri, DCTERMS_NS.modified, None))
    g.add((onto_uri, DCTERMS_NS.modified, rdflib.Literal(current_iso_datetime, datatype=XSD_NS.dateTime)))

    # Update vaem:GMD_QUDT-CONSTANTS metadata
    gmd_uri = VAEM_NS["GMD_QUDT-CONSTANTS"]
    if (gmd_uri, None, None) in g:
        g.remove((gmd_uri, DCTERMS_NS.modified, None))
        g.add((gmd_uri, DCTERMS_NS.modified, rdflib.Literal(current_iso_datetime, datatype=XSD_NS.dateTime)))
        g.remove((gmd_uri, SKOS_NS.changeNote, None))
        g.add((gmd_uri, SKOS_NS.changeNote, rdflib.Literal(onto_change_note, lang="en")))

    if output_md_path is None:
        output_md_path = output_ttl_path.with_suffix(".md")

    # Serialize Turtle graph
    serialized_ttl = g.serialize(format="turtle")

    # Build header comment block documenting list of changes
    header_lines = [
        "# ==============================================================================",
        f"# QUDT Physical Constants Vocabulary — Synchronized with CODATA {target_version}",
        "#",
        "# Generated by : codata-compare-qudt (CODATA-DRUM Task Group)",
        f"# Update Date  : {current_date_str}",
        "# Base Ontology: http://qudt.org/3.5.0/vocab/constant",
        f"# Version Info : 3.5.0-codata{target_version}",
        f"# Total Constants Evaluated : {len(results) if results else 'N/A'}",
        f"# Total Constants Updated   : {updated_count}",
        "#",
        "# HISTORICAL RELEASE BREAKDOWN OF UPDATED VALUES:",
    ]
    hist_counts = {}
    for r in outdated_items:
        v = r.get("matched_version") or "Unknown/Custom"
        hist_counts[v] = hist_counts.get(v, 0) + 1
    for v in sorted(hist_counts.keys(), reverse=True):
        header_lines.append(f"#   - CODATA {v}: {hist_counts[v]} constants")

    header_lines.extend([
        "#",
        f"# DOCUMENTED LIST OF CHANGES ({updated_count} CONSTANTS UPDATED):",
        "# " + "-" * 115,
        f"# {'QUDT CONSTANT ID':<42} | {'PREVIOUS VALUE':<22} -> {'UPDATED CODATA VALUE':<22} | {'PREV RELEASE'}",
        "# " + "-" * 115,
    ])

    for r in outdated_items:
        q_id = r["qudt_id"]
        old_v = r.get("qudt_val") or "N/A"
        new_v = to_decimal_str(r.get("codata_val")) or "N/A"
        prev_v = f"CODATA {r.get('matched_version')}" if r.get("matched_version") else "Unknown"
        header_lines.append(f"# {q_id:<42} | {old_v:<22} -> {new_v:<22} | {prev_v}")

    header_lines.extend([
        "# " + "-" * 115,
        "# Every updated entity in this graph contains machine-readable annotations:",
        f"#   skos:changeNote \"Updated to CODATA {target_version}...\"@en ;",
        f"#   dcterms:modified \"{current_date_str}\"^^xsd:date .",
        "#",
        f"# Detailed companion changelog and uncertainty analysis: {output_md_path.name}",
        "# ==============================================================================",
        "",
    ])

    final_ttl_content = "\n".join(header_lines) + serialized_ttl

    output_ttl_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_ttl_path, "w", encoding="utf-8") as f:
        f.write(final_ttl_content)

    logging.info(f"Successfully exported updated Turtle file to {output_ttl_path} ({updated_count} constants updated with changelog annotations).")

    # Generate companion Markdown update document
    if results is not None:
        generate_export_companion_md(output_md_path, results, target_version=target_version, ttl_file_name=output_ttl_path.name)

    return output_ttl_path, output_md_path


def main():
    parser = argparse.ArgumentParser(
        description="Compare QUDT Turtle constant values with official CODATA constants JSON."
    )
    parser.add_argument(
        "--codata-json",
        type=Path,
        default=DEFAULT_CODATA_JSON,
        help="Path to codata_constants.json",
    )
    parser.add_argument(
        "--qudt-url",
        type=str,
        default=QUDT_TTL_DEFAULT_URL,
        help="URL of QUDT constants Turtle file",
    )
    parser.add_argument(
        "--cache-dir",
        type=Path,
        default=DEFAULT_CACHE_DIR,
        help="Directory to cache fetched Turtle file",
    )
    parser.add_argument(
        "--refresh",
        action="store_true",
        help="Force re-download of QUDT Turtle file ignoring cache",
    )
    parser.add_argument(
        "--format",
        choices=["terminal", "markdown", "html", "json", "csv"],
        default="terminal",
        help="Output format (default: terminal)",
    )
    parser.add_argument(
        "--outdated-only",
        action="store_true",
        help="Show only outdated / mismatched constants",
    )
    parser.add_argument(
        "--version",
        default="2022",
        help="Target CODATA release version to compare against (default: 2022)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Output file path (prints to stdout if not specified)",
    )
    parser.add_argument(
        "--export-ttl",
        nargs="?",
        const=True,
        default=False,
        help="Produce and export an updated Turtle file with latest CODATA values and documented list of changes (e.g. qudt_constants_constant.<year>.ttl)",
    )
    parser.add_argument(
        "--update-qudt",
        action="store_true",
        help="Produce updated QUDT Turtle file with documented list of changes (alias for --export-ttl)",
    )
    parser.add_argument(
        "--export-md",
        type=Path,
        help="Custom path for companion Markdown change documentation file (default: matches --export-ttl with .md suffix)",
    )

    args = parser.parse_args()

    # 1. Fetch & Cache QUDT TTL
    ttl_path = fetch_and_cache_qudt_ttl(args.qudt_url, args.cache_dir, force_refresh=args.refresh)

    # 2. Parse QUDT TTL
    qudt_map, multi_entry_groups = parse_qudt_graph(ttl_path)

    # 3. Parse CODATA JSON
    codata_map, all_constants = parse_codata_json(args.codata_json)

    # 4. Compare using Dynamic Runtime Alias Detection
    results = run_comparison(codata_map, qudt_map, all_codata_constants=all_constants, target_version=args.version)

    # 5. Export Updated Turtle File if requested
    if args.export_ttl or args.update_qudt:
        if isinstance(args.export_ttl, (str, Path)) and args.export_ttl is not True:
            out_ttl_path = Path(args.export_ttl)
        else:
            out_ttl_path = args.cache_dir / f"qudt_constants_constant.{args.version}.ttl"

        out_md_path = args.export_md if args.export_md else out_ttl_path.with_suffix(".md")
        export_updated_ttl(
            ttl_path,
            out_ttl_path,
            codata_map,
            results=results,
            target_version=args.version,
            output_md_path=out_md_path,
        )

    # 6. Format Output
    output_str: str = ""
    if args.format == "terminal":
        output_str = format_terminal_output(results, multi_entry_groups=multi_entry_groups, outdated_only=args.outdated_only)
    elif args.format == "markdown":
        output_str = format_markdown_output(results, multi_entry_groups=multi_entry_groups, outdated_only=args.outdated_only)
    elif args.format == "html":
        output_str = format_html_output(results, multi_entry_groups=multi_entry_groups, outdated_only=args.outdated_only)
    elif args.format == "json":
        filtered = [r for r in results if not args.outdated_only or r["status"] == "OUTDATED"]
        output_str = json.dumps({"comparison": filtered, "multi_entry_groups": multi_entry_groups}, indent=2)
    elif args.format == "csv":
        filtered = [r for r in results if not args.outdated_only or r["status"] == "OUTDATED"]
        if filtered:
            import io
            sio = io.StringIO()
            # convert qudt_aliases to string for CSV
            for r in filtered:
                r["qudt_aliases"] = ", ".join(r.get("qudt_aliases", []))
            writer = csv.DictWriter(sio, fieldnames=filtered[0].keys())
            writer.writeheader()
            writer.writerows(filtered)
            output_str = sio.getvalue()
        else:
            output_str = ""

    # 7. Write or Display Output
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(output_str)
        logging.info(f"Report written to {args.output}")
    else:
        print(output_str)


if __name__ == "__main__":
    main()
