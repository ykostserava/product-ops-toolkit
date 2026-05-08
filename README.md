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

### Agents

`agents/` -- Claude Code subagent definitions used by `initiative-breakdown` (and reusable on their own):

- `product-brain-loader` -- loads product context, templates, and constraints from your memory/ knowledge base
- `sizing-validator` -- T-shirt sizing (XS/S/M/L/XL) with scope validation
- `breakdown-generator` -- generates epics and stories using configured templates
- `quality-reviewer` -- INVEST validation + PO auto-review + control manifest
- `mobile-delivery-agent` -- specialized assistant for mobile delivery managers; team-level patterns, release cycles, store constraints

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
