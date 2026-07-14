# API Access & Credentials

Example of an **unconditional rule**: where credentials live and how to behave when
internal APIs fail. Saves entire sessions from being burned on auth retry loops.

- **Check `.env` files FIRST** — look in the current project AND sibling directories
  for existing API keys/tokens before asking the user
- **Fail fast on API errors** — if a call fails with an auth/permission error, try
  ONCE, then immediately ask the user for one of:
  1. Manual content provision, OR
  2. Credentials location, OR
  3. Skip this step and move on
- **NEVER retry auth failures more than once** — don't waste time on repeated
  failed attempts

## Known-flaky services
List services whose API access frequently fails in your environment (e.g. an internal
wiki behind SSO). For those, go straight to "paste the content manually" after one
failed attempt.
