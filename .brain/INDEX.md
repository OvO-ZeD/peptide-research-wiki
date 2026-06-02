# 🧠 Session Brain — Peptide Research Wiki

**Last updated:** 2026-06-02

This is the persistent memory for the Peptide Research Wiki project. Each session is logged here for cross-session recall. Also works as an Obsidian vault — open this `.brain/` folder in Obsidian.

## How to use
- **Start of session**: Read this INDEX.md to see context
- **During session**: Reference [[2026-06-02-0124-fix-llm-fallback]] and other past logs
- **End of session**: No manual step needed — cron watchdog (`watchdog.sh`, runs every 2 min) auto-finalizes when Claude exits
- **To view logs**: Open `.brain/` in Obsidian via `bash .brain/open-brain.sh`
- **Obsidian**: All [[wikilinks]] resolve, tags work, graph view shows connections

## Sessions

| Date | Session | Summary |
|------|---------|---------|
| 2026-06-02 | [[2026-06-02-0124-fix-llm-fallback]] | Fixed Ollama fallback, llama3.1:8b, Karpathy guidelines, brain + watchdog, Semble code search (~98% fewer tokens) |

## Key Decisions (all sessions)

| # | Decision | Rationale |
|---|----------|-----------|
| D001 | Template answers must NEVER be overridden by raw PubMed/Wikipedia dumps | User reported generic/irrelevant answers. Root cause: `should_use_llm` forced fallback even with valid local data |
| D002 | Use `llama3.1:8b` for Ollama | Better general model for medical Q&A than `ministral-3:14b` |
| D003 | Karpathy 4 principles apply to all coding | User request: Think First, Simplicity, Surgical, Goal-Driven |
| D004 | Session brain as .brain/ directory | Portable with project, doubles as Obsidian vault, markdown-native |

## Active Concerns

- [ ] DrugBank database not built (requires manual XML download)
- [ ] SIDER DB built locally but not on Vercel (data/ is gitignored)
- [ ] PubMed/ClinicalTrials external API calls may time out on Vercel
- [ ] Chat UI positioning issue reported ("on top") — may need CSS check

## Templates

See [[_session_template]] for session log format.
New sessions: `YYYY-MM-DD-HHMM-brief-slug.md`
