"""Start the agent — run with: python run.py"""

import sys
from pathlib import Path

# Ensure the parent directory is in sys.path so that the 'agent' package
# can be imported when running from inside the agent/ folder.
_parent = str(Path(__file__).resolve().parent.parent)
if _parent not in sys.path:
    sys.path.insert(0, _parent)

from agent.__main__ import main  # noqa: E402

if __name__ == "__main__":
    main()
