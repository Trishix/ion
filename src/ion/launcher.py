from __future__ import annotations

import os
import sys
from pathlib import Path

from ion.config import load_config
from ion.tui.app import IonApp


def main() -> int:
    if not (sys.stdin.isatty() and sys.stdout.isatty()):
        print("Ion needs an interactive terminal. Run make run in a terminal window.", file=sys.stderr)
        return 2
    config_path = Path(os.environ.get("ION_CONFIG", Path(__file__).resolve().parents[2] / "ion.toml"))
    config = load_config(config_path)
    IonApp(config=config, repo_hint=os.environ.get("ION_REPO", "")).run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
