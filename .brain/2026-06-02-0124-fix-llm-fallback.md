---
date: 2026-06-02
start_time: 0124
end_time: active
tags: [fix, fallback, ollama, karpathy, brain]
focus: Fix LLM fallback overriding template answers, add Karpathy guidelines, set up brain
---

# Session: Fix LLM fallback, Karpathy guidelines, Brain setup

## Summary
Fixed critical bug where PubMed/Wikipedia fallback was overriding local template answers. Switched Ollama model to llama3.1:8b. Added Karpathy-inspired coding guidelines to CLAUDE.md. Set up persistent session brain system (.brain/ directory) for cross-session memory.

## Changes Made
- `app.py` — Restructured fallback logic: Ollama improvement now uses local data directly; PubMed/Wikipedia only fires when answer_parts is truly empty; added safety guard for matched_peptides edge case
- `app.py` — Ollama call now uses `ask_llm.query_ollama()` directly with local template context instead of `ask_llm.generate_answer()` (which did separate PubMed API call)
- `ask_llm.py` — Switched `DEFAULT_MODEL` from `ministral-3:14b` to `llama3.1:8b`
- `CLAUDE.md` — Created with merged Karpathy guidelines + project-specific rules + Semble token efficiency section
- `.brain/` — Created session memory system (Obsidian-compatible vault with INDEX.md, session logs, template)
- `.brain/watchdog.sh` — Cron watchdog that detects abrupt session end (terminal close, Ctrl+C, VS Code close) and auto-finalizes session logs
- `.brain/watchdog.log` — Watchdog activity log
- `.brain/open-brain.sh` — Helper to open vault in Obsidian
- `crontab` — Added `*/2 * * * *` entry for watchdog
- `.claude/agents/semble-search.md` — Semble sub-agent for token-efficient code search
- `.claude.json` — Semble MCP server added

## Key Decisions
- **Fallback restructure**: Try Ollama to improve template, but NEVER let PubMed/Wikipedia dump replace a valid local answer
- **Model choice**: `llama3.1:8b` over `ministral-3:14b` — better general model for medical Q&A
- **Brain location**: `.brain/` in project root so it's portable and doubles as Obsidian vault
- **Karpathy principles**: Four rules (Think First, Simplicity, Surgical, Goal-Driven) merged into project CLAUDE.md
- **Semble**: MCP + sub-agent + CLAUDE.md section — replaces grep+read for code search, ~98% fewer tokens

## Key Decisions
- **Fallback restructure**: Try Ollama to improve template, but NEVER let PubMed/Wikipedia dump replace a valid local answer
- **Model choice**: `llama3.1:8b` over `ministral-3:14b` — better general model for medical Q&A
- **Brain location**: `.brain/` in project root so it's portable and doubles as Obsidian vault
- **Karpathy principles**: Four rules (Think First, Simplicity, Surgical, Goal-Driven) merged into project CLAUDE.md

## Fixed Issues
- **Bug**: PubMed dump was overriding template answers for queries like "Best peptides for gut healing"
- **Root cause**: `should_use_llm = True` forced code into Ollama → PubMed fallback even when template had valid content. When Ollama failed (Vercel), raw PubMed dump replaced the answer.
- **Fix**: Separated "try to improve with Ollama" from "fall back to external sources" — they're now independent blocks. External sources only used when answer_parts is empty AND no local matches exist.

## Verified / Tested
- [x] Syntax verified on both app.py and ask_llm.py
- [x] Ollama models confirmed: llama3.1:8b, ministral-3:14b, qwen2.5-coder:7b, lfm2.5-thinking:1.2b, qwen2.5:3b all available
- [ ] Need user to test "Best peptides for gut healing" on live site to confirm fix

## Pending
- [ ] Verify fix on live site (user reported seeing Wikipedia results)
- [ ] DrugBank database not built (requires manual XML download)
- [ ] SIDER DB not on Vercel (data/ is gitignored)
- [ ] Chat UI positioning issue ("on top") may need CSS check

## Related Sessions
- (first session in brain system)
