"""The environment a headless `claude -p` child process is given.

Every script here that spawns `claude -p` (the board-sync eval today) goes
through headless_env() instead of hand-rolling its own filter, so a child
never inherits something that sends it somewhere other than the machine's
Claude login:

  - credentials: an inherited (even invalid) ANTHROPIC_API_KEY takes precedence
    over the subscription login the CLI would otherwise use; ANTHROPIC_CUSTOM_
    HEADERS can carry an Authorization header and is stripped with it;
  - provider routing: the switches that send the CLI to Vertex / Bedrock /
    Foundry / a gateway, the endpoint and project overrides that go with them,
    and the MODEL-ID overrides - with routing stripped but a provider-form
    model id left in place, the child asks the subscription for a model it
    does not know. Routing is listed BY NAME because the CLAUDE_CODE_USE_* and
    CLAUDE_CODE_SKIP_* prefixes also hold unrelated feature toggles;
  - nested-session markers: set when a script is itself run from inside a
    Claude Code session; they make the child believe it is a sub-session.

A background job must not inherit an interactive routing switch: a tray or
scheduler started in the morning would otherwise freeze that morning's
`/vertex on` and hand it to every child for the rest of the day.

CLAUDE_CLI_INHERIT_PROVIDER=1 (or inherit_provider=True) keeps the provider
environment verbatim - routing AND the credentials that go with it, because a
gateway reached through ANTHROPIC_BASE_URL authenticates with the very token
this module otherwise strips. Nested-session markers are stripped either way.
"""

import os

#: Can carry a credential; never handed to a child that should use the login.
CREDENTIAL_VARS = frozenset(
    {
        "ANTHROPIC_API_KEY",
        "ANTHROPIC_AUTH_TOKEN",
        "ANTHROPIC_IDENTITY_TOKEN",
        "ANTHROPIC_IDENTITY_TOKEN_FILE",
        "ANTHROPIC_CUSTOM_HEADERS",
    }
)

PROVIDER_ROUTING_VARS = frozenset(
    {
        # routing switches
        "CLAUDE_CODE_USE_VERTEX",
        "CLAUDE_CODE_USE_BEDROCK",
        "CLAUDE_CODE_USE_FOUNDRY",
        "CLAUDE_CODE_USE_GATEWAY",
        "CLAUDE_CODE_USE_MANTLE",
        "CLAUDE_CODE_USE_ANTHROPIC_AWS",
        "CLAUDE_CODE_USE_ANTHROPIC_GOOGLE_CLOUD",
        # auth-skip switches that only mean anything to a routed CLI
        "CLAUDE_CODE_SKIP_VERTEX_AUTH",
        "CLAUDE_CODE_SKIP_BEDROCK_AUTH",
        "CLAUDE_CODE_SKIP_FOUNDRY_AUTH",
        "CLAUDE_CODE_SKIP_MANTLE_AUTH",
        "CLAUDE_CODE_SKIP_ANTHROPIC_AWS_AUTH",
        "CLAUDE_CODE_SKIP_ANTHROPIC_GOOGLE_CLOUD_AUTH",
        "CLAUDE_CODE_SKIP_AWS_CRED_CACHE",
        # endpoint / project overrides
        "ANTHROPIC_BASE_URL",
        "ANTHROPIC_VERTEX_BASE_URL",
        "ANTHROPIC_VERTEX_PROJECT_ID",
        "ANTHROPIC_BEDROCK_BASE_URL",
        "ANTHROPIC_BEDROCK_MANTLE_BASE_URL",
        "ANTHROPIC_BEDROCK_REGION_PREFIX",
        "ANTHROPIC_BEDROCK_SERVICE_TIER",
        "ANTHROPIC_FOUNDRY_BASE_URL",
        "ANTHROPIC_FOUNDRY_RESOURCE",
        "ANTHROPIC_FOUNDRY_API_KEY",
        "ANTHROPIC_FOUNDRY_AUTH_TOKEN",
        "ANTHROPIC_AWS_BASE_URL",
        "ANTHROPIC_AWS_API_KEY",
        "ANTHROPIC_AWS_AUTH",
        "ANTHROPIC_AWS_WORKSPACE_ID",
        "ANTHROPIC_GOOGLE_CLOUD_AUTH",
        "ANTHROPIC_GOOGLE_CLOUD_BASE_URL",
        "ANTHROPIC_GOOGLE_CLOUD_LOCATION",
        "ANTHROPIC_GOOGLE_CLOUD_PROJECT",
        "ANTHROPIC_GOOGLE_CLOUD_WORKSPACE_ID",
        "AWS_BEARER_TOKEN_BEDROCK",
        "CLOUD_ML_REGION",
        "GOOGLE_APPLICATION_CREDENTIALS",
        "GOOGLE_CLOUD_AUTH",
        "GOOGLE_CLOUD_BASE_URL",
        "GOOGLE_CLOUD_PROJECT",
        "GOOGLE_CLOUD_LOCATION",
        "GOOGLE_CLOUD_QUOTA_PROJECT",
        "GOOGLE_CLOUD_WORKSPACE_ID",
        # model-id overrides: harmless with an explicit --model, fatal without
        "ANTHROPIC_MODEL",
        "ANTHROPIC_SMALL_FAST_MODEL",
        "ANTHROPIC_SMALL_FAST_MODEL_AWS_REGION",
        "ANTHROPIC_DEFAULT_OPUS_MODEL",
        "ANTHROPIC_DEFAULT_SONNET_MODEL",
        "ANTHROPIC_DEFAULT_HAIKU_MODEL",
        "ANTHROPIC_DEFAULT_FABLE_MODEL",
    }
)

#: The only prefix rule - a per-model family with no non-routing member.
PROVIDER_ROUTING_PREFIXES = ("VERTEX_REGION_",)

NESTED_SESSION_VARS = frozenset(
    {
        "CLAUDECODE",
        "CLAUDE_CODE_ENTRYPOINT",
        "CLAUDE_CODE_SESSION_ID",
        "CLAUDE_CODE_CHILD_SESSION",
        "CLAUDE_CODE_SESSION_ATTENDED",
        "CLAUDE_CODE_SSE_PORT",
        "CLAUDE_CODE_MESSAGING_SOCKET",
        "CLAUDE_CODE_EXECPATH",
        "CLAUDE_PID",
        "CLAUDE_EFFORT",
        "ANTHROPIC_SESSION_ID",
        "AI_AGENT",
    }
)

#: Never stripped - the child needs it to find bash on Windows.
KEPT_VARS = frozenset({"CLAUDE_CODE_GIT_BASH_PATH"})

INHERIT_FLAG = "CLAUDE_CLI_INHERIT_PROVIDER"


def _is_routing(name: str) -> bool:
    return name in PROVIDER_ROUTING_VARS or name.startswith(PROVIDER_ROUTING_PREFIXES)


def stripped_names(env: dict, inherit_provider: bool = False) -> set:
    """Which names headless_env() would remove from this environment."""
    dropped = {k for k in env if k in CREDENTIAL_VARS or k in NESTED_SESSION_VARS}
    if inherit_provider:
        dropped -= CREDENTIAL_VARS  # the provider environment is kept whole
    else:
        dropped |= {k for k in env if _is_routing(k)}
    return dropped


def headless_env(env: dict | None = None, inherit_provider: bool | None = None) -> dict:
    """Environment for a `claude -p` child: the caller's, minus what would send
    it somewhere other than this machine's Claude subscription login."""
    source = os.environ if env is None else env
    if inherit_provider is None:
        inherit_provider = source.get(INHERIT_FLAG, "") == "1"
    drop = stripped_names(source, inherit_provider)
    return {k: v for k, v in source.items() if k not in drop}


def routing_report(
    env: dict | None = None, inherit_provider: bool | None = None
) -> str:
    """What was TAKEN AWAY from this environment, by name, never by value."""
    source = os.environ if env is None else env
    if inherit_provider is None:
        inherit_provider = source.get(INHERIT_FLAG, "") == "1"
    dropped = sorted(stripped_names(source, inherit_provider))
    flag = "1" if inherit_provider else "0"
    return f"inherit_provider={flag} stripped={','.join(dropped) or 'none'}"
