"""
SIDER — Side Effect Resource query module for PeptideDB.

Provides lazy-loaded SQLite access to drug-side effect data from the
EMBL SIDER 4.1 database. All public functions return empty results
when the database is not available (graceful degradation).

Reference:
  - Site: http://sideeffects.embl.de/
  - Paper: https://doi.org/10.1093/nar/gkv1075 (Nucleic Acids Research, 2016)
  - Data: CC BY-SA 4.0 (meddra_all_se), CC0 (drug_names)
  - Coverage: 1,430 drugs, 5,800 side effects, 140,000+ drug-side effect pairs
"""

import gzip
import csv
import os
import sqlite3
import io

DB_PATH = os.environ.get("SIDER_DB_PATH") or os.path.join(
    os.path.dirname(__file__), "data", "sider.db"
)

_conn = None

SIDER_SOURCE_INFO = """### SIDER — Side Effect Resource
- **Source:** EMBL Heidelberg — SIDER 4.1
- **Publication:** Nucleic Acids Research (2016) — [doi:10.1093/nar/gkv1075](https://doi.org/10.1093/nar/gkv1075)
- **Coverage:** 1,430 marketed drugs, 5,800 side effect types, 140,000+ drug-side effect associations
- **Data Source:** FDA package inserts and public drug labels
- **URL:** [http://sideeffects.embl.de/](http://sideeffects.embl.de/)
- **License:** CC BY-SA 4.0"""

# Drug name aliases mapping PeptideDB names → SIDER drug names
DRUG_ALIASES = {
    "bpc-157": "bpc 157",
    "bpc157": "bpc 157",
    "tb-500": "thymosin beta 4",
    "tb500": "thymosin beta 4",
    "semaglutide": "semaglutide",
    "tirzepatide": "tirzepatide",
    "retatrutide": "retatrutide",
    "mk-677": "ibutamoren",
    "mk677": "ibutamoren",
    "aod-9604": "aod 9604",
    "aod9604": "aod 9604",
    "cjc-1295": "cjc 1295",
    "cjc1295": "cjc 1295",
    "ghk-cu": "ghk cu",
    "ghkcu": "ghk cu",
    "ss-31": "ss 31",
    "ss31": "ss 31",
    "pt-141": "bremelanotide",
    "pt141": "bremelanotide",
    "melanotan ii": "melanotan ii",
    "igf-1": "insulin like growth factor 1",
    "igf1": "insulin like growth factor 1",
    "ipamorelin": "ipamorelin",
    "sermorelin": "sermorelin",
    "tesamorelin": "tesamorelin",
    "liraglutide": "liraglutide",
    "cagrilintide": "cagrilintide",
    "mazdutide": "mazdutide",
    "survodutide": "survodutide",
    "minoxidil": "minoxidil",
    "finasteride": "finasteride",
    "dutasteride": "dutasteride",
    "metformin": "metformin",
    "berberine": "berberine",
    "rapamycin": "sirolimus",
    "nmn": "nicotinamide mononucleotide",
    "nad": "nicotinamide adenine dinucleotide",
    "resveratrol": "resveratrol",
    "thymosin alpha 1": "thymosin alpha 1",
    "thymulin": "thymulin",
    "kisspeptin-10": "kisspeptin",
    "kisspeptin": "kisspeptin",
    "motsc": "motsc",
    "humanin": "humanin",
    "epitalon": "epitalon",
    "selank": "selank",
    "semax": "semax",
    "dihexa": "dihexa",
    "bremelanotide": "bremelanotide",
    "oxytocin": "oxytocin",
    "ghrelin": "ghrelin",
    "growth hormone": "somatropin",
    "hgh": "somatropin",
    "testosterone": "testosterone",
    "prednisone": "prednisone",
    "ibuprofen": "ibuprofen",
    "aspirin": "aspirin",
    "acetaminophen": "acetaminophen",
}


def _get_db():
    """Lazy-open SQLite connection in read-only mode."""
    global _conn
    if _conn is None:
        if not os.path.exists(DB_PATH):
            return None
        try:
            _conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
            _conn.row_factory = sqlite3.Row
        except sqlite3.Error:
            return None
    return _conn


def _resolve_name(name):
    """Resolve a name to SIDER drug name via aliases."""
    nl = name.lower().strip().replace("_", " ").replace("-", " ")
    if nl in DRUG_ALIASES:
        return DRUG_ALIASES[nl]
    # Try partial matching — check if any alias key is contained in the name
    for alias, canonical in DRUG_ALIASES.items():
        if alias in nl or nl in alias:
            return canonical
    return name.lower().strip()


def get_sider_citation():
    """Return SIDER reference metadata for chat citations."""
    return {
        "label": "SIDER (EMBL)",
        "url": "http://sideeffects.embl.de/",
        "type": "side_effect_database",
        "description": "Drug side effect profiles from FDA labels — 1,430 drugs, 5,800 side effects",
    }


def query_drug_side_effects(drug_name, max_results=20):
    """Look up side effects associated with a drug or peptide.

    Returns list of dicts with side effect info, or empty list
    when the database is unavailable.
    """
    db = _get_db()
    if db is None:
        return []

    resolved = _resolve_name(drug_name)
    results = []

    # Exact match first
    like_pattern = f"%{resolved}%"
    query = """
        SELECT side_effect, umls_meddra_cui, meddra_type
        FROM side_effects
        WHERE drug_name LIKE ?
        LIMIT ?
    """
    try:
        for row in db.execute(query, (like_pattern, max_results)):
            results.append(dict(row))
    except sqlite3.Error:
        return []

    # If the resolved name differs from original, also try original
    if resolved != drug_name.lower().strip():
        orig_pattern = f"%{drug_name.lower().strip()}%"
        try:
            for row in db.execute(query, (orig_pattern, max_results)):
                results.append(dict(row))
        except sqlite3.Error:
            pass

    # Deduplicate by side effect name
    seen = set()
    unique = []
    for r in results:
        se = r.get("side_effect", "").lower()
        if se not in seen:
            seen.add(se)
            unique.append(r)

    # Count how many drugs report each side effect (multiplicity)
    for r in unique:
        try:
            cursor = db.execute(
                "SELECT COUNT(DISTINCT drug_name) as cnt FROM side_effects WHERE side_effect = ?",
                (r["side_effect"],),
            )
            cnt_row = cursor.fetchone()
            r["drug_count"] = cnt_row["cnt"] if cnt_row else 1
        except sqlite3.Error:
            r["drug_count"] = 1

    return unique[:max_results]


def query_side_effect_drugs(side_effect_name, max_results=15):
    """Find drugs that are associated with a given side effect.

    Returns list of dicts with drug names, or empty list when the
    database is unavailable.
    """
    db = _get_db()
    if db is None:
        return []

    pattern = f"%{side_effect_name.lower()}%"
    query = """
        SELECT DISTINCT drug_name
        FROM side_effects
        WHERE LOWER(side_effect) LIKE ?
        LIMIT ?
    """
    try:
        return [{"drug_name": row["drug_name"]} for row in db.execute(query, (pattern, max_results))]
    except sqlite3.Error:
        return []


def format_side_effects_for_context(drug_name: str, max_results: int = 12) -> str:
    """Format SIDER side effects as markdown for system prompt injection.

    Returns empty string when DB unavailable or no side effects found.
    """
    effects = query_drug_side_effects(drug_name, max_results)
    if not effects:
        return ""

    parts = [
        f"### SIDER Side Effects — {drug_name.upper()}\n",
        f"Known adverse reactions from FDA label data ({len(effects)} reported):\n\n",
    ]
    for e in effects[:12]:
        se = e.get("side_effect", "")
        dc = e.get("drug_count", 1)
        parts.append(f"- {se} (reported in {dc} drug{'s' if dc > 1 else ''})\n")

    parts.append(
        "\n*Source: SIDER 4.1 — [EMBL Heidelberg](http://sideeffects.embl.de/). "
        "Data from FDA package inserts.*\n\n"
    )
    return "".join(parts)


def get_download_instructions() -> str:
    """Return instructions for building the SIDER SQLite database."""
    return """
To build the SIDER side effect database:

  python scripts/build_sider_db.py

This will download meddra_all_se.tsv.gz and drug_names.tsv from
EMBL, then build data/sider.db with indexed tables (~10 MB SQLite).
"""
