#!/usr/bin/env python3
"""Detect backend framework, mobile platforms, and web stack in a repo path.

Exit codes: 0 success, 1 failure, 10 validation failure.
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path


@dataclass
class Result:
    ok: bool
    path: str
    backend: list[str] = field(default_factory=list)
    mobile_ios: bool = False
    mobile_android: bool = False
    web: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


BACKEND_MARKERS = {
    "symfony": ["composer.json", "config/routes.yaml", "src/Controller"],
    "laravel": ["composer.json", "routes/web.php", "routes/api.php"],
    "spring": ["pom.xml", "build.gradle", "build.gradle.kts"],
    "nestjs": ["package.json", "nest-cli.json"],
    "express": ["package.json"],
    "fastapi": ["pyproject.toml", "requirements.txt"],
    "rails": ["Gemfile", "config/routes.rb"],
    "django": ["manage.py"],
}

WEB_MARKERS = {
    "react": ["package.json"],
    "vue": ["package.json"],
    "angular": ["angular.json"],
    "svelte": ["svelte.config.js"],
}


def file_contains(path: Path, needle: str) -> bool:
    try:
        return needle in path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return False


def detect(root: Path) -> Result:
    if not root.exists():
        return Result(ok=False, path=str(root), notes=[f"path does not exist: {root}"])

    res = Result(ok=True, path=str(root))

    # Backend
    if (root / "composer.json").exists():
        cj = root / "composer.json"
        if file_contains(cj, "symfony/"):
            res.backend.append("symfony")
        if file_contains(cj, "laravel/"):
            res.backend.append("laravel")
    if (root / "pom.xml").exists() or any(root.glob("**/build.gradle*")):
        res.backend.append("spring")
    if (root / "package.json").exists():
        pj = root / "package.json"
        if file_contains(pj, "@nestjs/"):
            res.backend.append("nestjs")
        elif file_contains(pj, '"express"'):
            res.backend.append("express")
    if (root / "pyproject.toml").exists() or (root / "requirements.txt").exists():
        for f in ["pyproject.toml", "requirements.txt"]:
            p = root / f
            if p.exists() and file_contains(p, "fastapi"):
                res.backend.append("fastapi")
            if p.exists() and file_contains(p, "django"):
                res.backend.append("django")
    if (root / "Gemfile").exists() and file_contains(root / "Gemfile", "rails"):
        res.backend.append("rails")

    # Mobile
    if any(root.glob("**/*.xcodeproj")) or (root / "Package.swift").exists() or (root / "Podfile").exists():
        res.mobile_ios = True
    if (root / "AndroidManifest.xml").exists() or any(root.glob("**/AndroidManifest.xml")) or any(root.glob("**/build.gradle*")):
        if any(root.glob("**/*.kt")) or any(root.glob("**/*.java")):
            res.mobile_android = True

    # Web
    if (root / "package.json").exists():
        pj = root / "package.json"
        if file_contains(pj, '"react"'):
            res.web.append("react")
        if file_contains(pj, '"vue"'):
            res.web.append("vue")
        if (root / "angular.json").exists():
            res.web.append("angular")
        if (root / "svelte.config.js").exists():
            res.web.append("svelte")

    if not res.backend and not res.mobile_ios and not res.mobile_android and not res.web:
        res.notes.append("no recognised stack markers found - manual scoping required")

    return res


def main() -> int:
    p = argparse.ArgumentParser(description="Detect repo stack")
    p.add_argument("path", help="repository root path")
    p.add_argument("--json", action="store_true", help="emit JSON instead of text")
    args = p.parse_args()

    res = detect(Path(args.path))

    if args.json:
        print(json.dumps(asdict(res), indent=2))
    else:
        print(f"Path: {res.path}")
        print(f"Backend: {', '.join(res.backend) or '-'}")
        print(f"iOS: {'yes' if res.mobile_ios else 'no'}")
        print(f"Android: {'yes' if res.mobile_android else 'no'}")
        print(f"Web: {', '.join(res.web) or '-'}")
        for n in res.notes:
            print(f"Note: {n}")

    if not res.ok:
        return 10
    return 0


if __name__ == "__main__":
    sys.exit(main())
