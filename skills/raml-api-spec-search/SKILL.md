---
name: raml-api-spec-search
description: Use when needing to find API endpoints, request/response schemas, or RAML specifications from a central api-spec repository. Authoritative producer-side source of truth that pairs with consumer-side scans of iOS, Android, or web codebases. Triggers on questions about available APIs, endpoint paths, request/response formats, or capability gaps across any platform.
license: MIT
---

# RAML API Spec Search

Find information about available APIs from a central RAML specification repository (typically hosted on GitLab, GitHub, or Bitbucket).

This is the **producer-side source of truth** — what backend officially exposes. Pair it with a consumer-side scan (e.g. the `codebase-research` skill in this toolkit) of any client codebase — **iOS, Android, or web** — to see who consumes what.

> Configure the placeholders below in `config.yml` (or `.env`) before running. Defaults assume a single GitLab project hosting all RAML specs.

```yaml
# config.yml example
api_spec:
  host: gitlab.example.com         # or github.com, bitbucket.org
  project: ORG/api-spec             # URL-encoded project path
  default_branch: master
  token_env_var: GITLAB_TOKEN       # name of env var holding the API token
```

## When to Use

- Need to know what endpoints an API offers
- Looking for request/response schemas for an endpoint
- Checking if a specific API capability exists
- Need the RAML type definition for a data model
- Comparing what the API spec says vs what a client implements — **iOS SDK, Android SDK, or web frontend**
- Finding endpoints that exist on backend but no platform consumes (backend-only / under-utilised APIs)
- Verifying that a brief / PRD assumption holds at the protocol level before scoping platform work

## Repository Structure (typical convention)

A central api-spec repo usually contains many specifications in **RAML 1.0** format, one folder per service:

```
app-{service}/
  {sub-api}/
    api.raml              # Main spec: endpoints, methods, parameters
    api.html              # Generated HTML docs (optional)
    types/*.raml          # Data type definitions
    examples/
      requests/*.json     # Request body examples
      responses/*.json    # Response body examples
    traits/*.raml         # Reusable traits (filters, pagination)
    security/             # Security scheme definitions
```

If your repo uses a different convention, swap the folder names below — the search/read commands stay the same.

## How to Search

Two interchangeable transports:

**A. `glab` CLI** (preferred for GitLab-hosted repos when installed and authenticated). For GitHub use `gh`.

**B. `curl` fallback** when no CLI is available. Sources the API token from a `.env` file and hits the GitLab REST API directly.

```bash
# Source token (path varies per setup)
set -a; source .env; set +a
BASE="${GITLAB_URL:-https://gitlab.example.com}/api/v4/projects/<URL_ENCODED_PROJECT_PATH>"

# search
curl -sH "PRIVATE-TOKEN: $GITLAB_TOKEN" "$BASE/search?scope=blobs&search=KEYWORD&per_page=20"

# list directory
curl -sH "PRIVATE-TOKEN: $GITLAB_TOKEN" "$BASE/repository/tree?path=app-{service}&per_page=100"

# read file
curl -sH "PRIVATE-TOKEN: $GITLAB_TOKEN" "$BASE/repository/files/app-{service}%2Fapi.raml/raw?ref=master"
```

URL-encode `/` as `%2F` when passing file paths.

### 1. Search by keyword (best for discovering endpoints)

```bash
glab api "projects/<PROJECT_ID>/search?scope=blobs&search=KEYWORD&per_page=20"
```

Results include `path`, `startline`, and `data` (matching content). Filter results to `.raml` files for specs, `.json` for examples.

### 2. List API directories (find which APIs exist)

```bash
# List all top-level API directories
glab api "projects/<PROJECT_ID>/repository/tree?per_page=100"

# List sub-APIs within a specific service
glab api "projects/<PROJECT_ID>/repository/tree?path=app-{service}&per_page=100"
```

### 3. Read a specific file (get full spec content)

```bash
# URL-encode the file path (/ becomes %2F)
glab api "projects/<PROJECT_ID>/repository/files/<FILE_PATH_ENCODED>/raw?ref=master"
```

Examples:
```bash
# Read service spec
glab api "projects/<PROJECT_ID>/repository/files/app-{service}%2Fapi.raml/raw?ref=master"

# Read a type definition
glab api "projects/<PROJECT_ID>/repository/files/app-{service}%2Ftypes%2F{type-name}.raml/raw?ref=master"

# Read a response example
glab api "projects/<PROJECT_ID>/repository/files/app-{service}%2Fexamples%2Fresponses%2F{example}.json/raw?ref=master"
```

### 4. List files in a directory

```bash
glab api "projects/<PROJECT_ID>/repository/tree?path=app-{service}%2Ftypes&per_page=100"
```

## Client SDK / call-site hints

When comparing the spec against actual usage, look in these places (consumer-side):

| Platform | Where call sites live | How to spot them |
|---|---|---|
| **iOS** | `Packages/*SDK/Sources/.../Services/*Api.swift` (Alamofire enum-router pattern); also raw `URLRequest` / `URLSession` / `Alamofire.AF.request(...)` | `enum SomeApi { case ... }` + `extension SomeApi: PSApi { var path: ... var method: ... }` |
| **Android** | `sdks/<feature>/src/main/java/com/<org>/sdks/<feature>/retrofit/NetworkApiClient.kt` (Retrofit interface) | `@GET / @POST / @PUT / @DELETE / @PATCH("path")` annotations |
| **Web** | `axios.<method>('...')`, `fetch('...')`, generated SDK clients, sometimes a typed API layer (e.g. `api/<resource>.ts`) | URL string literals with `/rest/v1/...`; explicit method parameter for `fetch` |

For richer call-site discovery use the **`codebase-research` skill** — it greps these patterns and produces a per-platform call-site JSON that joins cleanly with the spec.

## RAML Quick Reference

RAML files define APIs like this:

```yaml
#%RAML 1.0
title: API Name
baseUri: https://example.com/rest/v1
mediaType: application/json

types:
  MyType: !include types/my-type.raml

/resource:
  get:
    description: List resources
    queryParameters:
      limit:
        type: integer
    responses:
      200:
        body:
          type: MyType[]
  post:
    body:
      type: MyType
    responses:
      200:
        body:
          type: MyType

  /{id}:
    get:
      description: Get single resource
    put:
      body:
        type: MyType
    delete:
```

Type definitions:
```yaml
#%RAML 1.0 DataType
type: object
properties:
  id:
    type: integer
    required: true
  name:
    type: string
  status:
    type: string
    enum: [active, inactive]
```

## Workflow

### A. Spec lookup (default)

When the user asks about an API:

1. **Identify the service** — determine which `app-*` directory is relevant
2. **List sub-APIs** — browse the directory to find the right sub-API
3. **Read the RAML spec** — fetch `api.raml` for endpoints and parameters
4. **Read types if needed** — fetch type definitions from `types/` for schemas
5. **Read examples if needed** — fetch from `examples/` for request/response samples
6. **Present findings** — summarize endpoints, parameters, schemas in a clear format

For broad searches ("what APIs handle <topic>?"), use the search endpoint first, then drill into specific specs.

### B. Spec ↔ Client comparison (cross-platform gap analysis)

When the user asks "does iOS / Android / web actually use this?" or "what does the spec offer that platform X doesn't consume?":

1. **Fetch the authoritative spec** — `app-X/api.raml` (+ types as needed)
2. **Extract the endpoint inventory** — list of (method, path) tuples from the RAML
3. **Get client call sites** — preferred: invoke the `codebase-research` skill with `--platform ios|android|web` to produce a JSON of call sites from the relevant repo. Fallback: grep manually with patterns from the SDK / call-site hints table above.
4. **Build a coverage matrix** — endpoint × {Backend, iOS, Android, Web}, marking each cell OK / MISSING / N/A
5. **Highlight gaps**:
   - **Backend-only**: spec defines it, no client calls — candidate for adoption or deprecation
   - **Platform-missing**: some platforms call it, others don't — consistency risk
   - **Drift**: client calls a path the spec doesn't define — likely deprecated, dynamic, or undocumented
6. **Present PO-ready output** — focus on what the gaps mean for scoping, not raw lists

### Platform-specific notes for step 3

- **iOS**: enum-router pattern (`SavingsApi.swift`-style) means the path string isn't on the same line as `@GET`-style annotations. Read the `var path` switch in the SDK's `*Api.swift` file directly — regex grep alone often misses these and reports `method: "?"`.
- **Android**: Retrofit annotations carry method + path on the same line — clean grep usually suffices.
- **Web**: paths often built from constants or template literals (`` `${BASE}/<resource>/${id}` ``); also check generated SDK clients (`api/<resource>.ts`, `services/<Resource>Api.ts`, etc.) and any GraphQL operations that wrap the REST API.
