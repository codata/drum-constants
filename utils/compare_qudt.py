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
import urllib.request
from pathlib import Path

import rdflib

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

QUDT_TTL_DEFAULT_URL = "https://qudt.org/3.5.0/vocab/constant"
DEFAULT_CACHE_DIR = Path(__file__).parent / "cache"
DEFAULT_CODATA_JSON = Path(__file__).parent / "codata_constants.json"

HISTORICAL_VERSIONS = ["2022", "2018", "2014", "2010", "2006", "2002", "1998"]

# RDF Namespaces
QUDT_NS = rdflib.Namespace("http://qudt.org/schema/qudt/")
CONST_NS = rdflib.Namespace("http://qudt.org/vocab/constant/")
RDFS_NS = rdflib.Namespace("http://www.w3.org/2000/01/rdf-schema#")


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


def parse_qudt_graph(ttl_path: Path) -> dict:
    """
    Parses the QUDT Turtle file using rdflib and extracts PhysicalConstant definitions.
    Returns a dictionary keyed by QUDT constant ID (local name).
    """
    logging.info(f"Parsing QUDT Turtle data from {ttl_path}...")
    g = rdflib.Graph()
    g.parse(ttl_path, format="turtle")

    qudt_constants = {}

    for subject in g.subjects(rdflib.RDF.type, QUDT_NS.PhysicalConstant):
        subject_str = str(subject)
        local_id = subject_str.replace(str(CONST_NS), "").split("/")[-1]

        label = g.value(subject, RDFS_NS.label)
        val_uri = g.value(subject, QUDT_NS.quantityValue)

        val_str = None
        unc_str = None
        unit_str = None

        if val_uri:
            val_node = g.value(val_uri, QUDT_NS.value) or g.value(val_uri, QUDT_NS.valueSN)
            unc_node = g.value(val_uri, QUDT_NS.standardUncertainty) or g.value(val_uri, QUDT_NS.standardUncertaintySN)
            unit_node = g.value(val_uri, QUDT_NS.hasUnit)

            val_str = str(val_node) if val_node is not None else None
            unc_str = str(unc_node) if unc_node is not None else None
            unit_str = str(unit_node).replace("http://qudt.org/vocab/unit/", "") if unit_node else None

        qudt_constants[local_id] = {
            "uri": subject_str,
            "id": local_id,
            "label": str(label) if label else local_id,
            "value": val_str,
            "uncertainty": unc_str,
            "unit": unit_str,
            "has_quantity_value": val_uri is not None,
        }

    logging.info(f"Extracted {len(qudt_constants)} PhysicalConstant items from QUDT graph.")
    return qudt_constants


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


def run_comparison(codata_map: dict, qudt_map: dict, target_version: str = "2022") -> list[dict]:
    """
    Performs side-by-side comparison of QUDT vs CODATA constants.
    """
    results = []
    processed_qudt_ids = set()

    # 1. Process items mapped in CODATA JSON
    for qudt_id, c_data in codata_map.items():
        processed_qudt_ids.add(qudt_id)

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
                "details": "QUDT ID referenced in CODATA JSON, but entity missing in QUDT TTL.",
            })
            continue

        qudt_val_str = qudt_entry["value"]
        qudt_unc_str = qudt_entry["uncertainty"]

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
                "details": details,
            })

    # 2. Process QUDT constants not referenced in CODATA JSON
    for qudt_id, qudt_entry in qudt_map.items():
        if qudt_id not in processed_qudt_ids:
            results.append({
                "qudt_id": qudt_id,
                "constant_id": None,
                "name": qudt_entry["label"],
                "status": "UNMAPPED_IN_CODATA",
                "qudt_val": qudt_entry["value"],
                "qudt_unc": qudt_entry["uncertainty"],
                "codata_val": None,
                "codata_unc": None,
                "codata_is_exact": False,
                "matched_version": None,
                "details": "Present in QUDT TTL, but not mapped via QUDT ID in codata_constants.json.",
            })

    return results


def format_terminal_output(results: list[dict], outdated_only: bool = False) -> str:
    """
    Renders terminal side-by-side table.
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
    missing_q = sum(1 for r in results if r["status"] in ("MISSING_IN_QUDT", "MISSING_VALUE_IN_QUDT"))
    unmapped = sum(1 for r in results if r["status"] == "UNMAPPED_IN_CODATA")

    lines.append("\nSUMMARY STATISTICS:")
    lines.append(f"  Total Constants Evaluated: {total}")
    lines.append(f"  Up To Date (CODATA 2022): {up_to_date} ({up_to_date/total*100:.1f}%)")
    lines.append(f"  Outdated (Differs from 2022): {outdated} ({outdated/total*100:.1f}%)")
    lines.append(f"  Missing / No Value in QUDT: {missing_q}")
    lines.append(f"  Unmapped in CODATA JSON:  {unmapped}")

    # Historical breakdown for outdated
    hist_counts = {}
    for r in results:
        if r["status"] == "OUTDATED":
            ver = r["matched_version"] or "Unknown/Custom"
            hist_counts[ver] = hist_counts.get(ver, 0) + 1

    lines.append("\nOUTDATED QUDT CONSTANTS BREAKDOWN BY MATCHED CODATA RELEASE:")
    for ver in sorted(hist_counts.keys(), reverse=True):
        lines.append(f"  CODATA {ver}: {hist_counts[ver]} constants")

    return "\n".join(lines)


def format_markdown_output(results: list[dict], outdated_only: bool = False) -> str:
    """
    Renders Markdown report.
    """
    filtered = [r for r in results if not outdated_only or r["status"] == "OUTDATED"]

    total = len(results)
    up_to_date = sum(1 for r in results if r["status"] == "UP_TO_DATE")
    outdated = sum(1 for r in results if r["status"] == "OUTDATED")
    missing_q = sum(1 for r in results if r["status"] in ("MISSING_IN_QUDT", "MISSING_VALUE_IN_QUDT"))
    unmapped = sum(1 for r in results if r["status"] == "UNMAPPED_IN_CODATA")

    lines: list[str] = []
    lines.append("# QUDT vs CODATA Physical Constants Comparison Report\n")
    lines.append("## Summary Statistics\n")
    lines.append(f"- **Total Evaluated**: {total}")
    lines.append(f"- **Up to Date (CODATA 2022)**: {up_to_date} ({up_to_date/total*100:.1f}%)")
    lines.append(f"- **Outdated QUDT Values**: {outdated} ({outdated/total*100:.1f}%)")
    lines.append(f"- **Missing in QUDT**: {missing_q}")
    lines.append(f"- **Unmapped in CODATA**: {unmapped}\n")

    lines.append("### Outdated Constants Breakdown\n")
    hist_counts = {}
    for r in results:
        if r["status"] == "OUTDATED":
            ver = r["matched_version"] or "Unknown/Custom"
            hist_counts[ver] = hist_counts.get(ver, 0) + 1

    for ver in sorted(hist_counts.keys(), reverse=True):
        lines.append(f"- **CODATA {ver}**: {hist_counts[ver]} constants")

    lines.append("\n## Comparison Table\n")
    lines.append("| QUDT ID | Name | Status | QUDT Value | CODATA 2022 Value | Matched CODATA Version |")
    lines.append("|---|---|---|---|---|---|")

    for r in filtered:
        status_badge = f"`{r['status']}`"
        if r['status'] == 'OUTDATED':
            status_badge = "⚠️ `OUTDATED`"
        elif r['status'] == 'UP_TO_DATE':
            status_badge = "✅ `UP_TO_DATE`"

        q_val = r["qudt_val"] if r["qudt_val"] is not None else "*N/A*"
        c_val = r["codata_val"] if r["codata_val"] is not None else "*N/A*"
        m_ver = f"CODATA {r['matched_version']}" if r["matched_version"] else "*None*"

        lines.append(f"| `{r['qudt_id']}` | {r['name']} | {status_badge} | `{q_val}` | `{c_val}` | {m_ver} |")

    return "\n".join(lines)


def format_html_output(results: list[dict], outdated_only: bool = False) -> str:
    """
    Renders standalone interactive HTML report.
    """
    filtered = [r for r in results if not outdated_only or r["status"] == "OUTDATED"]

    total = len(results)
    up_to_date = sum(1 for r in results if r["status"] == "UP_TO_DATE")
    outdated = sum(1 for r in results if r["status"] == "OUTDATED")
    missing_q = sum(1 for r in results if r["status"] in ("MISSING_IN_QUDT", "MISSING_VALUE_IN_QUDT"))
    unmapped = sum(1 for r in results if r["status"] == "UNMAPPED_IN_CODATA")

    rows_html = []
    for r in filtered:
        status_cls = "status-outdated" if r["status"] == "OUTDATED" else ("status-match" if r["status"] == "UP_TO_DATE" else "status-other")
        status_label = r["status"]
        if r["status"] == "OUTDATED":
            status_label = "⚠️ OUTDATED"
        elif r["status"] == "UP_TO_DATE":
            status_label = "✅ UP TO DATE"

        q_val = r["qudt_val"] or "N/A"
        c_val = r["codata_val"] or "N/A"
        m_ver = f"CODATA {r['matched_version']}" if r["matched_version"] else "None"

        rows_html.append(f"""
        <tr class="{status_cls}">
            <td><code>{r['qudt_id']}</code></td>
            <td>{r['name']}</td>
            <td><span class="badge {status_cls}">{status_label}</span></td>
            <td><code>{q_val}</code></td>
            <td><code>{c_val}</code></td>
            <td><span class="version-tag">{m_ver}</span></td>
        </tr>
        """)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>QUDT vs CODATA Physical Constants Comparison</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; margin: 0; padding: 24px; background: #f8fafc; color: #0f172a; }}
        h1 {{ margin-top: 0; font-weight: 700; color: #1e293b; }}
        .stats-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 16px; margin-bottom: 24px; }}
        .stat-card {{ background: white; padding: 20px; border-radius: 12px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); border: 1px solid #e2e8f0; }}
        .stat-card .val {{ font-size: 28px; font-weight: 700; margin-top: 4px; }}
        .stat-card.outdated .val {{ color: #dc2626; }}
        .stat-card.match .val {{ color: #16a34a; }}
        table {{ width: 100%; border-collapse: collapse; background: white; border-radius: 12px; overflow: hidden; box-shadow: 0 1px 3px rgba(0,0,0,0.1); border: 1px solid #e2e8f0; }}
        th, td {{ padding: 12px 16px; text-align: left; border-bottom: 1px solid #e2e8f0; font-size: 14px; }}
        th {{ background: #f1f5f9; font-weight: 600; color: #475569; }}
        code {{ font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace; background: #f1f5f9; padding: 2px 6px; border-radius: 4px; font-size: 13px; }}
        .badge {{ padding: 4px 8px; border-radius: 6px; font-size: 12px; font-weight: 600; display: inline-block; }}
        .badge.status-outdated {{ background: #fee2e2; color: #991b1b; }}
        .badge.status-match {{ background: #dcfce7; color: #166534; }}
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
        <div class="stat-card">
            <div>Missing / Unmapped</div>
            <div class="val">{missing_q + unmapped}</div>
        </div>
    </div>

    <table>
        <thead>
            <tr>
                <th>QUDT ID</th>
                <th>Constant Name</th>
                <th>Status</th>
                <th>QUDT Value</th>
                <th>CODATA 2022 Value</th>
                <th>Matched CODATA Version</th>
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

    args = parser.parse_args()

    # 1. Fetch & Cache QUDT TTL
    ttl_path = fetch_and_cache_qudt_ttl(args.qudt_url, args.cache_dir, force_refresh=args.refresh)

    # 2. Parse QUDT TTL
    qudt_map = parse_qudt_graph(ttl_path)

    # 3. Parse CODATA JSON
    codata_map, _ = parse_codata_json(args.codata_json)

    # 4. Compare
    results = run_comparison(codata_map, qudt_map, target_version=args.version)

    # 5. Format Output
    output_str: str = ""
    if args.format == "terminal":
        output_str = format_terminal_output(results, outdated_only=args.outdated_only)
    elif args.format == "markdown":
        output_str = format_markdown_output(results, outdated_only=args.outdated_only)
    elif args.format == "html":
        output_str = format_html_output(results, outdated_only=args.outdated_only)
    elif args.format == "json":
        filtered = [r for r in results if not args.outdated_only or r["status"] == "OUTDATED"]
        output_str = json.dumps(filtered, indent=2)
    elif args.format == "csv":
        filtered = [r for r in results if not args.outdated_only or r["status"] == "OUTDATED"]
        if filtered:
            import io
            sio = io.StringIO()
            writer = csv.DictWriter(sio, fieldnames=filtered[0].keys())
            writer.writeheader()
            writer.writerows(filtered)
            output_str = sio.getvalue()
        else:
            output_str = ""

    # 6. Write or Display Output
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(output_str)
        logging.info(f"Report written to {args.output}")
    else:
        print(output_str)


if __name__ == "__main__":
    main()
