"""Team-specific Jira settings shared by every script in this directory.

The engines (board_consistency, jira_apply, jira_transition, duplicate_scan,
jira_batch_fetch) are generic; what differs per team is the project key, the
workflow's status names, which moves are one-way, and which fields a create
must carry. Those live in ONE JSON file instead of being re-typed per script:

    scripts/jira-config.json      (override the path with JIRA_CONFIG=...)

Every key is optional - missing keys fall back to DEFAULTS below, which
describe a plain Kanban workflow (Backlog -> In analysis -> Ready for Dev ->
In progress -> Ready for testing -> Closed). Edit the JSON, not this file.

Keys:
    project_key              the board's project key (JQL defaults, release
                             membership, "external" detection in R7)
    statuses.one_way         statuses with NO transition back - writers refuse
                             them without an explicit confirmation flag
    statuses.closed          the terminal status (needs a resolution)
    statuses.epic_active     where an Epic goes when its first child starts
    statuses.r4_active       statuses where somebody must own the issue
    statuses.r4_exempt_types issue types that stay unassigned by design
    statuses.r6_stale        statuses where long silence means stuck work
    statuses.r8_ready        statuses that count as release-ready
    parent_link_types        issue-link type names that mean "parent of"
                             (Initiative <- Epic)
    create_rules.require_components
                             refuse a create with no components (some Jira
                             Server projects 400 without them)
    create_rules.risk_class  {"field": "customfield_NNNNN", "issuetypes":
                             ["1"]} - a required custom field on given
                             issue types; null to disable
    create_rules.components_requiring_assignee
                             component names whose new issues must name an
                             assignee (the engine refuses, it never picks)
    readiness_fields         {"label": "customfield_NNNNN"} custom fields the
                             readiness trim of jira_batch_fetch keeps
                             (acceptance criteria, flagged, dates, ...)
"""

import copy
import json
import os
from pathlib import Path

DEFAULT_PATH = Path(__file__).parent / "jira-config.json"

DEFAULTS = {
    "project_key": "PROJ",
    "statuses": {
        "one_way": ["Closed", "Ready for Dev"],
        "closed": "Closed",
        "epic_active": "In analysis",
        "r4_active": [
            "In analysis",
            "Ready for Dev",
            "In progress",
            "Ready for testing",
        ],
        "r4_exempt_types": ["Initiative", "Epic"],
        "r6_stale": ["In progress", "Ready for testing"],
        "r8_ready": ["Closed", "Ready for beta release"],
    },
    "parent_link_types": ["Implements", "Relates"],
    "create_rules": {
        "require_components": True,
        "risk_class": None,
        "components_requiring_assignee": [],
    },
    "readiness_fields": {},
}


def _merge(base, override):
    out = copy.deepcopy(base)
    for key, value in (override or {}).items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = _merge(out[key], value)
        else:
            out[key] = value
    return out


def load(path=None):
    """DEFAULTS merged with the JSON file (env JIRA_CONFIG > argument > default).

    A missing file is fine (defaults apply); a file that is not valid JSON is
    not - a silently ignored typo would make every engine run with the wrong
    project key.
    """
    candidate = os.environ.get("JIRA_CONFIG") or path or DEFAULT_PATH
    p = Path(candidate)
    if not p.is_file():
        return copy.deepcopy(DEFAULTS)
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"jira config {p} is not valid JSON: {exc}") from None
    return _merge(DEFAULTS, data)


def lower_set(values):
    return frozenset(v.lower() for v in values)


CONFIG = load()
