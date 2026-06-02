"""
DrugBank query module for PeptideDB.

Provides lazy-loaded SQLite access to DrugBank open-access data
(drug targets, mechanisms, pharmacology, indications). All public
functions return empty results when the database is not available.

Requires manual download of DrugBank open-access XML (free academic
registration at https://go.drugbank.com/).

Reference:
  - Site: https://go.drugbank.com/
  - Paper: https://doi.org/10.1093/nar/gkad976 (Nucleic Acids Research, 2024)
  - License: CC BY-NC 4.0 (open-access subset)
"""

import os
import sqlite3

DB_PATH = os.environ.get("DRUGBANK_DB_PATH") or os.path.join(
    os.path.dirname(__file__), "data", "drugbank.db"
)

_conn = None

DRUGBANK_SOURCE_INFO = """### DrugBank
- **Source:** University of Alberta / The Metabolomics Innovation Centre — DrugBank 6.0
- **Publication:** Nucleic Acids Research (2024) — [doi:10.1093/nar/gkad976](https://doi.org/10.1093/nar/gkad976)
- **Coverage:** 9,591 drug entries (2,037 FDA-approved small molecule, 528 biologics)
- **URL:** [https://go.drugbank.com/](https://go.drugbank.com/)
- **License:** CC BY-NC 4.0 (open-access subset — free registration required)
- **Description:** Manually curated drug-target interactions, pharmacology, mechanisms, and pharmacokinetics"""

# Drug name aliases
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
    "pt-141": "bremelanotide",
    "pt141": "bremelanotide",
    "igf-1": "insulin like growth factor i",
    "igf1": "insulin like growth factor i",
    "melanotan ii": "melanotan ii",
    "liraglutide": "liraglutide",
    "ipamorelin": "ipamorelin",
    "sermorelin": "sermorelin",
    "tesamorelin": "tesamorelin",
    "minoxidil": "minoxidil",
    "finasteride": "finasteride",
    "metformin": "metformin",
    "rapamycin": "sirolimus",
    "resveratrol": "resveratrol",
    "testosterone": "testosterone",
    "oxytocin": "oxytocin",
    "human growth hormone": "somatropin",
    "hgh": "somatropin",
    "nmn": "nicotinamide mononucleotide",
    "nad": "nad",
    "berberine": "berberine",
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
    """Resolve name to DrugBank drug name via aliases."""
    nl = name.lower().strip().replace("_", " ").replace("-", " ")
    if nl in DRUG_ALIASES:
        return DRUG_ALIASES[nl]
    for alias, canonical in DRUG_ALIASES.items():
        if alias in nl or nl in alias:
            return canonical
    return name.lower().strip()


def get_drugbank_citation():
    """Return DrugBank reference metadata."""
    return {
        "label": "DrugBank",
        "url": "https://go.drugbank.com/",
        "type": "pharmacology_database",
        "description": "Drug-target interactions, mechanisms, pharmacology — 9,591 drug entries",
    }


def query_drug_mechanism(drug_name):
    """Get mechanism of action and pharmacology for a drug.

    Returns dict with mechanism, indication, pharmacodynamics, toxicity
    or empty dict when unavailable.
    """
    db = _get_db()
    if db is None:
        return {}

    resolved = _resolve_name(drug_name)
    pattern = f"%{resolved}%"

    query = """
        SELECT name, mechanism_of_action, indication, pharmacodynamics, toxicity
        FROM drugs
        WHERE LOWER(name) LIKE ?
        LIMIT 1
    """
    try:
        row = db.execute(query, (pattern,)).fetchone()
        if row:
            return dict(row)
    except sqlite3.Error:
        pass

    # Try original name
    if resolved != drug_name.lower().strip():
        orig_pattern = f"%{drug_name.lower().strip()}%"
        try:
            row = db.execute(query, (orig_pattern,)).fetchone()
            if row:
                return dict(row)
        except sqlite3.Error:
            pass

    return {}


def query_drug_targets(drug_name, max_results=10):
    """Get protein targets for a drug.

    Returns list of dicts with target name, gene, organism, action.
    """
    db = _get_db()
    if db is None:
        return []

    resolved = _resolve_name(drug_name)
    pattern = f"%{resolved}%"

    query = """
        SELECT target_name, target_gene, organism, action
        FROM drug_targets
        WHERE drug_name LIKE ?
        LIMIT ?
    """
    try:
        return [dict(row) for row in db.execute(query, (pattern, max_results))]
    except sqlite3.Error:
        return []


def query_drug_interactions(drug_name, max_results=15):
    """Get drug-drug interactions for a drug.

    Returns list of dicts with interacting drug and description.
    """
    db = _get_db()
    if db is None:
        return []

    resolved = _resolve_name(drug_name)
    pattern = f"%{resolved}%"

    query = """
        SELECT other_drug, description
        FROM drug_interactions
        WHERE drug_name LIKE ?
        LIMIT ?
    """
    try:
        return [dict(row) for row in db.execute(query, (pattern, max_results))]
    except sqlite3.Error:
        return []


def format_drugbank_for_context(drug_name: str) -> str:
    """Format DrugBank info as markdown for system prompt injection."""
    parts = []

    mechanism = query_drug_mechanism(drug_name)
    if mechanism and mechanism.get("name"):
        parts.append(f"### DrugBank Pharmacology — {mechanism['name'].upper()}\n\n")

        if mechanism.get("mechanism_of_action"):
            moa = mechanism["mechanism_of_action"]
            # Truncate very long strings
            if moa and len(moa) > 1000:
                moa = moa[:1000] + "..."
            parts.append(f"**Mechanism of Action:** {moa}\n\n")

        if mechanism.get("indication"):
            ind = mechanism["indication"]
            if ind and len(ind) > 500:
                ind = ind[:500] + "..."
            parts.append(f"**Indication:** {ind}\n\n")

        if mechanism.get("pharmacodynamics"):
            pd = mechanism["pharmacodynamics"]
            if pd and len(pd) > 500:
                pd = pd[:500] + "..."
            parts.append(f"**Pharmacodynamics:** {pd}\n\n")

        if mechanism.get("toxicity"):
            tox = mechanism["toxicity"]
            if tox and len(tox) > 400:
                tox = tox[:400] + "..."
            parts.append(f"**Toxicity:** {tox}\n\n")

    # Targets
    targets = query_drug_targets(drug_name)
    if targets:
        parts.append("**Protein Targets:**\n")
        for t in targets[:5]:
            gene = t.get("target_gene", "") or ""
            name = t.get("target_name", "") or ""
            action = t.get("action", "") or ""
            desc = f"{name}"
            if gene:
                desc += f" ({gene})"
            if action:
                desc += f" — {action}"
            parts.append(f"- {desc}\n")
        parts.append("\n")

    if not parts:
        return ""

    parts.append(
        "*Source: [DrugBank](https://go.drugbank.com/) — University of Alberta. "
        "CC BY-NC 4.0.*\n\n"
    )
    return "".join(parts)


def get_download_instructions() -> str:
    """Return instructions for obtaining DrugBank data."""
    return """
To build the DrugBank SQLite database:

1. Register for a free academic account at: https://go.drugbank.com/
2. Download the "Full Open-Access XML" (~200 MB)
3. Place the XML file at: data/drugbank.xml
4. Run the build script:
   python scripts/build_drugbank_db.py

This creates data/drugbank.db with indexed tables (~150 MB SQLite).
"""
