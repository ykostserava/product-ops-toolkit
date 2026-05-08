#!/usr/bin/env python3
"""Build a coverage matrix joining backend endpoints with mobile/web call sites.

Usage:
    build_coverage_matrix.py endpoints.json [--ios ios.json] [--android android.json] [--web web.json] [--out matrix.md]

Exit codes: 0 success, 1 failure, 10 validation failure.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


def load(p: str | None) -> list[dict]:
    if not p:
        return []
    path = Path(p)
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))


def normalise(path: str) -> str:
    """Normalise paths for comparison: strip host, collapse param placeholders."""
    if not path:
        return ""
    # strip host
    path = re.sub(r"^https?://[^/]+", "", path)
    # normalise param placeholders: {id} <-> :id
    path = re.sub(r":(\w+)", r"{\1}", path)
    # collapse query strings
    path = path.split("?")[0]
    return path.rstrip("/").lower()


def match(endpoint_path: str, endpoint_method: str, calls: list[dict]) -> list[dict]:
    """Return calls that match this endpoint by method and normalised path."""
    ep_norm = normalise(endpoint_path)
    matched = []
    for c in calls:
        if c.get("method") and c["method"] != "?" and endpoint_method != "?":
            if c["method"].upper() != endpoint_method.upper():
                continue
        c_norm = normalise(c.get("path", ""))
        if not c_norm:
            continue
        if ep_norm == c_norm or ep_norm.endswith(c_norm) or c_norm.endswith(ep_norm):
            matched.append(c)
    return matched


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("endpoints", help="endpoints JSON")
    ap.add_argument("--ios", default=None)
    ap.add_argument("--android", default=None)
    ap.add_argument("--web", default=None)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    endpoints = load(args.endpoints)
    if not endpoints:
        print("no endpoints loaded", file=sys.stderr)
        return 10

    ios = load(args.ios)
    android = load(args.android)
    web = load(args.web)

    rows = []
    drift_ios = list(ios)
    drift_android = list(android)
    drift_web = list(web)

    for e in endpoints:
        m_ios = match(e["path"], e.get("method", "?"), ios)
        m_android = match(e["path"], e.get("method", "?"), android)
        m_web = match(e["path"], e.get("method", "?"), web)

        for c in m_ios:
            if c in drift_ios:
                drift_ios.remove(c)
        for c in m_android:
            if c in drift_android:
                drift_android.remove(c)
        for c in m_web:
            if c in drift_web:
                drift_web.remove(c)

        rows.append({
            "endpoint": f"{e.get('method', '?')} {e['path']}",
            "backend": "OK",
            "ios": "OK" if m_ios else ("--" if not ios else "MISSING"),
            "android": "OK" if m_android else ("--" if not android else "MISSING"),
            "web": "OK" if m_web else ("--" if not web else "MISSING"),
            "deprecated": e.get("deprecated", False),
            "feature_tag": e.get("feature_tag", ""),
        })

    out_lines = []
    out_lines.append("# Coverage Matrix\n")
    out_lines.append(f"Endpoints: {len(endpoints)} | iOS calls: {len(ios)} | Android calls: {len(android)} | Web calls: {len(web)}\n")
    out_lines.append("")
    out_lines.append("| Endpoint | Backend | iOS | Android | Web | Notes |")
    out_lines.append("|---|:-:|:-:|:-:|:-:|---|")
    for r in rows:
        notes = []
        if r["deprecated"]:
            notes.append("DEPRECATED")
        if r["feature_tag"]:
            notes.append(f"tag:{r['feature_tag']}")
        out_lines.append(f"| `{r['endpoint']}` | {r['backend']} | {r['ios']} | {r['android']} | {r['web']} | {'; '.join(notes)} |")

    out_lines.append("")
    out_lines.append("## Drift (calls not matching any backend endpoint)")
    out_lines.append("")
    if drift_ios:
        out_lines.append(f"### iOS ({len(drift_ios)})")
        for c in drift_ios:
            out_lines.append(f"- `{c.get('method', '?')} {c.get('path', '')}` at {c.get('file')}:{c.get('line')}")
    if drift_android:
        out_lines.append(f"### Android ({len(drift_android)})")
        for c in drift_android:
            out_lines.append(f"- `{c.get('method', '?')} {c.get('path', '')}` at {c.get('file')}:{c.get('line')}")
    if drift_web:
        out_lines.append(f"### Web ({len(drift_web)})")
        for c in drift_web:
            out_lines.append(f"- `{c.get('method', '?')} {c.get('path', '')}` at {c.get('file')}:{c.get('line')}")
    if not (drift_ios or drift_android or drift_web):
        out_lines.append("(none)")

    output = "\n".join(out_lines)
    if args.out:
        Path(args.out).write_text(output, encoding="utf-8")
        print(f"wrote {args.out}")
    else:
        print(output)

    return 0


if __name__ == "__main__":
    sys.exit(main())
