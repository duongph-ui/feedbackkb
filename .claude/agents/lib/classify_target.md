# classify_target (§3.2.2) — dynamic A/B/C classification of a Fixer patch

Run BEFORE proposing a prod apply. Read the TARGET system's `layerevent` rules
(never guess). The classifier service (`feedbackkb_server.service.classify`) encodes:

- **A** — only UI/API, no Entity Schema change -> human merge only.
- **B** — changes schema but does NOT read/write Layer Event & EventDetails and
  does NOT write CalculateKR & ExtractEvent -> POSUP of the target system.
- **C** — reads/writes/changes Layer Event/EventDetails OR writes
  CalculateKR/ExtractEvent -> POSUP + ARCH of the target system.

Record in `agent_task.result`: `target_system`, `classification`,
`approval_needed`, `layer_tables_touched[]`. The Analyst (impact phase) produces
the classification independently; Type C unapproved -> verdict `block`.
