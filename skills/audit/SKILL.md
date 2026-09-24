---
name: audit
description: Panel of three blind auditors over a design document - three models x three lenses (money and spend; failures, time and concurrency; definitions and boundaries), each reading the document and the code itself with no retelling. Use BEFORE writing code for a new scheme, flow, migration or integration. Read-only. Triggers on "audit", "run the panel", "three blind auditors", "audit this design".
disable-model-invocation: true
---

# /audit <path to the design document>

Launch THREE auditors IN PARALLEL (one message, three Agent calls):
`auditor-money`, `auditor-failures`, `auditor-definitions`
(definitions in `agents/`). Document: `$ARGUMENTS`.

Give each ONLY the path to the document and the list of files it relies on
(work the list out yourself from the links and mentions in the document).
Give none of them your own retelling of the scheme.

When all three have answered, merge:
- a finding raised by two or more auditors goes to the fix list without
  discussion;
- a finding raised by one is checked by hand BEFORE it is fixed;
- auditors contradicting each other (one says the opposite of another) go
  into a separate section.

Cost: roughly 350k tokens per run - it is for schemes where a mistake costs a
rewrite, not for point fixes (rule: `rules/examples/audit-panel.md`).
Planning, auditing and execution are different sessions.
