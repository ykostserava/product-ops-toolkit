---
name: grill-me
description: Relentless interview that stress-tests a plan, initiative, or decision until every branch of its design tree is settled. User-invoked only - type /grill-me before you scope, break down, or spec something that is still fuzzy.
disable-model-invocation: true
---

# /grill-me

Interview the user relentlessly until you reach a shared understanding of the
plan, decision, or idea they bring. This is the opposite of the default
"ask only what blocks the decision" habit - the user has explicitly asked to be
grilled, so leave nothing silently assumed.

Adapted from `grilling` in [mattpocock/skills](https://github.com/mattpocock/skills)
(MIT, see `NOTICE.md` next to this file) for product-owner work: same
mechanic, product-ops sources for facts, product-ops exits when done.

## Usage

```
/grill-me                                   # grill whatever is in the conversation
/grill-me docs/initiatives/<x>.md           # grill a document
/grill-me "<one-line idea or decision>"
```

## Mechanic: design tree, worked in rounds

Map the topic as a **design tree**: every decision branches into the decisions
that hang off it. The **frontier** is every decision whose prerequisites are
already settled - the questions you can ask _now_ without guessing at answers
you have not heard yet.

Ask the whole frontier in one round: number each question and give your
recommended answer. Then wait for the user's answers before the next round.

Format a round like so:

```
Q1 - <question title>: <question body, may be multiple paragraphs, including multiple choices>

-> recommended: <your recommended answer>

---

Q2 - <question title>: <question body>

-> recommended: <your recommended answer>
```

Plain ASCII on purpose: rounds and the closing lists get pasted into issue
trackers, some of which mangle anything else.

Each round the user answers reshapes the tree: settled decisions push the
frontier outward and unblock questions that depended on them. Recompute the
frontier and ask the next round. A question whose answer depends on another
question still open in this round belongs to a _later_ round, not this one.

A reply of "all as recommended" is an answer, but a cheap one: record those
decisions as **accepted-as-recommended**, not as the user's own ruling (see
Done), and before any one-way step downstream restate the reading and get an
explicit confirmation.

## Facts are your job, decisions are the user's

**Read-only throughout.** The interview never writes anywhere: no tracker
comments or transitions, no wiki pages, no chat messages, no registry edits,
no docs. Never ask the user for anything you could look up yourself. When a
frontier question needs a fact, look it up and do not block on it: only the
questions downstream of that fact wait; ask the rest of the frontier now.
Cheapest source first:

1. Already in context or one file away: your product-context files
   (`memory/product/`), ownership map, decision log - what was already decided
   and who owns what.
2. Availability and visibility rules (which markets, account types, or
   platforms can even see the thing) - before any "who sees this" question.
3. Deterministic scans: a duplicate check against the board, if your project
   ships one.
4. Issue-tracker reads (search and issue details only) - what status a ticket
   is in, what its comments settled.
5. Last, a read-only sub-agent or spec lookup for what the app actually does
   today - never the API specs alone. Findings stay in the conversation: a
   skill that writes a research report directory is not a source here.

Put every _decision_ to the user and wait. A decision that belongs to someone
else (another PO, a team, a stakeholder) is not a dead branch: mark it
`WAITING ON <role>` in the round, carry it to the Waiting-on list at the end of
the session, and there propose it as a follow-up entry - propose only, never
add it yourself, never draft a message to that person.

## Seed branches for product topics

Do not force these, but check each is either settled or consciously out of
scope before declaring the frontier empty:

- Scope reality: markets, account types, verification level, platform
  (iOS / Android / web). If your project keeps a scope checklist, read it
  explicitly: path-scoped rules do not auto-load for an interview that writes
  nothing.
- Ownership: is the surface yours or another team's?
- Existing state: does the live app or the board already have it?
- Acceptance: what appears in the data, where to look, on which input the
  check fails.
- Reversibility: any one-way step (tracker transitions, external posts) - name
  it before recommending it.

## Done

The session is done when the frontier is empty: every branch visited, nothing
left silently assumed. Then print, in plain ASCII:

- **Settled** - one line per decision: `decision -> answer [user]` when the
  user answered in their own words, `decision -> answer [as recommended]` when
  they accepted the recommendation. Downstream skills and `/handoff` must keep
  that tag.
- **Waiting on** - `decision -> role`, each with a proposed follow-up line for
  the user to add or drop.

Do not act on the result - no tickets, no docs, no tracker writes - until the
user confirms the shared understanding. Confirming the understanding approves
nothing further: `feature-intake`, `initiative-breakdown` and `product-spec`
keep their own gates when the user chooses to continue there.
