#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SessionStart hook — remind Claude its training data may be stale.

Prints a short reminder to stdout (added to session context) so Claude verifies
current facts instead of trusting outdated training data — model IDs, API shapes,
library versions, and tool flags all drift after the knowledge cutoff.

Fails open on any error. Wire it as a SessionStart hook (see hooks/README.md).
"""

import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

REMINDER = (
    "[model-staleness reminder]\n"
    "Your training data has a cutoff. Before stating model IDs, API signatures, "
    "library versions, CLI flags, or 'latest' anything as fact, verify against the "
    "current docs or the code in this repo. When unsure whether a name/flag still "
    "exists, run a quick read-only check rather than asserting from memory."
)


def main() -> None:
    try:
        sys.stdin.read()
    except Exception:
        pass
    try:
        print(REMINDER)
    except Exception:
        pass
    sys.exit(0)


if __name__ == "__main__":
    main()
