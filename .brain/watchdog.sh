#!/bin/bash
# Session Brain Watchdog
# Runs via cron every 2 minutes. Detects when a Claude Code session
# ends abruptly (terminal close, Ctrl+C, VS Code close, etc.) and
# finalizes the session log automatically.
#
# How it works:
#   1. Scans .brain/ for session files with 'end_time: active'
#   2. Checks if claude or code (VS Code) process is still running
#   3. If no relevant process found AND session is >5 min old → finalize

BRAIN_DIR="$(cd "$(dirname "$0")" && pwd)"

# Find active session files (end_time: active, not template/INDEX)
find "$BRAIN_DIR" -maxdepth 1 -name '*.md' \
  ! -name 'INDEX.md' \
  ! -name '_session_template.md' \
  ! -name '_*' \
  -exec grep -l 'end_time: active' {} \; 2>/dev/null | while read -r session_file; do

  # Check if claude or VS Code process is running
  CLAUDE_RUNNING=false
  if pgrep -x claude >/dev/null 2>&1 || pgrep -x code >/dev/null 2>&1; then
    CLAUDE_RUNNING=true
  fi

  if [ "$CLAUDE_RUNNING" = false ]; then
    # Check if file is older than 5 minutes (avoid false positives during brief pauses)
    NOW=$(date +%s)
    FILE_MTIME=$(stat -c %Y "$session_file" 2>/dev/null)
    if [ -n "$FILE_MTIME" ]; then
      AGE=$((NOW - FILE_MTIME))
      if [ $AGE -gt 300 ]; then
        # Finalize the session
        END_TIME=$(date +%H%M)
        SESSION_NAME=$(basename "$session_file" .md)

        echo "[$(date)] Finalizing interrupted session: $SESSION_NAME"

        # Replace end_time: active with end_time: HHMM
        sed -i "s/end_time: active/end_time: ${END_TIME} (interrupted)/" "$session_file"

        # Append interruption note if not already present
        if ! grep -q "⚠ Session interrupted" "$session_file"; then
          cat >> "$session_file" <<- EOF

---

## ⚠ Session interrupted
This session was automatically finalized by the watchdog on $(date '+%Y-%m-%d %H:%M') because Claude Code exited (terminal closed, Ctrl+C, or VS Code shutdown).
EOF
        fi

        echo "[$(date)] ✓ Finalized: $SESSION_NAME at $END_TIME"
      fi
    fi
  fi
done
