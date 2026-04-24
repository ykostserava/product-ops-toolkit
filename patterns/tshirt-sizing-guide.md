---
name: T-Shirt Sizing Guide
description: Initiative sizing framework (XS / S / M / L / XL) with decision criteria and examples
type: pattern
---

# T-Shirt Sizing Guide for Initiatives

## Purpose

Determine appropriate scope BEFORE breaking the initiative into epics. Prevents:
- Over-scoping (XL initiatives that should be split)
- Under-scoping (XS work that doesn't need the initiative layer)
- Unrealistic timelines

---

## The Scale

| Size | Duration | Team-Weeks | Typical Scope | Action Required |
|------|----------|------------|---------------|-----------------|
| **XS** | <2 weeks | 1-2 | Minor improvements, bugs, research | Skip Initiative layer, create Epic |
| **S** | 2-4 weeks | 2-4 | Small, well-defined feature | Standard breakdown |
| **M** | 4-6 weeks | 4-6 | Standard initiative | Standard breakdown |
| **L** | 6-10 weeks | 6-10 | Complex with dependencies | De-risking required |
| **XL** | >10 weeks | >10 | Major strategic "big rock" | MUST decompose first |

---

## Sizing Indicators

### XS - <2 weeks

- 1-2 epics maximum
- <10 total stories / tasks
- Single platform OR simple backend change
- No external dependencies
- Low technical risk
- Can be done by 1-2 developers

**Examples:**
- "Fix transaction sorting bug on mobile"
- "Add CSV export button to reports"
- "Research best pagination library"
- "Update privacy policy text across platforms"

**Recommendation:** Skip Epic layer. Create stories directly under the initiative.

**Why skip Epic?** Too much overhead for 3-5 stories. Epic adds no organizational value. One less layer = simpler structure.

---

### S - 2-4 weeks

- 2-3 feature-based epics
- 10-20 stories / tasks total
- 2-3 platforms
- Minimal external dependencies
- Low-medium technical risk
- Single team can deliver

**Examples:**
- "Add filtering to transaction history"
- "Simple goal creation feature" (create/edit/delete goals, basic UI)
- "Push notification system MVP"
- "CSV export for all reports"

**Recommendation:** Standard breakdown. 1-2 sprints. Single team (3-5 developers).

---

### M - 4-6 weeks

- 3-5 feature-based epics
- 20-40 stories / tasks total
- All platforms
- Some external dependencies (analytics, compliance)
- Medium technical risk
- Single team with full platform coverage

**Examples:**
- "Savings product MVP"
- "Multi-currency account switching"
- "Enhanced user profile with KYC"
- "Payment method management"

**Recommendation:** Standard breakdown. 3-4 sprints. Include mitigation for medium risks.

---

### L - 6-10 weeks

- 5-7 feature-based epics
- 40-60 stories / tasks total
- All platforms + complex integrations
- Cross-team dependencies (design, legal, external APIs)
- High technical risk OR new tech stack
- May require 1.5-2 teams

**Examples:**
- "Full savings product with interest calculation"
- "Payment gateway v2 migration"
- "Account aggregation via OpenBanking"
- "Redesigned onboarding flow"

**Recommendation:** Detailed breakdown with explicit risk assessment.
- De-risking activities in early sprints (POC, spike)
- Risk mitigation strategies documented
- Phased rollout plan (beta -> 10% -> 100%)
- Rollback plan documented
- External dependency tracking

---

### XL - >10 weeks

- 7+ feature-based epics
- 60+ stories / tasks
- Strategic scope (multi-product, platform-wide changes)
- Multiple team dependencies
- Very high technical or business risk
- Requires 2+ teams or >3 months

**Examples:**
- "Launch complete digital wallet platform"
- "Migrate to new architecture" (monolith -> microservices)
- "Multi-region expansion" (GDPR, localization, compliance)
- "Super-app transformation"

**Recommendation:** STOP. Decompose into vertical slices first.

**Why XL is dangerous:**
- Too much scope to manage as single initiative
- Risk of scope creep and timeline delays
- Hard to prioritize within a single initiative
- Team coordination becomes bottleneck
- Business value delivery delayed (all-or-nothing)

### Decomposition Strategies

**Option 1: By phase (MVP -> V1 -> V2)**

```
Initiative 1: Product MVP (M)
  - Core features only, single currency, basic UI

Initiative 2: Product V1 - Multi-currency (M)
  - Add multi-currency, exchange, improved UX

Initiative 3: Product V2 - Investments (L)
  - Savings goals, investment products, advanced features
```

**Option 2: By product area (vertical slices)**

```
Initiative 1: Account Management (M)
  - Account CRUD, balance display, multi-currency

Initiative 2: Transaction System (L)
  - Transfers, history, filtering

Initiative 3: Investment Products (M)
  - Goals, interest, reporting
```

**Option 3: By platform (if necessary)**

```
Initiative 1: Backend + Web (L)
Initiative 2: Mobile (iOS + Android) (M)
```

---

## Sizing Process (Step-by-Step)

### Step 1: Quick Scan

Read initiative description, identify:
- How many major features or capabilities?
- How many platforms involved?
- Any integrations or dependencies?

### Step 2: Epic Count Estimate

- 1-2 epics -> likely XS
- 2-3 epics -> likely S
- 3-5 epics -> likely M
- 5-7 epics -> likely L
- 7+ epics -> likely XL

### Step 3: Complexity Multipliers

Adjust size based on:

**Increase size (+1) if:**
- High technical risk (new tech, complex algorithms)
- Cross-team dependencies (>2 teams involved)
- Legal / compliance critical (regulations, GDPR, PCI-DSS)
- Major architectural change (database migration, new infra)
- External dependencies (third-party APIs, government approvals)

**Decrease size (-1) if:**
- Mostly UI work with existing APIs
- Single platform only
- Well-understood domain (similar to past work)
- No external dependencies

### Step 4: Final Size

Pick the size that matches most indicators.

### Step 5: Document Assessment

```markdown
## T-Shirt Size Assessment

Estimated Size: M

Reasoning:
- Feature Complexity: 4 major features
- Platform Coverage: all platforms from config
- Integrations: 2 external (analytics, KYC)
- Technical Risk: medium (new tables, scheduled jobs)
- Dependencies: internal only

Epic Count: 5
Estimated Stories: ~30
Estimated Timeline: 4-6 weeks (3-4 sprints)

Recommendation: Appropriate scope. Proceed with breakdown.
```

---

## Edge Cases

### Research / Spike Initiatives

Size as XS regardless of topic complexity. Duration: 1-2 weeks max. Output: decision document, not production code. Don't create Initiative - create Research Epic.

### Bug Fix Collections

- <10 bugs, small scope -> XS (Epic only)
- 10-20 bugs across platforms -> S (Initiative)
- >20 bugs requiring systematic fix -> M (Initiative with refactoring)

### Infrastructure / DevOps Work

Usually underestimated. Add complexity:
- Infrastructure migrations -> +1 size
- CI/CD overhaul -> +1 size
- Multi-region deployment -> +1 size

### Maintenance / Tech Debt

- Code cleanup -> XS (Epic)
- Dependency upgrades -> XS-S
- Refactoring single module -> S
- Architecture refactoring -> L-XL (decompose!)

---

## Common Sizing Mistakes

### Mistake 1: Underestimating Platform Work

"It's just adding a button" ignores Android + iOS + Web + Backend + QA.

Fix: always account for ALL platforms. Single platform: -1 size. 2-3 platforms: baseline. All 4 platforms: +0 to +1.

### Mistake 2: Ignoring External Dependencies

"We just integrate X API" ignores auth, testing, error handling, compliance.

Fix:
- Each external API: +0.5 size
- Legal / compliance: +1 size
- Government / banking: +2 sizes

### Mistake 3: Conflating Effort with Duration

"10 developers for 1 week" is not the same as "1 developer for 10 weeks."

Fix: T-shirt size is **duration**, not effort. Consider team coordination overhead, dependencies blocking parallel work, review / QA cycles.

### Mistake 4: Not Decomposing XL

"We can manage a 3-month initiative" -- XL initiatives carry high coordination overhead, scope creep risk, delayed value delivery, team burnout risk. Always decompose XL into M-sized slices.

---

## When to Re-Size

During breakdown, reassess size if:
- Epic count differs significantly from initial estimate
- Unexpected dependencies discovered
- Scope has crept since initial sizing
- Technical risk higher than anticipated

Update size in breakdown document if changed.

---

## How /initiative-breakdown Uses This

1. Load initiative description
2. Assess T-shirt size (this guide)
3. If XS: stop, recommend Epic-only
4. If XL: stop, recommend decomposition
5. If S/M/L: proceed with breakdown
6. Include size in output

---

## Summary

- Use T-shirt sizing BEFORE breakdown
- XS -> Create Epic only, skip Initiative layer
- S/M/L -> Standard breakdown
- XL -> Decompose first, then breakdown
- Document size in output
- Re-assess if scope changes
