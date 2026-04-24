---
description: Analyze product metrics from GA4 / Firebase and generate insights reports
---

# Product Analytics Skill

Automated analysis of product metrics from analytics sources (GA4, Firebase, PostHog, etc.). Generates markdown reports with adoption, engagement, and conversion metrics.

## Usage

```bash
# Full analysis
/product-analytics

# Weekly report
/product-analytics --weekly

# Feature-specific analysis
/product-analytics --feature="Transfers"

# Compare periods
/product-analytics --compare --period1="last-week" --period2="prev-week"
```

---

## What It Does

1. **Loads data** from your analytics source (CSV export or API)
2. **Analyzes metrics** by adoption / engagement / conversion framework
3. **Generates insights** with recommendations
4. **Saves report** as markdown

---

## Configuration

Before first use, configure:

- **Data source:** CSV path, or API credentials (GA4 / Firebase / PostHog)
- **Framework file:** reference document describing your metric definitions (e.g. `memory/analytics/framework.md`)
- **Feature list:** names of features to track (for feature-specific analysis)

---

## Workflow

### Phase 1: Load Data

Check for fresh data. If older than N days or missing, prompt the user to export from the analytics tool or run the API fetcher.

```bash
# CSV-based load
python scripts/parse_csv.py [csv-path] --output data/events-latest.json

# API-based load (when configured)
python scripts/fetch_analytics.py --events --engagement --output data/latest.json
```

### Phase 2: Analyze Metrics

Load the analytics framework (what each metric means for your product), then calculate:

**Adoption rate:**
```
Adoption = (Users who used feature / Total active users) * 100%
```

**Engagement rate:**
```
Engagement = Events per active user per period
```

**Conversion rate (for funnels):**
```
Conversion = (Completion events / Entry events) * 100%
```

**User segmentation:**
```
Power users: >10 events / week
Active users: 3-10 events / week
Light users: <3 events / week
```

### Phase 3: Generate Insights

For each feature:
- What's adoption trending?
- Which user segments use it most?
- What's the drop-off in funnels?
- Are there tracking gaps (events expected but missing)?

### Phase 4: Write Report

Save to `docs/analytics/[YYYY-MM-DD]-product-analytics.md` with:
- Executive summary
- Key metrics per feature (table)
- Insights and anomalies
- Recommendations with owners
- Tracking gaps to fix

---

## Output Quality Rules

- Every insight cites a specific number or percentage
- Every recommendation has an owner (team or role)
- Tracking gaps are flagged separately for analytics engineering
- Period-over-period comparisons when possible

## Integration

- `/product-spec` - use analytics findings to motivate new PRDs
- Initiative Breakdown skill - add analytics tasks to each epic that introduces new user flows
