"""
PrimeKG Knowledge Graph query module for PeptideDB.

Provides lazy-loaded SQLite access to a filtered PrimeKG biomedical
knowledge graph with entity name-bridging between PeptideDB's
layperson names and PrimeKG's ontology-standardized IDs.

All public functions return empty results when the database is
not available (graceful degradation for Vercel or fresh clones).

Reference:
  - GitHub: https://github.com/mims-harvard/PrimeKG
  - Paper: https://www.nature.com/articles/s41597-023-01960-3
  - Data: https://doi.org/10.7910/DVN/IXA7BM (Harvard Dataverse)
  - License: MIT (code), CC-BY (data)
"""

import os
import re
import sqlite3

DB_PATH = os.environ.get("PRIMEKG_DB_PATH") or os.path.join(os.path.dirname(__file__), "data", "primekg.db")

_conn = None

# Entity name aliases: PeptideDB name -> PrimeKG name
ENTITY_ALIASES = {
    "pt-141": "bremelanotide",
    "pt141": "bremelanotide",
    "aod-9604": "AOD-9604",
    "aod9604": "AOD-9604",
    "melanotan-2": "melanotan II",
    "melanotan2": "melanotan II",
    "melanotan i": "melanotan I",
    "melanotan-1": "melanotan I",
    "melanotan1": "melanotan I",
    "igf-1": "IGF-1",
    "igf1": "IGF-1",
    "igf-1-lr3": "IGF-1",
    "igf1-lr3": "IGF-1",
    "ghk-cu": "GHK-Cu",
    "ghkcu": "GHK-Cu",
    "mk-677": "MK-677",
    "mk677": "MK-677",
    "ss-31": "SS-31",
    "ss31": "SS-31",
    "bpc-157": "BPC-157",
    "bpc157": "BPC-157",
    "tb-500": "TB-500",
    "tb500": "TB-500",
    "tb4": "TB-500",
    "cjc-1295": "CJC-1295",
    "cjc1295": "CJC-1295",
    "dac": "CJC-1295",
    "epitalon": "Epitalon",
    "epithalon": "Epitalon",
    "kpv": "KPV",
    "lla-aa": "Lys-Leu-Ala",
    "semax": "Semax",
    "selank": "Selank",
    "pinealon": "Pinealon",
    "vesugen": "Vesugen",
    "cerebrolysin": "Cerebrolysin",
    "dihexa": "Dihexa",
    "p21": "P21",
    "adamax": "Adamax",
    "kisspeptin-10": "kisspeptin",
    "kisspeptin10": "kisspeptin",
    "motsc": "MOTS-c",
    "motsc": "MOTS-c",
    "foxo4-dri": "FOXO4-DRI",
    "urolithin a": "urolithin A",
    "nmn": "NMN",
    "nad": "NAD+",
    "nr": "nicotinamide riboside",
}

# Relation type display labels
RELATION_LABELS = {
    "indication": "FDA Indication",
    "contraindication": "Contraindication",
    "off-label use": "Off-Label Use",
    "drug_protein": "Drug Target / Protein Interaction",
    "disease_protein": "Disease-Associated Protein",
    "disease_phenotype_positive": "Associated Phenotype",
    "disease_disease": "Related Disease",
    "drug_drug": "Drug Interaction",
    "protein_protein": "Protein-Protein Interaction",
    "drug_disease": "Drug-Disease Association",
}

# Relation priority for formatting (lower = higher priority)
RELATION_PRIORITY = {
    "indication": 0,
    "contraindication": 1,
    "off-label use": 2,
    "drug_protein": 3,
    "disease_disease": 4,
    "disease_protein": 5,
    "disease_phenotype_positive": 6,
    "drug_disease": 7,
    "drug_drug": 8,
    "protein_protein": 9,
}


def _get_db():
    """Lazy-open SQLite connection in read-only mode. Returns None on failure."""
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
    """Try to resolve a PeptideDB name to a PrimeKG name via aliases."""
    nl = name.lower().strip().replace("_", " ").replace("-", " ")
    # Direct check in aliases
    if nl in ENTITY_ALIASES:
        return ENTITY_ALIASES[nl]
    # Check full alias dict with original name
    name_key = name.lower().strip()
    if name_key in ENTITY_ALIASES:
        return ENTITY_ALIASES[name_key]
    return name


def _name_tokens(name):
    """Extract meaningful tokens from a name for matching."""
    return set(re.findall(r'[a-z0-9]+', name.lower()))


def _token_overlap(a, b):
    """Jaccard similarity between token sets of two names."""
    ta = _name_tokens(a)
    tb = _name_tokens(b)
    if not ta or not tb:
        return 0
    return len(ta & tb) / max(len(ta | tb), 1)


def query_by_entity_name(entity_name, relation_filter=None, max_results=30):
    """
    Search PrimeKG edges where entity_name appears as x_name or y_name.

    Uses substring matching + token overlap scoring for flexible name lookup.
    Returns list of dicts with edge details.
    """
    db = _get_db()
    if db is None or not entity_name:
        return []

    resolved = _resolve_name(entity_name)
    results = []

    # Strategy 1: Exact substring match (fast, prioritized)
    like_pattern = f"%{resolved}%"
    if relation_filter:
        query = """
            SELECT * FROM edges
            WHERE (x_name LIKE ? OR y_name LIKE ?)
            AND relation IN ({})
            ORDER BY row_id
            LIMIT ?
        """.format(",".join("?" for _ in relation_filter))
        params = [like_pattern, like_pattern] + list(relation_filter) + [max_results]
    else:
        query = """
            SELECT * FROM edges
            WHERE (x_name LIKE ? OR y_name LIKE ?)
            ORDER BY row_id
            LIMIT ?
        """
        params = [like_pattern, like_pattern, max_results]

    try:
        for row in db.execute(query, params):
            results.append(dict(row))
    except sqlite3.Error:
        return []

    # Strategy 2: If few results, try token overlap scoring
    if len(results) < 5:
        token_rows = []
        token_query = "SELECT * FROM edges ORDER BY row_id LIMIT 100000"
        try:
            for row in db.execute(token_query):
                xm = row["x_name"] or ""
                ym = row["y_name"] or ""
                score = max(_token_overlap(entity_name, xm), _token_overlap(entity_name, ym))
                if score > 0.5 and row["row_id"] not in {r["row_id"] for r in results}:
                    if relation_filter is None or row["relation"] in relation_filter:
                        token_rows.append((dict(row), score))
        except sqlite3.Error:
            pass

        token_rows.sort(key=lambda x: -x[1])
        results.extend(r for r, _ in token_rows[:10])

    return results[:max_results]


def query_drug_relations(drug_name, max_results=20):
    """
    Get all PrimeKG relationships for a drug/peptide.

    Returns dict keyed by relation type, each value is a list of
    edge dicts describing the relationship.
    """
    edges = query_by_entity_name(drug_name, max_results=max_results)
    return _group_by_relation(edges, drug_name)


def query_disease_relations(disease_name, max_results=20):
    """
    Get all PrimeKG relationships for a disease/condition.

    Returns dict with keys: drugs, phenotypes, proteins, related_diseases.
    """
    edges = query_by_entity_name(disease_name, max_results=max_results)
    grouped = _group_by_relation(edges, disease_name)

    result = {"drugs": [], "phenotypes": [], "proteins": [], "related_diseases": []}
    for rel_type, entities in grouped.items():
        for e in entities:
            etype = e.get("other_type", "").lower()
            if rel_type in ("indication", "contraindication", "off-label use", "drug_disease"):
                result["drugs"].append(e)
            elif rel_type == "disease_phenotype_positive":
                result["phenotypes"].append(e)
            elif rel_type in ("disease_protein", "protein_disease"):
                result["proteins"].append(e)
            elif rel_type == "disease_disease":
                result["related_diseases"].append(e)
            else:
                # Fall through by entity type
                if etype in ("drug", "chemical compound"):
                    result["drugs"].append(e)
                elif etype in ("protein", "gene/protein"):
                    result["proteins"].append(e)
                elif etype in ("effect/phenotype", "phenotype"):
                    result["phenotypes"].append(e)
                elif etype == "disease":
                    result["related_diseases"].append(e)

    return result


def query_protein_targets(protein_name, max_results=10):
    """
    Get drugs/compounds that interact with a given protein target.
    """
    edges = query_by_entity_name(protein_name, relation_filter=["drug_protein"], max_results=max_results)
    drugs = []
    for e in edges:
        x_type = (e.get("x_type") or "").lower()
        y_type = (e.get("y_type") or "").lower()
        x_name = e.get("x_name") or ""
        y_name = e.get("y_name") or ""
        target_lower = protein_name.lower()

        if target_lower in x_name.lower():
            drugs.append({"name": y_name, "type": y_type, "id": e.get("y_id") or "",
                          "relation": e["relation"], "source": e.get("y_source") or ""})
        elif target_lower in y_name.lower():
            drugs.append({"name": x_name, "type": x_type, "id": e.get("x_id") or "",
                          "relation": e["relation"], "source": e.get("x_source") or ""})
    return drugs


def get_entity_summary(entity_name):
    """
    Get a high-level summary of all PrimeKG relationships for an entity.

    Returns a flat dict suitable for JSON serialization (used by
    fetch_peptide_evidence() in the evidence pipeline).
    """
    edges = query_by_entity_name(entity_name, max_results=40)
    if not edges:
        return None

    grouped = _group_by_relation(edges, entity_name)
    summary = {"entity": entity_name, "edge_count": len(edges), "relations": {}}

    for rel_type, entities in grouped.items():
        label = RELATION_LABELS.get(rel_type, rel_type.replace("_", " ").title())
        names = []
        for e in entities[:5]:  # Top 5 per type
            name = e.get("other_name", "")
            etype = e.get("other_type", "")
            eid = e.get("other_id", "")
            entry = name
            if eid:
                entry += f" ({eid})"
            names.append(entry)
        summary["relations"][label] = names
        summary["relations"][f"{label}_full"] = entities[:8]

    return summary


PRIMEKG_SOURCE_INFO = """### PrimeKG Knowledge Graph
- **Source:** Precision Medicine Knowledge Graph (Harvard)
- **GitHub:** [mims-harvard/PrimeKG](https://github.com/mims-harvard/PrimeKG)
- **Publication:** Nature Scientific Data (2023) — [doi:10.1038/s41597-023-01960-3](https://doi.org/10.1038/s41597-023-01960-3)
- **Data:** Harvard Dataverse — [doi:10.7910/DVN/IXA7BM](https://doi.org/10.7910/DVN/IXA7BM)
- **Coverage:** 17,080 diseases, 4,050,249 relationships across 10 biological scales
- **License:** MIT (code), CC-BY (data)
- **Description:** Integrates 20 biomedical resources (DrugBank, OMIM, PubMed, ClinicalTrials.gov, etc.)
  into a heterogeneous knowledge graph for precision medicine research."""


def get_primekg_citation():
    """Return PrimeKG reference metadata for chat citations.

    Returns a dict with source info the chat system can use to
    display PrimeKG as a cited knowledge source.
    """
    return {
        "label": "PrimeKG (Harvard)",
        "url": "https://github.com/mims-harvard/PrimeKG",
        "type": "knowledge_graph",
        "description": "Precision Medicine Knowledge Graph — 17,080 diseases, 4M+ relationships",
    }


def format_relations_for_context(edges_dict, entity_label):
    """
    Format PrimeKG edges into human-readable markdown text for LLM context injection.

    Args:
        edges_dict: Dict from query_drug_relations() or query_disease_relations()
        entity_label: Display label for the entity (e.g., "semaglutide")

    Returns:
        Markdown string or empty string if no edges
    """
    if not edges_dict:
        return ""

    parts = [f"### {entity_label.upper()} - PrimeKG Knowledge Graph"]

    # Sort relation types by priority
    sorted_types = sorted(edges_dict.keys(), key=lambda r: RELATION_PRIORITY.get(r, 99))

    for rel_type in sorted_types:
        entities = edges_dict[rel_type]
        if not entities:
            continue
        label = RELATION_LABELS.get(rel_type, rel_type.replace("_", " ").title())
        names = []
        for e in entities[:5]:
            name = e.get("other_name", "")
            source = e.get("other_source", "")
            entry = name
            if source:
                entry += f" ({source})"
            names.append(entry)
        if names:
            parts.append(f"**{label}:** {', '.join(names)}")

    parts.append("*Source: PrimeKG biomedical knowledge graph (Harvard).*")
    parts.append("")
    return "\n".join(parts)


def _group_by_relation(edges, query_name):
    """
    Group edges by relation type. Determines 'other' entity (the one
    that is NOT the query_name).
    """
    ql = query_name.lower()
    grouped = {}
    for e in edges:
        rel = e.get("relation", "unknown")
        x_name = e.get("x_name", "") or ""
        y_name = e.get("y_name", "") or ""

        if ql in x_name.lower() or _token_overlap(query_name, x_name) > 0.6:
            other = {"other_name": y_name, "other_type": e.get("y_type", ""),
                     "other_id": e.get("y_id", ""), "other_source": e.get("y_source", "")}
        elif ql in y_name.lower() or _token_overlap(query_name, y_name) > 0.6:
            other = {"other_name": x_name, "other_type": e.get("x_type", ""),
                     "other_id": e.get("x_id", ""), "other_source": e.get("x_source", "")}
        else:
            # Token match: pick the one with higher overlap
            x_overlap = _token_overlap(query_name, x_name)
            y_overlap = _token_overlap(query_name, y_name)
            if x_overlap >= y_overlap:
                other = {"other_name": y_name, "other_type": e.get("y_type", ""),
                         "other_id": e.get("y_id", ""), "other_source": e.get("y_source", "")}
            else:
                other = {"other_name": x_name, "other_type": e.get("x_type", ""),
                         "other_id": e.get("x_id", ""), "other_source": e.get("x_source", "")}

        if rel not in grouped:
            grouped[rel] = []
        grouped[rel].append({**other, "display_relation": e.get("display_relation", "")})

    return grouped
