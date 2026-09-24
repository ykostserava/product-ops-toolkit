# Product Ops Toolkit

AI-native tools for product owners, delivery managers, and engineering leads who build their own infrastructure instead of waiting for someone else to ship it.

Built by a PM who got tired of doing the same Jira-shaped rituals by hand, automated each one, and open-sourced the result.

---

## What's Inside

### Skills

`skills/` -- reusable Claude Code skills you can drop into your own project:

- **[initiative-breakdown](skills/initiative-breakdown/)** -- multi-agent orchestration (4 specialized agents + approval gates) that turns a Jira initiative or a PRD into validated epics and stories. Configurable per team via `config.yml`. Replaces 2-4 hours of manual breakdown with ~15 minutes + your review.
- **[product-spec](skills/product-spec/)** -- interactive PRD generator.
- **[product-analytics](skills/product-analytics/)** -- GA4 / Firebase / PostHog analysis with adoption / engagement / conversion framework.
- **[codebase-research](skills/codebase-research/)** -- multi-platform codebase audit. Inventories backend endpoints, traces them across iOS / Android / web, and produces a PO-ready coverage matrix with gaps and drift. Includes 4 stdlib-only Python scripts.
- **[raml-api-spec-search](skills/raml-api-spec-search/)** -- producer-side spec lookup against a central RAML repo (GitLab / GitHub). Pairs with `codebase-research` for spec-vs-implementation gap analysis.
- **[multi-agent](skills/multi-agent/)** -- generic 4-layer orchestration pattern (proposal -> design -> specs -> tasks).
- **[grill-me](skills/grill-me/)** -- relentless design-tree interview: asks the whole frontier of open decisions per round, each with a recommended answer, looks facts up itself and puts only decisions to you; closes with a Settled list that tells your own rulings from accepted recommendations. User-invoked only.
- **[to-questionnaire](skills/to-questionnaire/)** -- turns a decision you cannot settle alone into an async discovery questionnaire for one named person; interviews you only about the send (who, what back), never about the subject. Writes one file, sends nothing.
- **[handoff](skills/handoff/)** -- compacts the session into a document a fresh session can resume from: where the work is, what is verified, decisions with their author, dead ends, dangers, suggested skills. Plan, audit and execution as different sessions.
- **[board-sync](skills/board-sync/)** -- keeps parent statuses honest on a Jira board: deterministic engine (`scripts/board_consistency.py`, rules R1-R8: parent/child drift, unassigned active work, open blockers, aging WIP, external dependencies, release radar) -> `project-manager` judgment agent -> gated execution. Nothing is written without a per-item human yes; headless runs are propose-only by mechanism (`JIRA_PROPOSE_ONLY=1`).
- **[jira-package](skills/jira-package/)** -- a batch of Jira changes as a reviewable JSON changeset applied by one engine (`scripts/jira_apply.py`): ASCII payloads, required fields from `jira-config.json`, live-enumerated transitions, resolution on close, one-way confirmation, every write verified by reading it back. Dry run first.
- **[dup-check](skills/dup-check/)** -- "do we already have this?" with evidence: TF-IDF shortlist over the whole project (closed issues included, `scripts/duplicate_scan.py`) plus a judged duplicate / overlaps / distinct verdict. Read-only.
- **[followups](skills/followups/)** -- dated, person-addressed follow-ups in one registry (`scripts/followups.py`): aging view, sync from your notes with per-item approval, ping drafts that are never sent by the tool, and a cooldown so nobody gets nagged twice.
- **[writing-claude-code-rules](skills/writing-claude-code-rules/)** -- how to structure Claude Code instructions: CLAUDE.md vs `.claude/rules/` vs skills vs hooks, path-scoping, and why rules get ignored. Pairs with `rules/`.

The three interview/handoff skills are adapted from [mattpocock/skills](https://github.com/mattpocock/skills) (MIT); each carries a `NOTICE.md`.

### Agents

`agents/` -- Claude Code subagent definitions used by the skills (and reusable on their own).

Breakdown pipeline (used by `initiative-breakdown`):

- `product-brain-loader` -- loads product context, templates, and constraints from your memory/ knowledge base
- `sizing-validator` -- T-shirt sizing (XS/S/M/L/XL) with scope validation
- `breakdown-generator` -- generates epics and stories using configured templates
- `quality-reviewer` -- INVEST validation + PO auto-review + control manifest
- `mobile-delivery-agent` -- specialized assistant for mobile delivery managers; team-level patterns, release cycles, store constraints

Board operations (used by `board-sync`):

- `project-manager` -- judgment layer over the consistency engine's findings: reads comments/labels/devinfo, recommends FIX / SKIP / FLAG_ONLY / ASSIGN per finding with a proposed exceptions entry, reviews existing exceptions (KEEP / LIFT / DROP). Read-only; execution stays behind the skill's gates.

Audit fleet (used by the `cross-platform-audit` workflow):

- `ios-auditor` / `android-auditor` / `web-auditor` -- read-only consumer-side auditors: endpoint call sites, UI patterns, analytics events, tracking gaps per platform
- `backend-auditor` -- producer-side auditor: exposed endpoints, auth, DTO shapes, owner teams, spec drift
- `audit-coordinator` -- joins the per-platform JSON into a coverage matrix with orphan/phantom endpoints, UI parity, and event-name drift

### Workflows

`workflows/` -- deterministic multi-agent orchestration scripts for Claude Code's Workflow engine:

- **[cross-platform-audit.js](workflows/cross-platform-audit.js)** -- launches one read-only auditor per platform in parallel, adversarially spot-checks each audit's cited file:line references, then merges verified findings into a PO-ready coverage matrix. Point `args.repos` at your checkouts and go.

### Rules

`rules/` -- the `.claude/rules/` approach to project instructions: one constraint per small file, path-scoped where possible, indexed from CLAUDE.md. Ships a README with the method and four example rules (team process, issue-tracker hygiene, API access, doc output) distilled from a real product-team setup. See `rules/README.md`.

### Hooks

`hooks/` -- hard guarantees enforced by the Claude Code harness (rules are guidance; hooks are enforcement):

- `secret_scan.py` -- blocks `git commit` when gitleaks finds a secret in the staged diff (fails open if gitleaks isn't installed)
- `guard_env.py` -- blocks Claude from writing/editing `.env*` files

Wiring instructions in `hooks/README.md`.

### Memory scaffold

`memory/` -- empty starter knowledge-base structure (product/, patterns/, templates/, decisions/, feedback/, stakeholders/) plus a README explaining how each directory feeds the skills. Drop it into your project root and fill it in over time.

### Templates

`templates/` -- starting-point templates you fill in:

- `prd-template.md` -- Product Requirements Document
- `story-template.md` -- full 15-section story with As-Is/To-Be, error handling, NFRs, analytics
- `task-template.md` -- technical task (Why / What / Where / AC)
- `user-story-template.md` -- minimal story format for lighter work

### Patterns

`patterns/` -- reference docs the agents and humans can both read:

- `initiative-breakdown-pattern.md` -- feature-based epics vs platform-based, platform prefix convention
- `tshirt-sizing-guide.md` -- when to break down, when to split, when to skip Epic layer
- `user-story-format.md` -- INVEST checklist, Given-When-Then, anti-patterns
- `jira-api-best-practices.md` -- ASCII safety, default priority, scope confirmation
- `jira-read-protocol.md` -- the read-side contract every judgment agent shares: one access point, batch fetch exit codes, devinfo cost, dev-roster semantics, JQL quoting

### Scripts and tests

`scripts/` -- the stdlib-only engines behind the Jira skills, with their tests in `tests/` (run `pip install -r requirements-dev.txt && pytest`). A skill without its script and test is a promise; these are the mechanics:

| Script | Role | Writes to Jira? |
|---|---|---|
| `jira_api.py` | the ONLY Jira access point: `.env`-configured REST client + CLI (`search`, `get`, `epic`, `links`, `comments`, `devinfo`, `transitions`, ...) | no |
| `jira_config.py` + `jira-config.json` | team settings: project key, status names, one-way statuses, create rules, readiness fields | - |
| `jira_batch_fetch.py` | parallel (key x command) reads merged into one JSON; exit 2 = partial, `AUTH:` = stop | no |
| `board_consistency.py` | rules R1-R8 over the issue graph, exceptions and releases registries | no |
| `board_sync_delta.py` | diff of two `--report` snapshots for a nightly "what changed" | no |
| `duplicate_scan.py` | two-stage TF-IDF duplicate shortlist | no |
| `followups.py` | the follow-ups registry CLI | no (local JSON) |
| `jira_transition.py` | ONE status move: enumerate live, match by target name, one-way guard, resolution on close, verify after | yes, gated |
| `jira_assign.py` | ONE assignee change, verified after | yes, gated |
| `jira_apply.py` | a whole changeset through the same guards, `--dry-run` / `--apply` | yes, gated |

Every writer refuses when `JIRA_PROPOSE_ONLY=1` is set - put that in any scheduled wrapper and a headless run cannot write even if the model decides to. Connection settings: copy `scripts/.env.example` to `scripts/.env`.

### Pipelines

`pipelines/` -- ready-to-run automation:

- **[morning-briefing](pipelines/morning-briefing/)** -- daily headless pipeline that fetches your open Jira tickets, categorizes them, asks Claude for a "Top focus today", renders an HTML dashboard, and updates a Google Calendar event so you get a phone + laptop notification each morning. Windows Task Scheduler / cron / launchd compatible.

---

## Why This Exists

I'm a PM who transitioned from delivery management into product ownership by automating operational rituals into AI-augmented pipelines. At some point the toolkit became too good to keep local.

The thesis: POs and DMs don't need bigger boilerplate libraries. They need **orchestration** -- approval gates, structured knowledge, agent specialization -- that encodes their team's conventions and applies them consistently.

Everything here runs in Claude Code. It assumes:
- You're comfortable editing markdown and yaml
- You have Jira access and a token
- You're willing to invest 30-60 minutes on `config.yml` + memory files to get good output

If that fits, these tools will compound across every initiative, PRD, and sprint you run.

---

## Quick Start

This repo can be used **as a Claude Code plugin** (recommended) or copied manually.

### Option A: Install as a Claude Code plugin (recommended)

In Claude Code:

```
/plugin install https://github.com/ykostserava/product-ops-toolkit
```

After install, all skills are namespaced under `product-ops:`:

```
/product-ops:initiative-breakdown PROJ-42 --dry-run
/product-ops:product-spec "Savings goals"
/product-ops:codebase-research ./apps/api
/product-ops:scaffold-memory       # bootstraps memory/ in your project
```

The plugin bundles templates, patterns, and agent definitions, and resolves them via `${CLAUDE_PLUGIN_ROOT}` at runtime, so they keep working after upgrades.

To pin a version, set `version` in `.claude-plugin/plugin.json` and tag the release; Claude Code uses the tagged commit. To get unreleased changes, use the latest commit.

### Option B: Manual install (git-clone + cp)

1. **Clone this repo** next to your project:
   ```bash
   git clone https://github.com/ykostserava/product-ops-toolkit.git
   ```

2. **Copy skills and agents into your Claude Code setup**:
   ```bash
   cp -r product-ops-toolkit/skills/* ~/.claude/skills/
   cp -r product-ops-toolkit/agents/* ~/.claude/agents/
   ```
   Note: with manual install, references to `${CLAUDE_PLUGIN_ROOT}` inside SKILL.md and agent files won't resolve — replace them with absolute paths to where you cloned the repo, or copy the templates / patterns / memory directories into your project.

3. **Configure `config.yml`** inside `skills/initiative-breakdown/` - set your product name, Jira URL, platforms, templates, and constraints.

   For the Jira skills (`board-sync`, `jira-package`, `dup-check`) also copy `scripts/.env.example` to `scripts/.env` and edit `scripts/jira-config.json` (project key, your workflow's status names, one-way statuses).

4. **Seed your `memory/`** directory with product context, patterns, and templates. Run `/scaffold-memory` (after copying the skill) or copy the `memory/` scaffold from this repo.

5. **Run a skill**:
   ```
   /initiative-breakdown PROJ-42 --dry-run
   ```

See individual skill READMEs for detailed setup per tool.

---

## Philosophy

- **Configure, don't hardcode.** Every team-specific detail lives in `config.yml` or `memory/`. Skills are generic; your knowledge base makes them yours.
- **Orchestrate agents, don't replace them.** The value is phase structure + approval gates, not "one mega-prompt that does everything".
- **Invest in the knowledge base.** Output quality = context quality. Skills are as good as your `memory/` is.
- **Kanban > sprint ceremonies.** Default tone is priorities and dependencies, not story points and velocity. If your team runs Scrum, adjust `config.yml` -> `process.workflow: scrum`.
- **ASCII > Unicode for Jira API.** Too many Jira instances choke on arrows, smart quotes, and non-Latin scripts. `jira-api-best-practices.md` explains why.

---

## Contributing

Pull requests welcome. If your team has useful patterns worth generalizing, add them under `patterns/` with a short explanation of **why** the pattern matters (not just what it does).

Issues: use GitHub issues for skill improvements, new pattern proposals, or documentation gaps.

---

## License

[MIT](LICENSE) - use, modify, distribute. Authors assume no liability.

---

## Related

- [Claude Code](https://docs.claude.com/claude-code) - the runtime this is built for
- [Anthropic SDK](https://github.com/anthropics/anthropic-sdk-python) - when you need to go beyond Claude Code
