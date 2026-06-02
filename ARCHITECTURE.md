# Peptide Research Wiki — Architecture

## Overview

Flask-based web application providing peptide research data, a stack database, progress tracking, and an Ask AI chat feature. All knowledge sources are free — no paid APIs.

## Chat System Architecture

### Data Flow

```
User Message
  │
  ├─ extract_peptide_mentions()  → recognized peptides (via ALIASES + SNAPSHOT_LIBRARY)
  ├─ extract_medical_terms()     → medical keywords (hair loss, diabetes, etc.)
  └─ detect_comparison_query()   → is_comparison boolean
        │
        ▼
 build_research_context(peptides, medical_terms)
   ├─ SNAPSHOT_LIBRARY[peptide]       → clinical profile
   ├─ ClinicalTrials.gov API          → trials
   ├─ NCBI PubMed E-utilities         → articles
   ├─ primekg.query_drug_relations()  → knowledge graph edges
   └─ ckg.get_domain_summary()        → available CKG domains
        │
        ▼
 generate_local_ai_response()
   ├─ Strategy 1: ask_llm.query_ollama()  → local LLM (ministral-3:14b)
   └─ Strategy 2: Synthesized template    → formats research context sections
        │
        ▼
 client ← JSON (POST /ask/message) or SSE stream (GET /ask/stream)
```

### Routes

| Route | Method | Description |
|-------|--------|-------------|
| `/api/ask` | POST | Original research endpoint |
| `/ask/message` | POST | Chat message with JSON response |
| `/ask/stream` | GET | Chat message with SSE streaming |

## Knowledge Sources

### 1. PubMed (NCBI E-utilities)
- **API:** `https://eutils.ncbi.nlm.nih.gov/entrez/eutils/`
- **Free:** Yes, no API key required (3 req/s limit)
- **Cache:** `@lru_cache(maxsize=128)` in `fetch_pubmed()`
- **Integration:** `build_research_context()` → `**Recent Research for {peptide}:**` or `**Research for '{term}':**`

### 2. ClinicalTrials.gov API v2
- **API:** `https://clinicaltrials.gov/api/v2/studies`
- **Free:** Yes, no API key required
- **Cache:** `@lru_cache(maxsize=128)` in `fetch_clinical_trials()`
- **Integration:** `build_research_context()` → `**Clinical Trials for {peptide}:**`

### 3. PrimeKG (Harvard)
- **File:** `primekg.py` — query module, always available
- **Database:** `data/primekg.db` (SQLite, optional, graceful degradation)
- **Lookup:** Entity aliases map (70+ entries) + Jaccard token matching
- **Capabilities:** `query_drug_relations()`, `query_disease_relations()`, `query_protein_targets()`
- **Integration:** `build_research_context()` → `### {peptide} - PrimeKG Knowledge Graph`

### 4. CKG — Clinical Knowledge Graph (MannLab)
- **File:** `ckg.py` — source metadata + graceful-degradation stubs
- **Database:** `data/ckg_subset.db` (optional, 80GB full dump)
- **Domains mapped:** peptides_proteins, drug_targets, disease_associations, side_effects, pathways, metabolites, phenotypes
- **Integration:** `build_research_context()` → `### Clinical Knowledge Graph (CKG) — Available Domains`

### 5. SNAPSHOT_LIBRARY (built-in)
- Curated clinical profiles for known peptides
- Fields: `primary_effect`, `mechanism_pathway`, `expected_body_outcomes`, `clinical_context`

### 6. STACK_KNOWLEDGE (built-in)
- Curated peptide stack descriptions and benefits

## Response Generation

### Strategy 1: Local LLM (Ollama)
- Tried first when available
- Uses `ask_llm.query_ollama()` with `ministral-3:14b` model
- Receives the full `ASK_SYSTEM_PROMPT` + research context as system prompt
- Falls through to Strategy 2 on failure/unavailability

### Strategy 2: Synthesized Template
- Parses research context sections: Snapshots → Trials → PubMed → PrimeKG → CKG
- Handles both peptide research (`Recent Research for`) and general medical research (`Research for '{term}'`)
- Falls back to contextual guidance (not generic) when no research data found

## Deployment

- **Platform:** Vercel (via `vercel.json`)
- **Trigger:** Auto-deploys from `main` branch on GitHub push
- **Build:** `@vercel/python` build
- **Entry:** `app.py`

## Key Files

| File | Purpose |
|------|---------|
| `app.py` | Main Flask application, routes, chat logic, knowledge source integration |
| `ask_llm.py` | Ollama integration, PubMed search, Wikipedia search |
| `primekg.py` | PrimeKG knowledge graph query module |
| `ckg.py` | CKG knowledge graph source metadata + query stubs |
| `chat.js` | Frontend chat UI with SSE streaming |
| `ask.js` | Ask page frontend logic |
| `templates/ask.html` | Chat UI template |
| `templates/index.html` | Home page |
| `templates/stacks.html` | Stack database |
| `templates/tracker.html` | Progress tracker |
| `vercel.json` | Vercel deployment config |

## Version

Tracked via `VERSION` constant in `app.py`, displayed as version badge in all page footers.
