# CLAUDE.md

Behavioral guidelines to reduce common LLM coding mistakes. Merge with project-specific instructions as needed.

**Tradeoff:** These guidelines bias toward caution over speed. For trivial tasks, use judgment.

## 1. Think Before Coding

**Don't assume. Don't hide confusion. Surface tradeoffs.**

Before implementing:
- State your assumptions explicitly. If uncertain, ask.
- If multiple interpretations exist, present them — don't pick silently.
- If a simpler approach exists, say so. Push back when warranted.
- If something is unclear, stop. Name what's confusing. Ask.

## 2. Simplicity First

**Minimum code that solves the problem. Nothing speculative.**

- No features beyond what was asked.
- No abstractions for single-use code.
- No "flexibility" or "configurability" that wasn't requested.
- No error handling for impossible scenarios.
- If you write 200 lines and it could be 50, rewrite it.

Ask yourself: "Would a senior engineer say this is overcomplicated?" If yes, simplify.

## 3. Surgical Changes

**Touch only what you must. Clean up only your own mess.**

When editing existing code:
- Don't "improve" adjacent code, comments, or formatting.
- Don't refactor things that aren't broken.
- Match existing style, even if you'd do it differently.
- If you notice unrelated dead code, mention it — don't delete it.

When your changes create orphans:
- Remove imports/variables/functions that YOUR changes made unused.
- Don't remove pre-existing dead code unless asked.

The test: Every changed line should trace directly to the user's request.

## 4. Goal-Driven Execution

**Define success criteria. Loop until verified.**

Transform tasks into verifiable goals:
- "Add validation" → "Write tests for invalid inputs, then make them pass"
- "Fix the bug" → "Write a test that reproduces it, then make it pass"
- "Refactor X" → "Ensure tests pass before and after"

For multi-step tasks, state a brief plan:
```
1. [Step] → verify: [check]
2. [Step] → verify: [check]
3. [Step] → verify: [check]
```

Strong success criteria let you loop independently. Weak criteria ("make it work") require constant clarification.

---

## 5. Token Efficiency — Use Semble

**Semble** is installed as an MCP tool and sub-agent. It returns only the relevant code snippets, using ~98% fewer tokens than grep+read.

**Priority order for code navigation:**
1. **`search` tool** (MCP — `semble search`) — Find code by describing intent. Always prefer this first.
2. **`semble search`** (via sub-agent) — For complex multi-file investigations.
3. **`grep`** — Only when you need exhaustive literal matches or exact string confirmation.
4. **`Read`** (full file) — Only when the snippet from Semble doesn't give enough context.

**When to use:**
- Looking for a function, route, or pattern → `search "what does X do" ./repo`
- Understanding a code area → `semble search` then `semble find-related`
- Need exact locations → `semble search "symbol_name" ./repo`

**Don't grep+read blindly when Semble can find the exact chunk.**

---

## Project-Specific: Peptide Research Wiki

**Stack:** Flask, Jinja2 templates, SQLite (SIDER/PrimeKG/DrugBank), Ollama (local LLM)

**Key files:**
- `app.py` — Flask app, all routes, template logic, peptide matching
- `ask_llm.py` — Ollama integration, PubMed/ Wikipedia API calls
- `sider_db.py` / `primekg.py` / `ckg.py` / `drugbank.py` — database modules
- `templates/ask.html` — Chat UI page
- `vercel.json` — Vercel serverless deployment config

**Critical rules:**
- Template answers (from `STACK_KNOWLEDGE` / `EFFECT_KEYWORDS` / local data) MUST NEVER be overridden by raw PubMed/Wikipedia dumps
- External API calls (PubMed, ClinicalTrials) can time out on Vercel — always have local fallback
- Ollama runs at `localhost:11434` — use `llama3.1:8b` for medical questions
- Session memory is IP-keyed via `_conversation_history` dict
- Always include `sources` array in JSON responses
- Version badge in style.css (`.version-badge`)

**Testing:** Run locally with `python app.py` or `uvicorn server:app` for Vercel mode.

---

**These guidelines are working if:** fewer unnecessary changes in diffs, fewer rewrites due to overcomplication, and clarifying questions come before implementation rather than after mistakes.
