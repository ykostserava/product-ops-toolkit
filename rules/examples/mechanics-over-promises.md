# Mechanics instead of promises

A rule written in prose is a promise. A rule that works is one with a test, a
linter, a hook or a gate. A new rule in this repo gets a mechanic
(`tests/test_toolkit_config.py`, a hook, or a gate inside a skill) in the
same commit whenever one is possible.

## Process

- **Planning, auditing and execution are different sessions** (the panel:
  `audit-panel.md`).
- **The executor is not the acceptor.** Anything that leaves the repo
  (issue tracker, wiki, chats, mail) is a draft behind an explicit per-item
  gate. This is a repo-wide convention, not a property of individual skills.

## Framing the task

- **An ambiguous task gets a one-line goal BEFORE the edit** (which service,
  which files, which unit of data) and a question before code, not a rollback
  after.
- **A task without a verifiable acceptance criterion does not start**: what
  will appear in the data, where to look, on which input the check gives a
  negative result. For tickets - an acceptance-criteria checklist.
- **An answer to a question is only the answer.** Side findings go to the
  follow-ups registry (`/followups`), not into the reply; into the chat only
  if it breaks production or costs money today.

## Acceptance

- **The executor's words are not proof.** Order: name the source -> check
  its freshness and coverage -> conclusion; no source - say so: "could not
  confirm from data, here is where I looked". An error costs the same in
  both directions ("not done" about done work, and "done" about undone).
- **A status answer names the dashboard's figure** (the portal, a person's
  report), not your own query; a mismatch between the report and the query
  IS the answer, together with each one's window.
- **A figure that goes outside comes only from a registry** where the unit,
  the window, the selection rule and how it was verified are recorded. An
  unverified figure is not said at all - a caveat does not save it. Where a
  skill drafts outward text, wire a check-draft gate into it and name the
  skill in this rule; a test keeps the list honest.

## Quality

- **Fixing a bug - close the class, not the spot**: in the same commit a
  test, a linter rule or a shared helper, plus a search of the repo for the
  same rake elsewhere.
- **A new guard or threshold ships with named**: units, window, an input on
  which it MUST fire, and an input that is a false positive. A check without
  a test on a real case is a suspect, not a guarantee.

## Budget

- **The expensive call is the last step**: deterministic filtering on the
  data at hand -> a fast model ("is it worth doing") -> the expensive model
  with the context ready in the prompt. A failure of a cheap step passes the
  item on, it does not close it; a dry run writes nowhere. The pipeline
  skills here are built that way - new ones must be too.
- **Hitting a subscription limit is a separate outcome**, not "spent the
  money" - keep a documented fallback.

## Mechanics that hold these rules

`tests/test_toolkit_config.py`:
- size ratchet: the always-loaded rules stay under a fixed byte budget, or
  the tests go red - the file must not grow past the point where it stops
  being read;
- auditor panel: three agents exist, tools are Read/Grep/Glob only, the
  three models differ;
- every hook file has a row in `hooks/README.md`; every skill carries a
  name and a description.
