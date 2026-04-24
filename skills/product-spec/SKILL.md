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
   - Read `memory/product/context.md` (product vision, priorities, constraints)
   - Read `templates/prd-template.md` (from this toolkit or your own)
   - Read `patterns/user-story-format.md`

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

- [PRD Template](../../templates/prd-template.md)
- [User Story Format](../../patterns/user-story-format.md)
- Initiative Breakdown skill (to turn the PRD into epics and stories)
