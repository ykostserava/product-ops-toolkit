"""Mechanics that hold the toolkit's own rules (rules/examples/mechanics-over-promises.md).

A rule in prose is a promise; these tests are what makes a few of them hold.
"""

from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
RULES_DIR = REPO / "rules" / "examples"
AGENTS_DIR = REPO / "agents"
HOOKS_DIR = REPO / "hooks"
SKILLS_DIR = REPO / "skills"

# The always-loaded budget for a project that copies every example rule in:
# past this, the rules stop being read.
ALWAYS_LOADED_BUDGET = 40 * 1024

AUDITORS = {"auditor-money", "auditor-failures", "auditor-definitions"}
READONLY_TOOLS = {"Read", "Grep", "Glob"}


def frontmatter(path: Path) -> dict:
    parts = path.read_text(encoding="utf-8").split("---")
    assert len(parts) >= 3, f"{path}: no frontmatter block"
    fields = {}
    for line in parts[1].strip().splitlines():
        key, sep, value = line.partition(":")
        if sep:
            fields[key.strip()] = value.strip()
    return fields


def test_example_rules_fit_the_always_loaded_budget():
    total = sum(p.stat().st_size for p in RULES_DIR.glob("*.md"))
    assert total <= ALWAYS_LOADED_BUDGET, (
        f"rules/examples = {total} bytes > {ALWAYS_LOADED_BUDGET}; a rule that "
        "needs this much text is a skill or a hook in disguise"
    )


def test_auditor_panel_agents_exist():
    found = {p.stem for p in AGENTS_DIR.glob("auditor-*.md")}
    missing = AUDITORS - found
    assert not missing, f"blind-auditor panel incomplete, missing: {sorted(missing)}"


def test_auditor_agents_are_read_only():
    for name in sorted(AUDITORS):
        fields = frontmatter(AGENTS_DIR / f"{name}.md")
        tools = {t.strip() for t in fields.get("tools", "").split(",") if t.strip()}
        extra = tools - READONLY_TOOLS
        assert tools and not extra, (
            f"{name}: write-capable tools {sorted(extra)} - an auditor that can "
            "edit or run stops being an auditor"
        )


def test_auditor_models_are_distinct():
    models = [
        frontmatter(AGENTS_DIR / f"{n}.md").get("model") for n in sorted(AUDITORS)
    ]
    assert all(models), f"every auditor must pin a model, got: {models}"
    assert len(set(models)) == len(models), (
        f"same model twice is an echo, not a panel: {models}"
    )


def test_audit_skill_launches_every_auditor():
    text = (SKILLS_DIR / "audit" / "SKILL.md").read_text(encoding="utf-8")
    for name in sorted(AUDITORS):
        assert name in text, f"/audit does not launch {name}"


def test_every_hook_has_a_readme_row():
    readme = (HOOKS_DIR / "README.md").read_text(encoding="utf-8")
    for hook in sorted(HOOKS_DIR.glob("*.py")):
        if hook.name == "pre_mr_marker.py":
            continue  # a module the guard imports, not a hook of its own
        assert f"`{hook.name}`" in readme, (
            f"{hook.name} has no row in hooks/README.md - an unwired hook "
            "guarantees nothing"
        )


def test_every_skill_has_a_name_and_a_description():
    for skill in sorted(SKILLS_DIR.glob("*/SKILL.md")):
        fields = frontmatter(skill)
        assert fields.get("name") == skill.parent.name, (
            f"{skill.parent.name}: frontmatter name {fields.get('name')!r} "
            "does not match the directory"
        )
        assert len(fields.get("description", "")) > 40, (
            f"{skill.parent.name}: description missing or too short to trigger on"
        )
