#!/usr/bin/env python3
"""Extract HTTP endpoints from a backend project.

Supports OpenAPI specs, Symfony/Laravel, Spring, NestJS/Express, FastAPI, Rails routes.
Best-effort regex parsing - does not replace real route enumeration but gets ~80% there.

Usage:
    extract_endpoints.py <path> [--feature NAME] [--json]

Exit codes: 0 success, 1 failure, 10 no endpoints found.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path

try:
    import yaml  # optional
except ImportError:
    yaml = None


@dataclass
class Endpoint:
    method: str
    path: str
    handler: str = ""
    auth: str = ""
    deprecated: bool = False
    feature_tag: str = ""
    source: str = ""  # file:line


PHP_ATTR = re.compile(
    r'#\[Route\(\s*[\'"](?P<path>[^\'"]+)[\'"](?:[^)]*?methods\s*[:=]\s*\[(?P<methods>[^\]]+)\])?[^)]*\)\]\s*[\r\n]+\s*public function\s+(?P<handler>\w+)',
    re.DOTALL,
)
SPRING_MAP = re.compile(
    r'@(Get|Post|Put|Delete|Patch|Request)Mapping\(\s*(?:value\s*=\s*)?[\'"](?P<path>[^\'"]+)[\'"]',
    re.IGNORECASE,
)
NEST_DEC = re.compile(
    r'@(Get|Post|Put|Delete|Patch)\(\s*[\'"]?(?P<path>[^\'")]*)[\'"]?\s*\)\s*[\r\n]+\s*\w+\s+(?P<handler>\w+)\(',
)
EXPRESS = re.compile(
    r'(?:app|router)\.(?P<method>get|post|put|delete|patch)\(\s*[\'"`](?P<path>[^\'"`]+)[\'"`]',
)
FASTAPI = re.compile(
    r'@(?:app|router)\.(?P<method>get|post|put|delete|patch)\(\s*[\'"](?P<path>[^\'"]+)[\'"]',
)
LARAVEL = re.compile(
    r'Route::(?P<method>get|post|put|delete|patch|any)\(\s*[\'"](?P<path>[^\'"]+)[\'"]',
)
RAILS = re.compile(
    r'^\s*(?P<method>get|post|put|delete|patch)\s+[\'"](?P<path>[^\'"]+)[\'"]',
    re.MULTILINE,
)


def line_of(text: str, pos: int) -> int:
    return text.count("\n", 0, pos) + 1


def parse_openapi(p: Path) -> list[Endpoint]:
    eps: list[Endpoint] = []
    if yaml is None and p.suffix in {".yml", ".yaml"}:
        return eps
    try:
        data = yaml.safe_load(p.read_text(encoding="utf-8")) if yaml and p.suffix in {".yml", ".yaml"} else json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return eps
    paths = (data or {}).get("paths") or {}
    for path, ops in paths.items():
        if not isinstance(ops, dict):
            continue
        for method, op in ops.items():
            if method.lower() not in {"get", "post", "put", "delete", "patch"}:
                continue
            eps.append(Endpoint(
                method=method.upper(),
                path=path,
                handler=op.get("operationId", "") if isinstance(op, dict) else "",
                deprecated=bool(op.get("deprecated")) if isinstance(op, dict) else False,
                feature_tag=",".join(op.get("tags", [])) if isinstance(op, dict) else "",
                source=str(p),
            ))
    return eps


def scan_text_files(root: Path, suffixes: set[str]) -> list[tuple[Path, str]]:
    out: list[tuple[Path, str]] = []
    skip = {".git", "node_modules", "vendor", "venv", ".venv", "build", "dist", "target", "__pycache__"}
    for p in root.rglob("*"):
        if not p.is_file():
            continue
        if any(part in skip for part in p.parts):
            continue
        if p.suffix.lower() not in suffixes:
            continue
        try:
            out.append((p, p.read_text(encoding="utf-8", errors="ignore")))
        except OSError:
            continue
    return out


def extract(root: Path) -> list[Endpoint]:
    eps: list[Endpoint] = []

    # 1. OpenAPI specs
    for name in ["openapi.yaml", "openapi.yml", "openapi.json", "swagger.yaml", "swagger.yml", "swagger.json"]:
        for p in root.rglob(name):
            eps.extend(parse_openapi(p))
    if eps:
        return eps

    # 2. Framework regexes
    php_files = scan_text_files(root, {".php"})
    for p, text in php_files:
        for m in PHP_ATTR.finditer(text):
            methods = m.group("methods") or "GET"
            for verb in re.findall(r"[A-Z]+", methods.upper()):
                eps.append(Endpoint(method=verb, path=m.group("path"), handler=m.group("handler"), source=f"{p}:{line_of(text, m.start())}"))
        for m in LARAVEL.finditer(text):
            eps.append(Endpoint(method=m.group("method").upper(), path=m.group("path"), source=f"{p}:{line_of(text, m.start())}"))

    java_kt = scan_text_files(root, {".java", ".kt"})
    for p, text in java_kt:
        for m in SPRING_MAP.finditer(text):
            verb = m.group(1).upper().replace("REQUEST", "GET")
            eps.append(Endpoint(method=verb, path=m.group("path"), source=f"{p}:{line_of(text, m.start())}"))

    js_ts = scan_text_files(root, {".js", ".ts"})
    for p, text in js_ts:
        for m in NEST_DEC.finditer(text):
            eps.append(Endpoint(method=m.group(1).upper(), path=m.group("path") or "/", handler=m.group("handler"), source=f"{p}:{line_of(text, m.start())}"))
        for m in EXPRESS.finditer(text):
            eps.append(Endpoint(method=m.group("method").upper(), path=m.group("path"), source=f"{p}:{line_of(text, m.start())}"))

    py = scan_text_files(root, {".py"})
    for p, text in py:
        for m in FASTAPI.finditer(text):
            eps.append(Endpoint(method=m.group("method").upper(), path=m.group("path"), source=f"{p}:{line_of(text, m.start())}"))

    rb = scan_text_files(root, {".rb"})
    for p, text in rb:
        for m in RAILS.finditer(text):
            eps.append(Endpoint(method=m.group("method").upper(), path=m.group("path"), source=f"{p}:{line_of(text, m.start())}"))

    return eps


def filter_by_feature(eps: list[Endpoint], feature: str) -> list[Endpoint]:
    f = feature.lower()
    return [e for e in eps if f in e.path.lower() or f in e.handler.lower() or f in e.source.lower() or f in (e.feature_tag or "").lower()]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("path")
    ap.add_argument("--feature", default="", help="filter to feature substring")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    root = Path(args.path)
    if not root.exists():
        print(f"path not found: {root}", file=sys.stderr)
        return 1

    eps = extract(root)
    if args.feature:
        eps = filter_by_feature(eps, args.feature)

    if not eps:
        print("no endpoints found", file=sys.stderr)
        if args.json:
            print("[]")
        return 10

    if args.json:
        print(json.dumps([asdict(e) for e in eps], indent=2))
    else:
        print(f"{'METHOD':7} {'PATH':50} HANDLER  SOURCE")
        for e in eps:
            print(f"{e.method:7} {e.path:50} {e.handler[:20]:20} {e.source}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
