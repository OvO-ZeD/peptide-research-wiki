"""
Clinical Knowledge Graph (CKG) query module for PeptideDB.

Provides citation metadata and query stubs for the MannLabs Clinical
Knowledge Graph — an open-source platform with 16M+ nodes and 220M+
relationships spanning proteomics, clinical data, drugs, diseases,
proteins, pathways, and biomedical literature.

The full CKG Neo4j dump is ~80 GB. This module provides:
1. Source citation metadata for the chat system (always available)
2. Query functions that gracefully return empty when the local
   filtered subset is not available (no degradation in chat UX)
3. A download/filter helper to build a peptide-relevant SQLite subset

Reference:
  - GitHub: https://github.com/MannLabs/CKG
  - Paper (BioRxiv): https://www.biorxiv.org/content/10.1101/2020.05.09.084897v1
  - Paper (Nat Biotech via BioCypher): https://doi.org/10.1038/s41587-023-01848-y
  - Graph DB dump: https://data.mendeley.com/datasets/mrcf7f4tc2/1
  - Docs: https://CKG.readthedocs.io
  - License: MIT

Relevant CKG data domains for PeptideDB:
  - UniProt / HPA: peptide sequences, protein targets, tissue expression
  - DrugBank / DGIdb: drug targets, SARMs pharmacology, mechanisms
  - DisGeNET / OncoKB: disease associations, tumor biomarkers, cancer
  - SIDER: drug side effect profiles (SARMs safety)
  - STRING / Reactome: protein networks, metabolic pathways, muscle
  - HMDB: metabolite / amino acid profiles
  - DISEASES: tissue-disease associations for general health
"""

import os
import json

# ---------------------------------------------------------------------------
# CKG Source Metadata (always available — no DB required)
# ---------------------------------------------------------------------------

CKG_SOURCE_INFO = """### Clinical Knowledge Graph (CKG)
- **Source:** MannLab CKG — Clinical Knowledge Graph
- **GitHub:** [MannLabs/CKG](https://github.com/MannLabs/CKG)
- **Publication:** BioRxiv (2020) — [doi:10.1101/2020.05.09.084897](https://www.biorxiv.org/content/10.1101/2020.05.09.084897v1)
- **BioCypher:** Nature Biotechnology (2023) — [doi:10.1038/s41587-023-01848-y](https://doi.org/10.1038/s41587-023-01848-y)
- **Coverage:** 16M+ nodes, 220M+ relationships across proteomics, drugs, diseases, pathways
- **Integrated Sources:** UniProt, DrugBank, STRING, Reactome, DisGeNET, SIDER, HPA, HMDB, OncoKB, DGIdb, and 20+ more
- **License:** MIT"""

# CKG sub-databases mapped to PeptideDB relevance domains
CKG_DOMAINS = {
    "peptides_proteins": {
        "label": "Peptides & Proteins",
        "sources": ["UniProt", "HPA", "PhosphoSitePlus", "Pfam"],
        "description": "Protein sequences, post-translational modifications, tissue expression",
        "relevance": "Peptide identification, protein targets, expression profiles",
    },
    "drug_targets": {
        "label": "Drug Targets & Pharmacology",
        "sources": ["DrugBank", "DGIdb", "STITCH"],
        "description": "Drug-target interactions, mechanisms of action, pharmacology",
        "relevance": "SARMs mechanisms, peptide drug targets, receptor binding",
    },
    "disease_associations": {
        "label": "Disease Associations",
        "sources": ["DisGeNET", "OncoKB", "DISEASES", "Cancer Genome Interpreter"],
        "description": "Gene-disease associations, cancer genomics, tumor biomarkers",
        "relevance": "Tumor biology, disease mechanisms, health conditions",
    },
    "side_effects": {
        "label": "Side Effects & Safety",
        "sources": ["SIDER", "CTD"],
        "description": "Drug adverse effects, toxicity profiles, safety data",
        "relevance": "SARMs side effects, peptide safety profiles",
    },
    "pathways": {
        "label": "Biological Pathways",
        "sources": ["Reactome", "STRING", "CORUM", "GO"],
        "description": "Protein-protein interactions, metabolic pathways, complexes",
        "relevance": "Muscle growth pathways, metabolic routes, signaling",
    },
    "metabolites": {
        "label": "Metabolites & Amino Acids",
        "sources": ["HMDB", "SMPDB", "FooDB"],
        "description": "Metabolite profiles, amino acid pathways, food compounds",
        "relevance": "Amino acid metabolism, nutritional biochemistry",
    },
    "phenotypes": {
        "label": "Phenotypes & Ontologies",
        "sources": ["HPO", "DO", "SNOMED-CT", "EFO"],
        "description": "Phenotype annotations, disease ontologies, clinical terms",
        "relevance": "Clinical phenotype matching, symptom analysis",
    },
}

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DB_PATH = os.environ.get(
    "CKG_DB_PATH",
    os.path.join(os.path.dirname(__file__), "data", "ckg_subset.db"),
)

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def get_ckg_citation() -> dict:
    """Return CKG reference metadata for chat source citations.

    Returns a dict with source info the chat system can use to
    display CKG as a cited knowledge source (no DB required).
    """
    return {
        "label": "CKG (MannLab)",
        "url": "https://github.com/MannLabs/CKG",
        "type": "knowledge_graph",
        "description": "Clinical Knowledge Graph — 16M+ nodes, 220M+ relationships",
    }


def get_domain_summary() -> list[dict]:
    """Return a human-readable summary of CKG domains relevant to PeptideDB.

    Always available — no DB connection needed.
    """
    return [
        {
            "domain": info["label"],
            "sources": info["sources"],
            "relevance": info["relevance"],
        }
        for info in CKG_DOMAINS.values()
    ]


def format_ckg_context_for_prompt() -> str:
    """Return a markdown snippet about CKG for injection into the AI system prompt.

    Always available — no DB connection needed.
    """
    parts = [
        "### Clinical Knowledge Graph (CKG) — MannLab",
        "Relevant domains for biomedical research:",
    ]
    for info in CKG_DOMAINS.values():
        parts.append(
            f"- **{info['label']}** ({', '.join(info['sources'])}): "
            f"{info['relevance']}"
        )
    parts.append(
        "*Source: [MannLabs/CKG](https://github.com/MannLabs/CKG) — "
        "MIT license.*"
    )
    return "\n".join(parts)


def query_peptide_evidence(peptide_name: str, max_results: int = 10) -> list[dict]:
    """Query CKG for evidence related to a peptide or protein name.

    Returns empty list when the local CKG subset DB is not available.
    """
    return _query_ckg("peptide", peptide_name, max_results)


def query_drug_evidence(drug_name: str, max_results: int = 10) -> list[dict]:
    """Query CKG for drug-target and pharmacology evidence.

    Returns empty list when the local CKG subset DB is not available.
    """
    return _query_ckg("drug", drug_name, max_results)


def query_disease_evidence(disease_name: str, max_results: int = 10) -> list[dict]:
    """Query CKG for disease-associated evidence.

    Returns empty list when the local CKG subset DB is not available.
    """
    return _query_ckg("disease", disease_name, max_results)


# ---------------------------------------------------------------------------
# Internal
# ---------------------------------------------------------------------------


def _query_ckg(entity_type: str, name: str, max_results: int) -> list[dict]:
    """Generic CKG query stub. Returns empty when DB is absent.

    When a filtered SQLite subset of CKG is available at DB_PATH,
    this queries it. Otherwise returns empty for graceful degradation.
    """
    if not os.path.exists(DB_PATH):
        return []

    try:
        import sqlite3

        conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Check what tables exist — CKG subset may have various schemas
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
        tables = {row["name"] for row in cursor.fetchall()}

        results = []
        like_pattern = f"%{name}%"

        # Try domain-specific tables if they exist
        table_map = {
            "peptide": ["uniprot", "protein", "peptide"],
            "drug": ["drugbank", "drug", "compound"],
            "disease": ["disgenet", "oncokb", "disease"],
        }

        candidate_tables = table_map.get(entity_type, [])
        for tbl in candidate_tables:
            if tbl not in tables:
                continue
            # Probe for name/title columns
            cursor.execute(f"PRAGMA table_info({tbl})")
            cols = [row["name"] for row in cursor.fetchall()]
            name_cols = [
                c for c in cols if any(
                    k in c.lower() for k in ["name", "title", "preferred", "gene_symbol"]
                )
            ]
            for nc in name_cols[:2]:
                query = (
                    f"SELECT * FROM {tbl} WHERE {nc} LIKE ? LIMIT ?"
                )
                try:
                    for row in cursor.execute(query, (like_pattern, max_results)):
                        results.append(dict(row))
                except sqlite3.Error:
                    continue

        conn.close()
        return results[:max_results]

    except Exception:
        return []


# ---------------------------------------------------------------------------
# Dataset download helper (documentation only — user runs manually)
# ---------------------------------------------------------------------------

CKG_FILTER_INSTRUCTIONS = """
To build a filtered CKG subset relevant to peptides, amino acids, bodybuilding,
tumors, general health, and SARMs:

1. Clone the full CKG repository:
   git clone https://github.com/MannLabs/CKG.git

2. The CKG uses Neo4j. Export relevant nodes via Cypher queries:
   MATCH (n) WHERE n.source IN ['UniProt','DrugBank','DisGeNET','SIDER',
     'Reactome','HMDB','OncoKB','DGIdb','HPA','STRING']
   RETURN n LIMIT 100000

3. Convert the export to SQLite and place at:
   data/ckg_subset.db

Or download pre-filtered subsets from the Mendeley dump:
   https://data.mendeley.com/datasets/mrcf7f4tc2/1
"""
