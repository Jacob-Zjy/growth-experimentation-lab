"""Run the full project without requiring an editable installation first."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from growth_lab.pipeline import main  # noqa: E402

if __name__ == "__main__":
    main()
