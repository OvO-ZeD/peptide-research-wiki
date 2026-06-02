"""
Build PrimeKG filtered SQLite database for PeptideDB.

Downloads the PrimeKG CSV from Harvard Dataverse, filters to edges relevant
to PeptideDB's peptides, conditions, and high-value relationship types,
then writes a compact SQLite database to data/primekg.db.

Usage:
    python scripts/build_primekg_db.py
"""

import csv
import json
import os
import re
import sqlite3
import sys
import urllib.request
from io import StringIO

PRIMEKG_URL = "https://dataverse.harvard.edu/api/access/datafile/6180620"
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "primekg.db")
MAPPING_REPORT_PATH = os.path.join(os.path.dirname(__file__), "entity_mapping.json")
CSV_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "primekg.csv")

HIGH_VALUE_RELATIONS = {
    "indication", "contraindication", "off-label use",
    "drug_protein", "disease_protein", "disease_disease",
    "drug_disease", "protein_disease",
}


def load_peptidedb_terms():
    """Import PeptideDB data structures to build interest terms."""
    sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
    import app

    terms = set()
    # Normalize helper
    def normalize(name):
        return name.lower().strip().replace("_", " ").replace("-", " ")

    # STACK_KNOWLEDGE keys (peptide names)
    for key in app.STACK_KNOWLEDGE:
        terms.add(key.lower())
        terms.add(normalize(key))

    # ALIASES values (canonical names)
    for val in app.ALIASES.values():
        terms.add(val.lower())
        terms.add(normalize(val))

    # SYMPTOM_CONDITION_MAP keys (conditions)
    for key in app.SYMPTOM_CONDITION_MAP:
        terms.add(key.lower())
        terms.add(normalize(key))

    # SNAPSHOT_LIBRARY keys
    for key in app.SNAPSHOT_LIBRARY:
        terms.add(key.lower())

    # EFFECT_LABELS
    for label in app.EFFECT_LABELS.values():
        terms.add(label.lower())

    # REGULATORY_STATUS keys
    for key in app.REGULATORY_STATUS:
        terms.add(key.lower())

    # Safety notes keys
    for key in app.SAFETY_NOTES:
        if key != "general":
            terms.add(key.lower())

    # Extract mechanism/pathway terms from SNAPSHOT_LIBRARY
    for snap in app.SNAPSHOT_LIBRARY.values():
        for field in ["primary_effect", "mechanism_pathway", "expected_body_outcomes"]:
            text = snap.get(field, "")
            if text:
                words = re.findall(r'[a-zA-Z-]+', text)
                for w in words:
                    if len(w) > 4:
                        terms.add(w.lower())

    # Clean and deduplicate
    cleaned = set()
    for t in terms:
        t = t.strip()
        if len(t) > 2:
            cleaned.add(t)
            # Also add individual tokens for better matching
            tokens = re.findall(r'[a-z0-9]+', t)
            for tok in tokens:
                if len(tok) > 2 and tok not in ("the", "and", "for", "with", "type", "vs"):
                    cleaned.add(tok)

    print(f"  Loaded {len(cleaned)} interest terms from PeptideDB")
    return cleaned


def download_csv():
    """Download PrimeKG CSV if not already present. Returns path."""
    if os.path.exists(CSV_PATH):
        file_size = os.path.getsize(CSV_PATH)
        print(f"  Using existing CSV: {CSV_PATH} ({file_size / 1024 / 1024:.1f} MB)")
        return CSV_PATH

    print(f"  Downloading PrimeKG from Harvard Dataverse...")
    print(f"  URL: {PRIMEKG_URL}")
    print(f"  This is a ~1.8 GB file, may take several minutes...")

    # Harvard Dataverse requires a browser User-Agent
    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }

    try:
        req = urllib.request.Request(PRIMEKG_URL, headers=headers)
        with urllib.request.urlopen(req) as response:
            total_size = int(response.headers.get("Content-Length", 0))
            downloaded = 0
            with open(CSV_PATH, "wb") as f:
                while True:
                    chunk = response.read(8192 * 1024)  # 8MB chunks
                    if not chunk:
                        break
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total_size > 0:
                        pct = downloaded / total_size * 100
                        print(f"\r  Downloaded: {downloaded / 1024 / 1024:.0f} MB / {total_size / 1024 / 1024:.0f} MB ({pct:.1f}%)", end="")
                    else:
                        print(f"\r  Downloaded: {downloaded / 1024 / 1024:.0f} MB...", end="")
        print()
        file_size = os.path.getsize(CSV_PATH)
        print(f"  Download complete: {file_size / 1024 / 1024:.1f} MB")
        return CSV_PATH
    except Exception as e:
        print(f"\n  Download failed: {e}")
        return None


def interest_matches(name, interest_terms):
    """Check if a name (from PrimeKG) matches any PeptideDB interest term.

    Uses fast substring matching (set membership + token-in-term check)
    to avoid O(N*M) per row.
    """
    if not name:
        return False
    nl = name.lower().strip()
    # Fast exact match
    if nl in interest_terms:
        return True
    # Token-by-token check: if ANY token from the name is a substring
    # of any interest term (or vice versa), it's a match.
    # This avoids iterating all interest terms for every row.
    name_tokens = set(re.findall(r'[a-z0-9]+', nl))
    if name_tokens & interest_terms:
        return True
    # Multi-word name check: does the entire lowercase name appear
    # as a substring of any interest term (or vice versa)?
    # Limited to short names for performance.
    if len(nl) < 50:
        for term in interest_terms:
            if nl in term or term in nl:
                return True
    return False


def build_database(csv_path, interest_terms):
    """Stream CSV line-by-line, filter edges, write to SQLite."""
    print(f"  Reading CSV and filtering edges...")

    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=OFF")
    conn.execute("PRAGMA synchronous=OFF")

    conn.executescript("""
        CREATE TABLE IF NOT EXISTS edges (
            row_id INTEGER PRIMARY KEY,
            relation TEXT NOT NULL,
            display_relation TEXT,
            x_type TEXT,
            x_name TEXT,
            x_id TEXT,
            x_source TEXT,
            y_type TEXT,
            y_name TEXT,
            y_id TEXT,
            y_source TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_edges_x_name ON edges(x_name);
        CREATE INDEX IF NOT EXISTS idx_edges_y_name ON edges(y_name);
        CREATE INDEX IF NOT EXISTS idx_edges_relation ON edges(relation);
        CREATE INDEX IF NOT EXISTS idx_edges_x_id ON edges(x_id);
        CREATE INDEX IF NOT EXISTS idx_edges_y_id ON edges(y_id);
    """)

    total_rows = 0
    kept_rows = 0
    insert_batch = []
    matched_entities = set()

    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        headers = next(reader)
        print(f"  Columns: {headers}")

        col_map = {h.strip().lower(): i for i, h in enumerate(headers)}
        rel_idx = col_map.get("relation", 0)
        display_rel_idx = col_map.get("display_relation", 1)
        x_type_idx = col_map.get("x_type", 2)
        x_name_idx = col_map.get("x_name", 4)
        x_id_idx = col_map.get("x_id", 3)
        x_source_idx = col_map.get("x_source", 5)
        y_type_idx = col_map.get("y_type", 8)
        y_name_idx = col_map.get("y_name", 9)
        y_id_idx = col_map.get("y_id", 8)
        y_source_idx = col_map.get("y_source", 10)

        for row in reader:
            total_rows += 1
            if total_rows % 500000 == 0:
                print(f"    Processed {total_rows:,} rows, kept {kept_rows:,}")

            relation = row[rel_idx].strip().lower() if len(row) > rel_idx else ""
            x_name = row[x_name_idx].strip() if len(row) > x_name_idx else ""
            y_name = row[y_name_idx].strip() if len(row) > y_name_idx else ""

            # Only keep edges relevant to PeptideDB: must match an interest
            # term AND be a high-value biomedical relation type.
            # This keeps the database small enough for Vercel deployment.
            matches_x = interest_matches(x_name, interest_terms)
            matches_y = interest_matches(y_name, interest_terms)
            keep = (matches_x or matches_y) and relation in HIGH_VALUE_RELATIONS

            if keep:
                kept_rows += 1
                if x_name:
                    matched_entities.add(x_name.lower())
                if y_name:
                    matched_entities.add(y_name.lower())
                insert_batch.append((
                    relation,
                    row[display_rel_idx].strip() if len(row) > display_rel_idx else "",
                    row[x_type_idx].strip() if len(row) > x_type_idx else "",
                    x_name,
                    row[x_id_idx].strip() if len(row) > x_id_idx else "",
                    row[x_source_idx].strip() if len(row) > x_source_idx else "",
                    row[y_type_idx].strip() if len(row) > y_type_idx else "",
                    y_name,
                    row[y_id_idx].strip() if len(row) > y_id_idx else "",
                    row[y_source_idx].strip() if len(row) > y_source_idx else "",
                ))

            if len(insert_batch) >= 10000:
                conn.executemany(
                    "INSERT INTO edges (relation, display_relation, x_type, x_name, x_id, x_source, "
                    "y_type, y_name, y_id, y_source) VALUES (?,?,?,?,?,?,?,?,?,?)",
                    insert_batch
                )
                conn.commit()
                insert_batch = []

    # Final batch
    if insert_batch:
        conn.executemany(
            "INSERT INTO edges (relation, display_relation, x_type, x_name, x_id, x_source, "
            "y_type, y_name, y_id, y_source) VALUES (?,?,?,?,?,?,?,?,?,?)",
            insert_batch
        )
        conn.commit()

    print(f"  Total rows: {total_rows:,}")
    print(f"  Kept rows: {kept_rows:,}")

    # Build entity lookup table
    print(f"  Building entity lookup table...")
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS entities (
            entity_id TEXT,
            entity_name TEXT,
            entity_type TEXT,
            source TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_entities_name ON entities(entity_name);
        CREATE INDEX IF NOT EXISTS idx_entities_type ON entities(entity_type);
    """)
    conn.execute("""
        INSERT OR IGNORE INTO entities (entity_id, entity_name, entity_type, source)
        SELECT DISTINCT x_id, x_name, x_type, x_source FROM edges
        UNION
        SELECT DISTINCT y_id, y_name, y_type, y_source FROM edges
    """)
    conn.commit()

    # Analyze
    conn.execute("ANALYZE")

    db_size = os.path.getsize(DB_PATH)
    print(f"  Database size: {db_size / 1024 / 1024:.1f} MB")

    # Build mapping report
    entity_count = conn.execute("SELECT COUNT(*) FROM entities").fetchone()[0]
    relation_counts = {}
    conn.close()

    conn = sqlite3.connect(DB_PATH)
    for row in conn.execute("SELECT relation, COUNT(*) as cnt FROM edges GROUP BY relation ORDER BY cnt DESC"):
        relation_counts[row[0]] = row[1]
    conn.close()

    report = {
        "total_primekg_rows": total_rows,
        "filtered_rows": kept_rows,
        "unique_entities": entity_count,
        "relation_type_counts": relation_counts,
        "matched_entity_examples": sorted(matched_entities)[:100],
    }

    with open(MAPPING_REPORT_PATH, "w") as f:
        json.dump(report, f, indent=2)
    print(f"  Mapping report written to {MAPPING_REPORT_PATH}")

    return report


def main():
    print("=== PrimeKG Database Builder ===")
    print()

    # Step 1: Load PeptideDB interest terms
    print("[1/4] Loading PeptideDB terms...")
    interest_terms = load_peptidedb_terms()

    # Step 2: Download CSV
    print("[2/4] Checking/downloading PrimeKG CSV...")
    csv_path = download_csv()
    if not csv_path:
        print("ERROR: Could not download PrimeKG CSV. Aborting.")
        sys.exit(1)

    # Step 3: Filter and build database
    print("[3/4] Building filtered SQLite database...")
    report = build_database(csv_path, interest_terms)

    # Step 4: Summary
    print("[4/4] Build complete!")
    print()
    print("=== Summary ===")
    print(f"  Database: {DB_PATH}")
    print(f"  Total PrimeKG rows: {report['total_primekg_rows']:,}")
    print(f"  Filtered edges kept: {report['filtered_rows']:,}")
    print(f"  Unique entities: {report['unique_entities']:,}")
    print(f"  Relation types found: {len(report['relation_type_counts'])}")
    for rel, cnt in list(report['relation_type_counts'].items())[:10]:
        print(f"    {rel}: {cnt:,}")
    print()


if __name__ == "__main__":
    main()
