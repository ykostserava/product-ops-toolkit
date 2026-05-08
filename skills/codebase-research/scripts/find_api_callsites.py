#!/usr/bin/env python3
"""Find HTTP API call sites in mobile (iOS/Android) or web sources.

Usage:
    find_api_callsites.py <path> --platform {ios,android,web} [--json]

Exit codes: 0 success, 1 failure, 10 no calls found.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass
class CallSite:
    platform: str
    method: str  # GET/POST/... or "?"
    path: str
    file: str
    line: int


SKIP_DIRS = {".git", "node_modules", "vendor", "venv", ".venv", "build", "dist", "target", "__pycache__", "Pods", ".gradle"}


def walk(root: Path, suffixes: set[str]):
    for p in root.rglob("*"):
        if not p.is_file():
            continue
        if any(part in SKIP_DIRS for part in p.parts):
            continue
        if p.suffix.lower() in suffixes:
            yield p


def line_at(text: str, pos: int) -> int:
    return text.count("\n", 0, pos) + 1


# iOS patterns
IOS_URL_LITERAL = re.compile(r'(?:URL\(string:\s*|URLRequest\(url:\s*URL\(string:\s*)?[\'"](?P<url>https?://[^\'"\s]+|/v\d+/[^\'"\s]+|/api/[^\'"\s]+)[\'"]')
IOS_ALAMOFIRE = re.compile(r'(?:AF|session)\.request\(\s*[\'"](?P<url>[^\'"]+)[\'"](?:[^)]*method:\s*\.(?P<method>\w+))?')

# Android patterns
ANDROID_RETROFIT = re.compile(r'@(?P<method>GET|POST|PUT|DELETE|PATCH)\(\s*[\'"](?P<path>[^\'"]+)[\'"]')
ANDROID_OKHTTP = re.compile(r'\.url\(\s*[\'"](?P<url>https?://[^\'"\s]+|/v\d+/[^\'"\s]+)[\'"]\s*\)')

# Web patterns
WEB_AXIOS = re.compile(r'axios\.(?P<method>get|post|put|delete|patch)\s*\(\s*[`\'"](?P<url>[^`\'"]+)[`\'"]')
WEB_FETCH = re.compile(r'fetch\s*\(\s*[`\'"](?P<url>[^`\'"]+)[`\'"](?:[^)]*method:\s*[`\'"](?P<method>\w+)[`\'"])?')


def scan_ios(root: Path) -> list[CallSite]:
    out: list[CallSite] = []
    for p in walk(root, {".swift", ".m", ".mm"}):
        try:
            text = p.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for m in IOS_ALAMOFIRE.finditer(text):
            out.append(CallSite("ios", (m.group("method") or "?").upper(), m.group("url"), str(p), line_at(text, m.start())))
        for m in IOS_URL_LITERAL.finditer(text):
            url = m.group("url")
            if any(c.path == url and c.file == str(p) for c in out):
                continue
            out.append(CallSite("ios", "?", url, str(p), line_at(text, m.start())))
    return out


def scan_android(root: Path) -> list[CallSite]:
    out: list[CallSite] = []
    for p in walk(root, {".kt", ".java"}):
        try:
            text = p.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for m in ANDROID_RETROFIT.finditer(text):
            out.append(CallSite("android", m.group("method"), m.group("path"), str(p), line_at(text, m.start())))
        for m in ANDROID_OKHTTP.finditer(text):
            out.append(CallSite("android", "?", m.group("url"), str(p), line_at(text, m.start())))
    return out


def scan_web(root: Path) -> list[CallSite]:
    out: list[CallSite] = []
    for p in walk(root, {".js", ".ts", ".jsx", ".tsx", ".vue", ".svelte"}):
        try:
            text = p.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for m in WEB_AXIOS.finditer(text):
            out.append(CallSite("web", m.group("method").upper(), m.group("url"), str(p), line_at(text, m.start())))
        for m in WEB_FETCH.finditer(text):
            out.append(CallSite("web", (m.group("method") or "GET").upper(), m.group("url"), str(p), line_at(text, m.start())))
    return out


SCANNERS = {"ios": scan_ios, "android": scan_android, "web": scan_web}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("path")
    ap.add_argument("--platform", required=True, choices=list(SCANNERS))
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    root = Path(args.path)
    if not root.exists():
        print(f"path not found: {root}", file=sys.stderr)
        return 1

    calls = SCANNERS[args.platform](root)

    if not calls:
        print(f"no {args.platform} call sites found", file=sys.stderr)
        if args.json:
            print("[]")
        return 10

    if args.json:
        print(json.dumps([asdict(c) for c in calls], indent=2))
    else:
        print(f"{'METHOD':7} {'URL/PATH':60} FILE:LINE")
        for c in calls:
            print(f"{c.method:7} {c.path[:60]:60} {c.file}:{c.line}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
