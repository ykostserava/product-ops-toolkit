---
description: Generate Product Requirements Document for a feature
---

# Product Spec Generator

Creates a comprehensive PRD following a configurable template.

## Usage

```
/product-spec [feature name]
```

## Process

1. **Load context**
   - Read the project's product context (default: `memory/product/context.md` in the user's cwd; falls back to `${CLAUDE_PLUGIN_ROOT}/memory/product/context.md` only if explicitly bundled)
   - Read PRD template: `${CLAUDE_PLUGIN_ROOT}/templates/prd-template.md` (or the user's project override at `templates/prd-template.md`)
   - Read user-story format: `${CLAUDE_PLUGIN_ROOT}/patterns/user-story-format.md`

   To resolve `${CLAUDE_PLUGIN_ROOT}` first, run a quick Bash check (e.g. `echo "$CLAUDE_PLUGIN_ROOT"`) and use the absolute path in subsequent Read calls.

2. **Gather requirements** (interactive)
   - What problem does this solve?
   - Who are the users?
   - What are the success metrics?
   - Any technical constraints?
   - Out of scope items?

3. **Generate PRD**
   - Follow template structure
   - Write clear user stories with acceptance criteria (Given-When-Then)
   - Include timeline estimate
   - Add "Out of Scope" section
   - Identify stakeholders

4. **Save**
   - Write to `docs/specs/[feature-name]-prd.md`
   - Optionally publish to wiki / Confluence
   - Optionally create Jira epic linked to the spec

## Output Quality Rules

- Every user story has acceptance criteria
- Success metrics are measurable (not "improve UX")
- Technical considerations addressed
- Stakeholders identified with communication cadence
- Out of scope items explicitly listed

## Related

- PRD Template: `${CLAUDE_PLUGIN_ROOT}/templates/prd-template.md`
- User Story Format: `${CLAUDE_PLUGIN_ROOT}/patterns/user-story-format.md`
- `initiative-breakdown` skill in this plugin (to turn the PRD into epics and stories)
