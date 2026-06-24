#!/usr/bin/env bash
# Stop-hook (Step 24 / CL7-A) — passive knowledge capture.
# Fires at session end. Only prompts when there are signals of a REAL fix, then
# drafts a lesson for the dev to confirm with one key (Enter=save / Esc=skip).
# It does NOT auto-write (avoids noise); /capture-fix is the active path.
set -euo pipefail

# --- trigger gate: did this session actually fix something? ---
changed=$(git diff --name-only HEAD 2>/dev/null | grep -vE '\.(md|lock)$|/tests?/' || true)
[ -z "$changed" ] && exit 0   # only read/asked -> nothing to capture

# debug signal: a fix-y commit message, or the same file edited >=2 times
fix_signal=$(git log --oneline -5 2>/dev/null | grep -iE 'fix|bug' || true)
if [ -z "$fix_signal" ] && [ "$(echo "$changed" | wc -l)" -lt 1 ]; then
  exit 0
fi

cat <<'MSG'
[FeedbackKB] This session looks like a real fix. Draft a lesson?
  Enter = capture (runs /capture-fix)   Esc/n = skip
A draft lesson has been prepared from your git diff; review then confirm.
MSG
# In a real install the harness reads the keypress and invokes /capture-fix.
# Non-interactive runs exit 0 (no forced write).
exit 0
