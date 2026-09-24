import sys
from pathlib import Path

# scripts/ is not a package; make its modules importable in tests.
SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
