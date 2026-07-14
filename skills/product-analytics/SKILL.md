---
description: Product Analytics - analyze GA4 / Firebase / PostHog data, generate insights, track metric history, create reports
---

# Product Analytics Skill

Automated analysis of product metrics from your analytics sources (GA4, Firebase, PostHog, or CSV exports). Calculates adoption / engagement / conversion metrics, tracks them over time, and generates markdown insight reports.

## Usage

```bash
# Full analysis (recommended)
/product-analytics

# Weekly report
/product-analytics --weekly

# Feature-specific analysis
/product-analytics --feature="Checkout"

# Compare periods
/product-analytics --compare --period1="last-week" --period2="prev-week"
```

---

## What This Skill Does

1. **Loads data** from your analytics source (CSV export or API)
2. **Analyzes metrics** against your Product Analytics Framework
3. **Generates insights** and prioritized recommendations
4. **Creates a report** in Markdown
5. **Saves a snapshot** to history so every future report includes trends

---

## Setup

Before first use, configure the skill for your team. Create `config.yml` next to this `SKILL.md`:

```yaml
# config.yml
product:
  name: "Your Product Name"
  context_files:
    - memory/product/context.md
    - memory/product/product-definition.md

analytics:
  data_source: "csv"            # or "api"
  provider: "ga4"               # ga4 | firebase | posthog
  api_host: "https://your-analytics-host.example.com"  # for self-hosted PostHog etc.
  project_id: "your-project-id" # provider project, if applicable
  data_dir: "data/"             # where raw exports and snapshots live
  framework_file: "docs/analytics/product-analytics-framework.md"
  output_dir: "docs/analytics/"
  retention_days: 90

features:                        # names the skill will look for in event data
  - Checkout
  - Search
  - Notifications
  - Onboarding

benchmarks:
  adoption_good: 0.50            # >50% adoption = healthy
  engagement_good: 5             # >5 events/user/week = healthy
  conversion_good: 0.80          # >80% funnel completion = healthy
```

Credentials never go in `config.yml`. Put them in `.env` (gitignored):

```bash
# .env
POSTHOG_API_KEY=...
GA4_SERVICE_ACCOUNT_JSON=path/to/service-account.json
```

---

## Workflow

### Phase 1: Load Data

**Step 1.1: Check for latest data**

```bash
# Check if fresh data exists (path from config: analytics.data_dir)
ls -lt data/events-*.json | head -1

# If older than 7 days or missing:
# Ask user to export CSV from the analytics tool or run the API fetch
```

**Step 1.2: Parse data**

If CSV provided:
```bash
python scripts/parse_events_csv.py [csv-path] --output data/events-latest.json
python scripts/parse_users_csv.py [csv-path] --output data/users-latest.json
```

If API available (e.g. PostHog API, or GA4 via BigQuery export):
```bash
python scripts/fetch_analytics.py --events --engagement --output data/events-latest.json
```

The fetcher reads `analytics.api_host` / `analytics.project_id` from `config.yml` and the API key from `.env`.

---

### Phase 2: Analyze Metrics

**Step 2.1: Load your Product Analytics Framework**

Read the file configured as `analytics.framework_file` (e.g. `docs/analytics/product-analytics-framework.md`).

**Extract:**
- Critical tracking gaps (events that should exist but do not)
- Feature health metrics (adoption, engagement, completion)
- User behavior patterns

**Step 2.2: Calculate Key Metrics**

For each feature in data:

**1. Adoption Rate**
```
Adoption = (Users who used feature / Total active users) * 100%
```

**2. Engagement Rate**
```
Engagement = Events per active user
```

**3. Conversion Rate** (if a funnel exists)
```
Conversion = (Completion events / Entry events) * 100%
```

**4. User Segmentation**
```
Power users: >10 events/week
Active users: 3-10 events/week
Light users: <3 events/week
```

**A note on event naming.** Funnel math only works if entry and completion events are named consistently. A pattern that works well: `[feature]_[action]` pairs such as `checkout_open` -> `checkout_done`, or `account_create_attempt` -> `account_create_success`. Keep platform (web/ios/android) as an event **property**, never in the event name -- otherwise every cross-platform funnel needs N event names instead of one.

---

### Phase 3: Generate Insights

**Step 3.1: Identify Trends**

For each metric:
- **Winning:** High adoption + high engagement + high conversion
- **At Risk:** High adoption but declining engagement
- **Problem:** Low adoption or broken tracking
- **Opportunity:** Low adoption but high completion rate

**Step 3.2: Compare Against Benchmarks**

Benchmarks come from `config.yml`:

| Metric | Benchmark | Status |
|--------|-----------|--------|
| Adoption | >50% | OK / At Risk / Problem |
| Engagement | >5 events/week | OK / At Risk / Problem |
| Conversion | >80% | OK / At Risk / Problem |

**Step 3.3: Flag Critical Issues**

Based on your Product Analytics Framework:
- P0: Broken tracking (missing events -- you cannot measure the feature at all)
- P1: Low performance (bad metrics)
- P2: Optimization opportunity

---

### Phase 4: Create Report

**Step 4.1: Generate Markdown Report**

Save to: `[output_dir]/product-report-[date].md`

**Structure:**
```markdown
# Product Analytics Report
**Period:** [dates]
**Generated:** [timestamp]

## Executive Summary
- DAU: [number] ([WoW change]%)
- Top feature: [name] ([adoption]%)
- Critical issue: [description]

## Trends (4-week)

### Top-Line Metrics
- DAU: [current] ([trend] vs 4 weeks ago)
- MAU: [current] ([trend])
- Stickiness: [current]% ([trend])

### Feature Performance Trends
- [Feature 1] adoption: [current]% ([trend])
- [Feature 2] adoption: [current]% ([trend])
[Repeat for key features]

## Feature Performance

### [Feature Name]
- Adoption: [X]% ([users]/[total]) [trend indicator]
- Engagement: [X] events/week [trend indicator]
- Conversion: [X]% or UNKNOWN if tracking missing
- Status: OK / At Risk / Critical tracking gap

[Repeat for each feature]

## Insights & Recommendations

### Critical Actions (P0)
1. [Action 1]
2. [Action 2]

### High Priority (P1)
1. [Action 1]

### Opportunities (P2)
1. [Opportunity 1]

## User Segments

### Power Users ([X]%)
- Behavior: [description]
- Value: [metric]

### Active Users ([X]%)
- Behavior: [description]

### Light Users ([X]%)
- Behavior: [description]

## Historical Context
- Snapshots in history: [count]
- Oldest data: [date]
- Latest data: [date]

## Appendix
- Data source: [CSV/API]
- Events analyzed: [count]
- Period: [dates]
```

**Step 4.2: Output to console**

Show a summary (illustrative numbers only):
```
Product Analytics Report Generated

Period: [date range]
DAU: [N] users ([WoW change]%)
Top Feature: [name] ([X]% adoption, [trend] vs 4 weeks ago)

Critical Issues:
P0 [Feature] funnel broken (no completion tracking)
P0 No error events (cannot debug failures)

Trends:
- DAU trending up
- [Feature] adoption declining
- Notification open rate improving

Report saved: docs/analytics/product-report-[date].md
History updated: [N] snapshots tracked
```

---

### Phase 5: Save to History

**Step 5.1: Calculate metrics and save snapshot**

```bash
python scripts/collect_metrics.py \
  --events data/events-latest.json \
  --users data/users-latest.json \
  --date [YYYY-MM-DD] \
  --save-history
```

This automatically:
- Calculates all metrics (adoption, engagement, conversion)
- Saves a snapshot to `data/analytics-history.json`
- Shows WoW comparison with the previous week

**Step 5.2: Load historical trends**

For each key metric in the report, include trend data:
```bash
python scripts/analytics_history.py --trend "top_line.dau"
python scripts/analytics_history.py --trend "features.checkout.adoption"
python scripts/analytics_history.py --compare "top_line.dau"
```

**Step 5.3: Add trend indicators to report**

For each metric with historical data:
- Show current value
- Show 4-week change (absolute + percentage)
- Add trend indicator (up/down/stable)
- Flag significant changes (>10% movement)

---

## Analysis Templates

### Template 1: Feature Health Check

For each feature:
```markdown
### [Feature Name]

**Metrics:**
- Adoption: [X]% ([users]/[total])
- Engagement: [X] events/week
- Conversion: [X]% ([done]/[open])

**Status:** Healthy / At Risk / Problem

**Insight:**
[What's working / what's not]

**Recommendation:**
[Specific action to take]
```

---

### Template 2: Funnel Analysis

For features with an entry -> completion event pair (e.g. `[feature]_open` -> `[feature]_done`):
```markdown
### [Feature] Funnel

```
[feature]_open: [X] users
        v  [conversion]%
[feature]_done: [Y] users
        v
Drop-off: [Z] users ([%]%)
```

**Issues:**
- [Issue 1]: [description]
- [Issue 2]: [description]

**Next Steps:**
1. [Action 1]
2. [Action 2]
```

---

### Template 3: Cohort Comparison

For user segments (illustrative numbers):
```markdown
### User Segment Comparison

| Segment | Users | Adoption | Engagement | Value |
|---------|-------|----------|------------|-------|
| Power   | 2K (10%)  | 95% | 25 events/week | High |
| Active  | 13K (65%) | 75% | 8 events/week  | Medium |
| Light   | 5K (25%)  | 30% | 2 events/week  | Low |

**Insight:**
[Behavioral difference]

**Opportunity:**
[How to move users up segments]
```

---

## Rules for Analysis

### 1. Always Use Latest Data

- Check data freshness (< 7 days old)
- If stale, ask user for a new export
- Note the data period in all reports

### 2. Context from Product Brain

Before analysis, read (paths from `config.yml`):
- `analytics.framework_file` (what to look for)
- `product.context_files` (product priorities and scope)

### 3. Focus on Actionable Insights

Don't just report numbers -- explain WHY a number matters and WHAT to do about it.

**Bad:** "Checkout adoption is 62%"
**Good:** "Checkout adoption is 62% -- this is our core conversion path. However, we can't measure completion because there is no `checkout_done` event. P0: add it."

### 4. Flag Data Quality Issues

If tracking is broken or missing:
- Mark as P0 Critical
- Estimate impact (which feature becomes unmeasurable)
- Provide a specific fix (add event Y with parameters Z)

### 5. Compare Against Benchmarks

Use the benchmarks from `config.yml`:
- Adoption: >50% is good
- Engagement: >5 events/week is good
- Conversion: >80% is good

Tune these to your product -- a daily-use utility and a quarterly tax tool have very different healthy baselines.

---

## Weekly Report Automation

**When user runs:** `/product-analytics --weekly`

**Generate:**
1. **Metrics Dashboard** (current week vs last week)
2. **Feature Health Scorecard** (all features)
3. **Top Insights** (3 most important findings)
4. **Action Items** (prioritized by P0/P1/P2)

**Send to:** `[output_dir]/weekly-report-[date].md`

**Include:**
- Week-over-week trends (up/down)
- New issues detected
- Progress on previous action items

---

## Feature-Specific Analysis

**When user runs:** `/product-analytics --feature="Checkout"`

**Analyze only:**
- Checkout-related events
- Checkout funnel (if it exists)
- Checkout user segments
- Checkout trends

**Output:** Focused report on a single feature

---

## Comparison Mode

**When user runs:** `/product-analytics --compare --period1="last-week" --period2="prev-week"`

**Compare:**
- DAU change
- Feature adoption change
- Engagement change
- New issues vs resolved issues

**Output:** Comparison report with deltas (+/- X%)

---

## Output Locations

**Reports** (in `analytics.output_dir`):
```
docs/analytics/
|-- product-report-[date].md       # Full analysis with trends
|-- weekly-report-[date].md        # Weekly summary with WoW comparison
|-- trends-[date].md               # 4-week trend report
|-- feature-[name]-[date].md       # Feature-specific analysis
`-- comparison-[date].md           # Period comparison
```

**Data** (in `analytics.data_dir`):
```
data/
|-- events-latest.json             # Most recent event export
|-- users-latest.json              # Most recent user metrics (DAU/WAU/MAU)
|-- events-[date].json             # Archived by date
|-- users-[date].json              # Archived by date
`-- analytics-history.json         # Historical snapshots with trends
```

**Scripts** (host repo; adapt names to your stack):
```
scripts/
|-- parse_events_csv.py            # Parse an events CSV export
|-- parse_users_csv.py             # Parse a users/engagement CSV export
|-- fetch_analytics.py             # API fetcher (PostHog / GA4-BigQuery)
|-- collect_metrics.py             # Calculate metrics and save to history
`-- analytics_history.py           # Historical tracking and trend analysis
```

---

## Integration with Other Skills

### Use in Initiative Breakdown

When breaking down an initiative:
```bash
# 1. Run product analytics
/product-analytics --feature="Checkout"

# 2. Use insights in the breakdown
/initiative-breakdown PROJ-10 --research="docs/analytics/feature-checkout-[date].md"
```

**Benefits:**
- Data-driven scope (focus on low-adoption features)
- Success metrics (increase adoption from X% to Y%)
- Risk mitigation (fix tracking gaps first)

---

### Use in Product Spec

When writing a PRD:
```bash
# 1. Get current state
/product-analytics --feature="Search"

# 2. Reference in PRD (illustrative numbers)
Problem: Search adoption is below the 50% target
Opportunity: High completion rate suggests the UX is good, discovery is the gap
Success Metric: Increase search adoption from X% to Y% next quarter
```

---

## Examples

### Example 1: Full Analysis (with historical trends)

**Input:**
```bash
/product-analytics
```

**Output** (all numbers illustrative):
```
Running Product Analytics...

Loading data: data/events-latest.json + data/users-latest.json
Period: [7-day range]
Events: 50 analyzed
Users: 20,000 active

Loading historical data...
Found 15 snapshots (oldest: [date], latest: [date])

Calculating trends...
DAU: 18K -> 20K (+11% over 4 weeks) UP
MAU: 45K -> 48K (+7% over 4 weeks) UP
Stickiness: 38% -> 42% (+4pp over 4 weeks) UP

Analyzing features...
OK      Onboarding (adoption: 90%, conversion: 80%, trend: +2% over 4 weeks)
PROBLEM Checkout (adoption: 62%, conversion: UNKNOWN - missing tracking!, trend: +5%)
AT-RISK Search (adoption: 35%, conversion: N/A, trend: -3% declining)
OK      Notifications (open rate: 45%, trend: stable)

Generating insights...
3 critical issues found
5 high-priority opportunities
2 optimization ideas

Saving snapshot to history...
Snapshot saved for [date]
WoW Comparison (DAU): 20.0K this week vs 19.4K last week (+0.6K, +3.1%)

Report saved: docs/analytics/product-report-[date].md

Critical Actions:
1. Add checkout_done event (P0 - blocks funnel measurement)
2. Add error tracking (P0 - cannot debug failures)
3. Investigate Search adoption decline (-3% over 4 weeks)
```

---

### Example 2: Weekly Report (with trends)

**Input:**
```bash
/product-analytics --weekly
```

**Output** (all numbers illustrative):
```
Weekly Product Report

Period: Week N
Previous: Week N-1
Historical data: 15 snapshots

Top-Line Metrics:
DAU: 20K (+3% WoW, +11% over 4 weeks)
MAU: 48K (stable WoW, +7% over 4 weeks)
Stickiness: 42% (+0.5pp WoW, +4pp over 4 weeks)
Sessions/user: 6.9 (no change)
Engagement: 57 screens/user (+3% WoW)

Feature Performance Trends (4-week):
OK      Checkout: 62% adoption (+5% over 4 weeks, +2% WoW)
AT-RISK Search: 35% adoption (-3% over 4 weeks, -1% WoW) - DECLINING
OK      Notifications: 45% open rate (+8% over 4 weeks, +4% WoW)
OK      Onboarding: 90% adoption (+2% over 4 weeks)

New Issues:
P0 Checkout completion tracking still missing (3rd week)
P1 Search adoption declining trend confirmed (3 consecutive weeks down)

Action Items:
P0 (carryover): 3 items
P1 (new this week): 2 items
P2 (monitoring): 1 item

Trend Analysis:
- Overall engagement UP (positive momentum)
- Core feature (Checkout) growing
- Secondary feature (Search) needs attention

Report saved: docs/analytics/weekly-report-[date].md
Trend report saved: docs/analytics/trends-[date].md
History updated: 16 snapshots tracked
```

---

## Success Criteria

**This skill is successful if:**
- Reports are generated in <2 minutes
- Insights are actionable (specific P0/P1/P2 items)
- Data quality issues are flagged automatically
- The PO can use the report to prioritize features
- Integration with initiative breakdown works

---

## Troubleshooting

### No data file found

**Error:** "No event data found in data/ directory"

**Fix:**
1. Export a CSV from your analytics tool (e.g. GA4: Reports -> Events -> Export)
2. Run: `python scripts/parse_events_csv.py path.csv --output data/events-latest.json`
3. Retry the skill

---

### Data too old

**Warning:** "Data is 14 days old. Refresh recommended."

**Fix:**
- Export a fresh CSV
- Or set up the API fetcher (`analytics.data_source: api` in config.yml)

---

### Missing framework file

**Error:** "Product Analytics Framework not found"

**Fix:**
- Create the file at the path configured in `analytics.framework_file`
- It should define: your metric definitions, known tracking gaps, and per-feature health criteria

---

### API auth failures

**Error:** 401/403 from the analytics API

**Fix:**
- Check `.env` has the right key (e.g. `POSTHOG_API_KEY`) -- never hardcode keys in config or scripts
- Check `analytics.api_host` in `config.yml` points at your instance
- Fail fast: retry once, then fall back to CSV export

---

## Next Steps

After running this skill:
1. Review the generated report
2. Prioritize action items (P0 -> P1 -> P2)
3. Create tracker tasks for P0 tracking gaps
4. Schedule a weekly recurring run
5. Feed insights into your next initiative breakdown

---

**Owner:** Product team
**Dependencies:** parser/fetcher scripts (see Output Locations), Product Analytics Framework file, `config.yml`
