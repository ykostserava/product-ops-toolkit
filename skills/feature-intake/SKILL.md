---
name: feature-intake
description: Use when starting any new feature, initiative, or request - before scoping, breaking it down, or building - especially when it may span multiple platforms or touch service availability.
---

# feature-intake

Lightweight "think and prepare" step BEFORE building. Not code, not tickets - a
short routine that answers three things: **what we already know, what the feature
touches, and who to ask for each gap.** Built for a multi-repo, cross-functional
reality (planning is shared/PO-driven; execution is per-repo, per-engineer).

## When to use
- A new feature/initiative/request arrives and you're about to scope or break it down.
- Skip for trivial one-line changes.

## The routine (3 steps + a gate)

> **Preflight first (if your project ships a pre-scoping verification skill):** run it on the
> feature/initiative before step 1. A good one bundles the analytics-event-existence + service x
> country + account-type-visibility checks below into one deterministic verified / gap-confirmed /
> needs-code-verify table. Treat every `needs-code-verify` row as an unknown to route in step 3, and
> never declare a gap it did not confirm. No such skill? Do the checks manually as below.

### 1. Local knowledge first (don't start blind)
Read what we already have BEFORE any exploration:
- Your product-context skill (glossary + per-service product cards) - load it first.
- Apply a **scope-reality-check**: country + account-type availability per your cards/matrix.
- Half the answers usually already exist here - don't re-derive them.

### 2. Classify (what does it touch)
Decide which domains/platforms are in scope:

| Signal in the request | Domain -> where it lives |
|-----------------------|--------------------------|
| iOS / iPhone | iOS repo · platform auditor · owner |
| Android | Android repo · platform auditor · owner |
| web / dashboard | web repo · platform auditor · owner |
| endpoint / API / DTO / auth | backend repo(s) · `backend-auditor` · BE owner |
| test / QA / regression | QA strategy · QA owner |
| availability / country / account type / visibility | product-context · PO |
| event / metric / funnel | your product-analytics tool (PostHog / GA4 / etc.) · analytics |

Note the country/account-type scope explicitly (e.g. "FeatureX = Country-A only" -> don't scope Country-B).

### 3. Route (right agent/tool for each open question)
For every unknown, send it to the right place - don't guess, don't ask the wrong person:

| Question | Route to |
|----------|----------|
| Is this service available in country / account type? | your product-context skill -> product cards + availability matrix |
| Does an endpoint / RAML schema exist? | `raml-api-spec-search` skill |
| Where is an endpoint consumed across platforms? | `codebase-research` skill |
| Current behaviour on iOS / Android / Web? | your per-platform auditor agents |
| Backend: endpoint owner / DTO / auth? | `backend-auditor` (confirm with the BE owner) |
| Is it consistent across all platforms? | your cross-platform audit workflow |
| What does a domain term mean? | your context glossary |
| Does an analytics event exist / how to measure? | your pre-scoping verification skill (bundles this check) or PostHog/GA4 - **verify the event exists before declaring a gap** |
| Is the shared knowledge stale? | your context-maintainer agent |

### Gate: plan mode before deeper work
Present the plan and get approval BEFORE breaking down or building. Don't silently proceed.

## Output (hand this to the team)
- **Known** - facts already established from local knowledge (with scope: countries/account types).
- **Unknowns** - open questions, each tagged with its route (from step 3).
- **Per-platform slices** - what each platform/repo needs, who owns it.
- **Next** - feed into the breakdown flow; engineers execute in their own repos.

## What this is NOT
- Not execution. Planning is shared/PO-driven; building happens per-repo, per-engineer.
- Not a code orchestrator - for cross-platform checks use your audit workflow; for layered multi-agent work use `multi-agent`.
- Don't invent product facts - if a card/fact is missing, route it, don't guess.

## References (downward)

- **Knowledge:** your product-context skill (glossary, product cards, sources).
- **Discipline:** scope-reality-check (country / account-type availability).
- **Routes to:** per-platform auditor agents, cross-platform audit workflow, `raml-api-spec-search`, `codebase-research`, context-maintainer, `multi-agent`.

(Referenced by name, not `@import`. When routing to an agent, name the skill/context it should use - a subagent does not inherit them automatically.)
