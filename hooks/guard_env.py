"""PreToolUse hook: block Write/Edit on .env files.

Exits 2 (blocking error) when target path is .env, .env.local, .env.dev, etc.
Stderr is shown to the model so it knows why the write was blocked.
"""
import sys, json, os.path

try:
    data = json.load(sys.stdin)
except Exception:
    sys.exit(0)

file_path = data.get("tool_input", {}).get("file_path", "")
base = os.path.basename(file_path)

if base == ".env" or base.startswith(".env.") or base.endswith(".env"):
    sys.stderr.write(
        f".env file protected by hook policy: {file_path}\n"
        "Edit manually if you really need to change it.\n"
    )
    sys.exit(2)
