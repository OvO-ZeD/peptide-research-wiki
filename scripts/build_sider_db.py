"""
Build the SIDER side effect SQLite database.

Downloads meddra_all_se.tsv.gz and drug_names.tsv from EMBL,
creates data/sider.db with indexed drug-side effect tables.

Usage:
  python scripts/build_sider_db.py
"""

import gzip
import csv
import io
import os
import sqlite3
import urllib.request

BASE_URL = "http://sideeffects.embl.de/media/download"
DB_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
DB_PATH = os.path.join(DB_DIR, "sider.db")

SE_FILE = "meddra_all_se.tsv.gz"
NAMES_FILE = "drug_names.tsv"


def download_text(url):
    """Download a file and return its text content."""
    print(f"  Downloading {url} ...")
    req = urllib.request.Request(url, headers={"User-Agent": "PeptideDB/1.0"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return resp.read()


def main():
    os.makedirs(DB_DIR, exist_ok=True)

    # ── Download files ──
    print("Downloading SIDER data files ...")

    # meddra_all_se.tsv.gz
    se_gz = download_text(f"{BASE_URL}/{SE_FILE}")
    se_text = gzip.decompress(se_gz).decode("utf-8")
    se_reader = csv.reader(io.StringIO(se_text), delimiter="\t")

    # drug_names.tsv
    names_text = download_text(f"{BASE_URL}/{NAMES_FILE}").decode("utf-8")
    names_reader = csv.reader(io.StringIO(names_text), delimiter="\t")

    # ── Build drug name → STITCH CID mapping ──
    print("Building drug name mapping ...")
    name_to_cid = {}
    for row in names_reader:
        if len(row) >= 2:
            cid = row[0].strip()
            name = row[1].strip().lower()
            if cid and name:
                name_to_cid[name] = cid
                # Also add without common prefixes
                for prefix in ["cid", "cid100000"]:
                    if cid.lower().startswith(prefix):
                        short = cid[len(prefix):]
                        name_to_cid[short] = cid

    print(f"  Mapped {len(name_to_cid)} drug names")

    # ── Parse side effects ──
    print("Parsing side effect records ...")
    rows = []
    for row in se_reader:
        if len(row) < 6:
            continue
        stitch_flat = row[0].strip()
        stitch_stereo = row[1].strip()
        umls_label = row[2].strip()
        meddra_type = row[3].strip()
        umls_meddra = row[4].strip()
        se_name = row[5].strip()

        drug_name = stitch_flat
        # Skip if no meaningful data
        if not se_name or not stitch_flat:
            continue

        rows.append({
            "drug_id": stitch_flat,
            "drug_stereo": stitch_stereo,
            "umls_label_cui": umls_label,
            "meddra_type": meddra_type,
            "umls_meddra_cui": umls_meddra,
            "side_effect": se_name,
        })

    print(f"  Parsed {len(rows)} drug-side effect pairs from {SE_FILE}")

    # ── Build name lookup from CIDs ──
    # Also try to extract names from the se_reader data itself
    # side effects data has drug_id as STITCH compound IDs like CID100000085
    # We'll look these up in the name_to_cid map

    # Create reverse mapping: stitch_cid → drug_name(s) from drug_names.tsv
    cid_to_names = {}
    for name, cid in name_to_cid.items():
        if cid not in cid_to_names:
            cid_to_names[cid] = []
        cid_to_names[cid].append(name)

    # ── Create SQLite database ──
    print(f"Creating database at {DB_PATH} ...")
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS side_effects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            drug_id TEXT,
            drug_stereo TEXT,
            drug_name TEXT,
            umls_label_cui TEXT,
            meddra_type TEXT,
            umls_meddra_cui TEXT,
            side_effect TEXT
        )
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_side_effects_drug_name
        ON side_effects(drug_name)
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_side_effects_side_effect
        ON side_effects(side_effect)
    """)

    insert_sql = """
        INSERT INTO side_effects (drug_id, drug_stereo, drug_name, umls_label_cui,
                                   meddra_type, umls_meddra_cui, side_effect)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """

    inserted = 0
    for r in rows:
        drug_id = r["drug_id"]
        # Try to resolve drug name from CID
        names = cid_to_names.get(drug_id, [])
        drug_name = names[0] if names else drug_id

        cursor.execute(insert_sql, (
            r["drug_id"],
            r["drug_stereo"],
            drug_name,
            r["umls_label_cui"],
            r["meddra_type"],
            r["umls_meddra_cui"],
            r["side_effect"],
        ))
        inserted += 1

        # Also add under each alias name for better search coverage
        for n in names[1:]:
            cursor.execute(insert_sql, (
                r["drug_id"],
                r["drug_stereo"],
                n,
                r["umls_label_cui"],
                r["meddra_type"],
                r["umls_meddra_cui"],
                r["side_effect"],
            ))

    conn.commit()

    # ── Stats ──
    cursor.execute("SELECT COUNT(*) FROM side_effects")
    total = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(DISTINCT drug_name) FROM side_effects")
    distinct_drugs = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(DISTINCT side_effect) FROM side_effects")
    distinct_se = cursor.fetchone()[0]

    conn.close()

    print(f"\nDone! Database stats:")
    print(f"  Total records:     {total:,}")
    print(f"  Unique drugs:      {distinct_drugs:,}")
    print(f"  Unique side effects: {distinct_se:,}")
    print(f"  Database size:     {os.path.getsize(DB_PATH) / 1024 / 1024:.1f} MB")
    print(f"\nDatabase location: {DB_PATH}")


if __name__ == "__main__":
    main()
