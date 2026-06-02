"""
Build the DrugBank SQLite database from the open-access XML.

Parses DrugBank's XML format (open-access subset) using streaming
XML parsing to handle large files efficiently.

Prerequisites:
  Register at https://go.drugbank.com/ and download the
  "Full Open-Access XML" (~200 MB). Place it at data/drugbank.xml

Usage:
  python scripts/build_drugbank_db.py
"""

import os
import sqlite3
import xml.etree.ElementTree as ET

DB_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
DB_PATH = os.path.join(DB_DIR, "drugbank.db")
XML_PATH = os.path.join(DB_DIR, "drugbank.xml")

NS = "{http://www.drugbank.ca}"


def safe_text(elem, tag):
    """Get text content of a child element, or None."""
    child = elem.find(f"{NS}{tag}")
    if child is not None and child.text:
        return child.text.strip()
    return None


def safe_text_list(elem, tag):
    """Get text from all children with given tag."""
    return [c.text.strip() for c in elem.findall(f"{NS}{tag}") if c.text]


def main():
    if not os.path.exists(XML_PATH):
        print(f"DrugBank XML not found at: {XML_PATH}")
        print()
        print("To download:")
        print("  1. Register at https://go.drugbank.com/ (free academic account)")
        print(f"  2. Download 'Full Open-Access XML' to {XML_PATH}")
        print("  3. Run this script again")
        return

    print(f"Parsing DrugBank XML: {XML_PATH}")
    print("(this may take a few minutes for ~200 MB XML)")

    os.makedirs(DB_DIR, exist_ok=True)
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # ── Schema ──
    cursor.executescript("""
        CREATE TABLE IF NOT EXISTS drugs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            drugbank_id TEXT UNIQUE,
            name TEXT,
            drug_type TEXT,
            description TEXT,
            mechanism_of_action TEXT,
            indication TEXT,
            pharmacodynamics TEXT,
            toxicity TEXT,
            half_life TEXT
        );

        CREATE TABLE IF NOT EXISTS drug_targets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            drugbank_id TEXT,
            drug_name TEXT,
            target_id TEXT,
            target_name TEXT,
            target_gene TEXT,
            organism TEXT,
            action TEXT
        );

        CREATE TABLE IF NOT EXISTS drug_interactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            drugbank_id TEXT,
            drug_name TEXT,
            other_drugbank_id TEXT,
            other_drug TEXT,
            description TEXT
        );

        CREATE INDEX IF NOT EXISTS idx_drugs_name ON drugs(name);
        CREATE INDEX IF NOT EXISTS idx_drug_targets_drug ON drug_targets(drug_name);
        CREATE INDEX IF NOT EXISTS idx_drug_interactions_drug ON drug_interactions(drug_name);
    """)

    # ── Stream parse XML ──
    count = 0
    errors = 0

    # Use iterparse to stream through elements
    for event, elem in ET.iterparse(XML_PATH, events=("end",)):
        if elem.tag != f"{NS}drug":
            continue

        try:
            drug_id = safe_text(elem, "drugbank-id")
            name = safe_text(elem, "name")
            drug_type = elem.get("type", "")

            if not drug_id or not name:
                elem.clear()
                continue

            description = safe_text(elem, "description") or ""
            mechanism = safe_text(elem, "mechanism-of-action") or ""
            indication = safe_text(elem, "indication") or ""
            pharmacodynamics = safe_text(elem, "pharmacodynamics") or ""
            toxicity = safe_text(elem, "toxicity") or ""
            half_life = safe_text(elem, "half-life") or ""

            cursor.execute("""
                INSERT OR IGNORE INTO drugs
                    (drugbank_id, name, drug_type, description,
                     mechanism_of_action, indication, pharmacodynamics, toxicity, half_life)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (drug_id, name, drug_type, description,
                  mechanism, indication, pharmacodynamics, toxicity, half_life))

            # ── Targets ──
            targets = elem.find(f"{NS}targets")
            if targets is not None:
                for target in targets.findall(f"{NS}target"):
                    tid = safe_text(target, "id") or ""
                    tname = safe_text(target, "name") or ""
                    organism = safe_text(target, "organism") or ""
                    actions = safe_text_list(target, "actions")
                    action_str = "; ".join(actions) if actions else ""

                    # Get gene from polypeptide
                    gene = ""
                    poly = target.find(f"{NS}polypeptide")
                    if poly is not None:
                        gene = safe_text(poly, "gene") or ""

                    cursor.execute("""
                        INSERT INTO drug_targets
                            (drugbank_id, drug_name, target_id, target_name, target_gene, organism, action)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (drug_id, name, tid, tname, gene, organism, action_str))

            # ── Drug interactions ──
            interactions = elem.find(f"{NS}drug-interactions")
            if interactions is not None:
                for inter in interactions.findall(f"{NS}drug-interaction"):
                    other_id = safe_text(inter, "drugbank-id") or ""
                    other_name = safe_text(inter, "name") or ""
                    desc = safe_text(inter, "description") or ""

                    cursor.execute("""
                        INSERT INTO drug_interactions
                            (drugbank_id, drug_name, other_drugbank_id, other_drug, description)
                        VALUES (?, ?, ?, ?, ?)
                    """, (drug_id, name, other_id, other_name, desc))

            count += 1
            if count % 500 == 0:
                print(f"  Processed {count} drugs ...")
                conn.commit()

        except Exception as e:
            errors += 1
            if errors <= 5:
                print(f"  Error on drug #{count + 1}: {e}")

        # Free memory
        elem.clear()

    conn.commit()

    # ── Stats ──
    cursor.execute("SELECT COUNT(*) FROM drugs")
    total_drugs = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM drug_targets")
    total_targets = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM drug_interactions")
    total_interactions = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(DISTINCT name) FROM drugs WHERE mechanism_of_action != ''")
    with_mechanism = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(DISTINCT name) FROM drugs WHERE indication != ''")
    with_indication = cursor.fetchone()[0]

    conn.close()

    print(f"\nDone! Database stats:")
    print(f"  Drugs:                {total_drugs:,}")
    print(f"  Drug targets:          {total_targets:,}")
    print(f"  Drug interactions:     {total_interactions:,}")
    print(f"  With mechanism:        {with_mechanism:,}")
    print(f"  With indication:       {with_indication:,}")
    print(f"  Database size:         {os.path.getsize(DB_PATH) / 1024 / 1024:.1f} MB")
    print(f"\nDatabase location: {DB_PATH}")


if __name__ == "__main__":
    main()
