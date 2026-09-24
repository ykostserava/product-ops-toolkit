"""What a headless `claude -p` child is allowed to inherit."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from claude_cli import (  # noqa: E402
    CREDENTIAL_VARS,
    INHERIT_FLAG,
    KEPT_VARS,
    NESTED_SESSION_VARS,
    PROVIDER_ROUTING_VARS,
    headless_env,
    routing_report,
)

TRAY_LIKE = {
    "PATH": "/usr/bin",
    "CLAUDE_CODE_GIT_BASH_PATH": "C:/Program Files/Git/bin/bash.exe",
    "CLAUDE_CODE_USE_VERTEX": "1",
    "ANTHROPIC_VERTEX_PROJECT_ID": "my-vertex-project",
    "GOOGLE_CLOUD_PROJECT": "my-vertex-project",
    "GOOGLE_CLOUD_LOCATION": "global",
    "VERTEX_REGION_CLAUDE_5_SONNET": "us-east5",
    "ANTHROPIC_API_KEY": "sk-invalid-from-dotenv",
    "CLAUDECODE": "1",
    "MY_APP_SETTING": "kept",
}


def test_strips_routing_credentials_and_session_markers():
    env = headless_env(TRAY_LIKE)
    assert "CLAUDE_CODE_USE_VERTEX" not in env
    assert "ANTHROPIC_VERTEX_PROJECT_ID" not in env
    assert "VERTEX_REGION_CLAUDE_5_SONNET" not in env
    assert "ANTHROPIC_API_KEY" not in env
    assert "CLAUDECODE" not in env
    assert env["MY_APP_SETTING"] == "kept"
    assert env["PATH"] == "/usr/bin"


def test_git_bash_path_is_kept():
    assert headless_env(TRAY_LIKE)["CLAUDE_CODE_GIT_BASH_PATH"].endswith("bash.exe")


def test_kept_vars_are_never_in_any_strip_list():
    for name in KEPT_VARS:
        assert name not in CREDENTIAL_VARS
        assert name not in PROVIDER_ROUTING_VARS
        assert name not in NESTED_SESSION_VARS


def test_inherit_flag_keeps_provider_and_credentials_but_not_session():
    env = headless_env({**TRAY_LIKE, INHERIT_FLAG: "1"})
    assert env["CLAUDE_CODE_USE_VERTEX"] == "1"
    assert env["ANTHROPIC_API_KEY"] == "sk-invalid-from-dotenv"
    assert "CLAUDECODE" not in env


def test_routing_report_names_what_was_stripped_without_values():
    report = routing_report(TRAY_LIKE)
    assert report.startswith("inherit_provider=0 stripped=")
    assert "ANTHROPIC_API_KEY" in report and "sk-invalid" not in report
    assert routing_report({"PATH": "x"}) == "inherit_provider=0 stripped=none"
