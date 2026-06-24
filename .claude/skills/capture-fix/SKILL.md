---
name: capture-fix
description: After a real fix, capture the lesson. Reads the git diff + this session, writes a 5-part lesson (symptom / root cause / fix / file:line / prevention), dedupes it, and stores it as TRUSTED knowledge. Solves knowledge loss (pain #1).
---

# /capture-fix

Run this right after you finish fixing something. It turns the fix you just did
into a reusable lesson so the next person (or you next month) does not re-debug it.

## Steps
1. Read the session's `git diff` + the conversation to reconstruct what broke and why.
2. Compose the lesson (CL3 fixed shape):
   ```
   ## <short symptom title>
   - Symptom: <what the user/dev saw>
   - Root cause: <the actual cause>
   - Fix: <what you changed>
   - File/line: <path:line>
   - Prevention: <how to stop it recurring>
   ```
3. Compute `symptom_hash` and call `capture_lesson` (feedbackkb-mcp), which runs
   the knowledge-write step: secret-scan -> dedupe (bump occurrence if it already
   exists) -> store via the KnowledgeStore adapter + index in `knowledge_ref`.
4. Because the dev authored + approved it, the lesson is stored `status=trusted`
   immediately (agent-authored lessons would be `draft` until reviewed).

## Noise filter (CL7-B)
Skip trivial fixes (typo/format with no prevention value). If a near-duplicate
lesson exists, bump its `occurrence` instead of creating a new one.

## Why
This is the active half of knowledge capture; the Stop-hook
(`.claude/agents/hooks/capture-lesson.sh`) is the passive half that catches the fixes you
forget to record.
