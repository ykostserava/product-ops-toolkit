---
name: codebase-research
description: Multi-platform codebase investigation for Product Owners. Maps backend endpoints first, then traces their consumption across mobile (iOS, Android) and web frontends. Produces a PO-ready coverage matrix showing which endpoints are used by which platforms, gaps, and inconsistencies. Use when investigating feature scope, planning a redesign, auditing API coverage, or preparing a brief that spans backend + mobile + web.
license: MIT
metadata:
  version: 1.0.0
---

# Codebase Research

Investigate a codebase the way a Product Owner needs to: **what does the backend expose, who consumes it, and where are the gaps?**

This skill runs an ordered three-phase exploration — Backend → Mobile (iOS + Android) → Web — and produces a coverage matrix you can drop into a brief, PRD, or wiki page.

---

## Quick Start

```
/codebase-research <repo-path-or-paths>
/codebase-research backend=./api mobile_ios=./ios mobile_android=./android web=./web
/codebase-research feature="<feature-keyword>"   # scope to a feature area
```

If only one path is given, the skill auto-detects sub-projects (monorepo) or asks for the missing platforms.

---

## Triggers

Invoke this skill when the user says any of:

- "research the codebase", "investigate the code", "explore this repo for me"
- "what endpoints does X expose", "which platforms use endpoint Y"
- "map backend to mobile/web", "API coverage", "endpoint inventory"
- "I need to understand <feature> across backend + mobile + web"
- "audit which platforms call which endpoints"

Do **not** invoke for: a single-file read, a one-line grep, code review, or new feature design (use a generic explorer agent for new-build scoping).

---

## Quick Reference

| Phase | Goal | Output |
|---|---|---|
| 0. Scope | Confirm paths, feature filter, depth | Scope confirmation |
| 1. Backend | Inventory endpoints (method, path, handler, auth, DTO) | `endpoints.md` table |
| 2. Mobile | Find calls in iOS + Android, map to endpoints | `mobile-usage.md` |
| 3. Web | Find calls in web frontends, map to endpoints | `web-usage.md` |
| 4. Synthesis | Coverage matrix + gaps + inconsistencies | `coverage-matrix.md` |

---

## How It Works

```
Phase 0: SCOPE CONFIRMATION
  - Detect repo layout (monorepo vs separate repos)
  - Confirm: backend path, iOS path, Android path, web path
  - Confirm feature filter (e.g. "savings", "auth") or "all"
  - Confirm output location (default: ./docs/research/<timestamp>/)

Phase 1: BACKEND ENDPOINT INVENTORY
  - Detect framework (Symfony, Spring, NestJS, FastAPI, Express, Rails, etc.)
  - Extract: HTTP method, path, controller/handler, auth requirement,
    request DTO, response DTO, deprecation markers
  - Filter by feature scope if provided
  - Produce: endpoints.md with one row per endpoint

Phase 2: MOBILE USAGE MAPPING (iOS + Android in parallel)
  iOS:
    - Search Swift/Obj-C for URL strings, API client calls, generated SDK usage
    - Map each call site to a backend endpoint (best-effort path matching)
  Android:
    - Search Kotlin/Java for Retrofit interfaces, OkHttp, generated clients
    - Map each call site to a backend endpoint
  - Flag: endpoints called by mobile but not in backend inventory (drift)
  - Flag: endpoints in backend never called by mobile (unused-on-mobile)

Phase 3: WEB USAGE MAPPING
  - Detect web stack (React, Vue, Angular, vanilla, plus axios/fetch/SDK)
  - Search for API calls, map to endpoints
  - Flag: web-only endpoints, web-missing endpoints

Phase 4: SYNTHESIS
  - Build coverage matrix: endpoint x [backend, iOS, Android, web]
  - Highlight: platform gaps, deprecated-but-used, mobile-only, web-only
  - Generate PO summary: top findings, scope implications, risks
```

---

## Commands

| Command | Action |
|---|---|
| `/codebase-research <path>` | Auto-detect and run all phases |
| `/codebase-research --scope <feature>` | Filter to a feature area |
| `/codebase-research --phase backend` | Run only Phase 1 |
| `/codebase-research --phase mobile` | Run only Phase 2 (requires endpoints.md) |
| `/codebase-research --phase web` | Run only Phase 3 (requires endpoints.md) |
| `/codebase-research --refresh` | Re-run from cached scope |

---

## Output Structure

```
docs/research/<YYYY-MM-DD>/
+-- 00-scope.md             # Confirmed paths, feature filter, frameworks detected
+-- 01-endpoints.md         # Backend endpoint inventory (one row per endpoint)
+-- 02-mobile-usage.md      # iOS + Android call sites mapped to endpoints
+-- 03-web-usage.md         # Web call sites mapped to endpoints
+-- 04-coverage-matrix.md   # endpoint x platform table + gaps
\-- 99-summary.md           # PO-ready findings, risks, scope implications
```

### `01-endpoints.md` row format

| # | Method | Path | Handler | Auth | Request DTO | Response DTO | Deprecated | Feature Tag |
|---|---|---|---|---|---|---|---|---|

### `04-coverage-matrix.md` row format

| Endpoint | Backend | iOS | Android | Web | Notes |
|---|:-:|:-:|:-:|:-:|---|
| `GET /v1/<resource>` | OK | OK | OK | MISSING | Web team has not adopted; check roadmap |
| `POST /v1/<resource>/action` | OK | MISSING | MISSING | MISSING | Backend-only; not yet wired up |

---

## Scripts

| Script | Purpose |
|---|---|
| `scripts/detect_stack.py` | Detect backend framework, mobile platforms, web stack from a path |
| `scripts/extract_endpoints.py` | Parse routes from common backend frameworks -> JSON |
| `scripts/find_api_callsites.py` | Grep mobile/web sources for HTTP calls -> JSON |
| `scripts/build_coverage_matrix.py` | Join endpoints + call sites -> markdown matrix |

All scripts are pure-Python stdlib, exit 0 on success / 1 on failure / 10 on validation failure. Run independently or chained by the skill.

```bash
python scripts/detect_stack.py /path/to/repo
python scripts/extract_endpoints.py /path/to/backend --feature <feature> > endpoints.json
python scripts/find_api_callsites.py /path/to/ios --platform ios > ios_calls.json
python scripts/build_coverage_matrix.py endpoints.json --ios ios_calls.json --android android_calls.json --web web_calls.json --out matrix.md
```

---

## Anti-Patterns

| Avoid | Why | Instead |
|---|---|---|
| Reading every file | Burns context, no value | Frame queries by feature scope first |
| Trusting one regex pass | Misses generated SDK calls, dynamic URLs | Combine grep + framework-specific parsing |
| Reporting raw grep output | Not PO-actionable | Always produce the coverage matrix |
| Skipping the scope phase | Produces noise across the whole repo | Always confirm feature filter |
| Forcing one report format | Different stakeholders need different cuts | Keep phase outputs separate; summary is the deliverable |

---

## Verification Checklist

Before declaring research complete:

- [ ] Scope confirmed with user (paths + feature filter)
- [ ] Each platform path either mapped or explicitly marked "not in scope"
- [ ] `endpoints.md` has at least one row OR explicitly states "no endpoints match feature filter"
- [ ] Every endpoint row in `coverage-matrix.md` has a status for each platform (OK / MISSING / N/A)
- [ ] Gaps section in `99-summary.md` lists at least: backend-only endpoints, platform-missing endpoints, drift (mobile/web calling endpoint not in backend inventory)
- [ ] Output saved to `docs/research/<date>/` and path reported back to user

---

## Related Skills / Patterns

| Where | Relationship |
|---|---|
| `raml-api-spec-search` skill (this toolkit) | Use as the producer-side pair when the backend is documented as RAML, not extracted from code |
| Built-in Explore agent | Use as the search engine inside Phase 1-3 |
| Wiki / Confluence integration | Push the summary to a docs page once research is done |
| Jira integration | Cross-reference endpoints with existing epics / stories |

---

## Extension Points

1. **New backend frameworks** - add a parser to `scripts/extract_endpoints.py`
2. **New mobile/web stacks** - add a matcher to `scripts/find_api_callsites.py`
3. **Custom output cuts** - add templates under `assets/templates/` (e.g. per-team view, per-epic view)
4. **Cross-link to tickets** - extend Phase 4 to query Jira/Confluence for each endpoint

---

## Deep Dive

<details>
<summary><strong>Phase 1: Backend Endpoint Inventory</strong></summary>

### Detection order

1. Look for OpenAPI/Swagger spec (`openapi.yaml`, `swagger.json`) - fastest, most reliable
2. If absent, detect framework from manifests:
   - `composer.json` + Symfony/Laravel -> parse route configs and `#[Route]` attributes
   - `pom.xml` / `build.gradle` + Spring -> parse `@RequestMapping` / `@GetMapping` etc.
   - `package.json` + NestJS -> parse `@Controller` + `@Get/@Post...`
   - `package.json` + Express -> parse `app.get/post/...` and `router.*`
   - `requirements.txt` / `pyproject.toml` + FastAPI -> parse `@app.get/post`
   - `Gemfile` + Rails -> parse `config/routes.rb`
3. If unknown, fall back to grep for common HTTP verb patterns and ask user

### Per-endpoint extraction

For each route found, extract:
- HTTP method, path (with parameters)
- Controller class + method (handler)
- Auth requirement (annotation, middleware, decorator)
- Request DTO/schema (if typed)
- Response DTO/schema (if typed)
- Deprecation markers (`@Deprecated`, `deprecated: true`)
- Feature tag (best-effort: from path prefix, controller namespace, or annotation)

### Feature filtering

If user passes `--scope <feature>`, filter to endpoints where any of:
- Path contains `/<feature>/`
- Controller class name contains the feature keyword
- File path contains the feature keyword

</details>

<details>
<summary><strong>Phase 2: Mobile Usage Mapping</strong></summary>

### iOS detection

1. Find `*.xcodeproj`, `Package.swift`, `Podfile`
2. Search `*.swift` and `*.m` for:
   - `URLRequest(url:`, `URL(string:`
   - URL string literals matching `/^https?:\/\/` or `/v\d+\//`
   - Generated SDK clients (Swagger/OpenAPI Generator output usually has class suffix `API`)
   - Common HTTP libraries: Alamofire (`AF.request`, `session.request`), URLSession (`dataTask`)
3. For each call site, extract: file:line, HTTP method (if explicit), URL template, auth header usage

### Android detection

1. Find `build.gradle(.kts)`, `AndroidManifest.xml`
2. Search `*.kt` and `*.java` for:
   - Retrofit interfaces (`@GET`, `@POST`, `@PUT`, `@DELETE`, `@PATCH` annotations on methods)
   - OkHttp `Request.Builder().url(...)`
   - Generated SDK clients
3. Extract: file:line, method, path template, auth interceptor usage

### Mapping to backend endpoints

Path matching is best-effort:
- Exact match on method + path -> confident match
- Method match + path match modulo `{param}` placeholders -> confident match
- Partial path match -> fuzzy match, flag for review
- No match -> "drift" (mobile calls something backend inventory doesn't list)

### Output

Each endpoint in `01-endpoints.md` gets two new columns in `02-mobile-usage.md`: iOS call sites count + Android call sites count, with file:line references.

</details>

<details>
<summary><strong>Phase 3: Web Usage Mapping</strong></summary>

### Web stack detection

1. `package.json` -> identify React / Vue / Angular / Svelte
2. Identify HTTP layer: axios, fetch, ky, generated SDK, GraphQL client
3. Search `*.ts/.tsx/.js/.jsx/.vue` for:
   - `axios.{get,post,...}('...')`, `fetch('...')`
   - SDK client method calls (if generated)
   - GraphQL operations (separate sub-inventory)

### Mapping

Same matching rules as mobile. GraphQL operations are listed separately in `03-web-usage.md` with their resolver mapping if discoverable from backend.

</details>

<details>
<summary><strong>Phase 4: Synthesis</strong></summary>

### Coverage matrix

Build a single table joining endpoints with platform usage:

```
| Endpoint              | Backend | iOS | Android | Web | Notes                        |
|-----------------------|:-:|:-:|:-:|:-:|------------------------------------|
| GET /v1/<resource>    | OK  | OK  | OK  | --  | Web missing - confirm with team    |
```

### Gap categories

- **Backend-only**: endpoint exists, no platform calls it -> candidate for deprecation or "not yet wired"
- **Platform-missing**: endpoint called on some platforms but not all -> consistency risk
- **Drift**: platform calls endpoint not in backend inventory -> either deprecated, dynamic, or extraction missed it
- **Deprecated-but-used**: backend marks endpoint deprecated, platforms still call it -> migration risk

### PO-ready summary

`99-summary.md` always contains:
1. Top 5 findings (one-liners)
2. Scope implications (what this means for the brief / PRD / roadmap)
3. Risks (deprecated-but-used, drift, platform inconsistency)
4. Suggested next actions (e.g. "confirm with web team", "raise ticket for Android gap")

</details>
