from __future__ import annotations

import os
import sys
from typing import Optional

from .cli import main as cli_main
from .settings import ensure_api_key_from_settings


def main(argv: Optional[list[str]] = None) -> None:
    argv = list(sys.argv[1:] if argv is None else argv)
    # If any explicit subcommands/args are passed, route to CLI for power users.
    if argv:
        cli_main(argv)
        return
    # Zero-args path: run setup wizard if needed, else launch TUI.
    if not ensure_api_key_from_settings():
        from .wizard import run_setup_wizard
        run_setup_wizard()
    # After setup, try to launch TUI.
    try:
        from .tui import run_tui
        run_tui()
    except Exception as e:
        # Fallback: minimal console wizard
        from .wizard import run_world_wizard
        print("Textual TUI unavailable; running console wizard.")
        run_world_wizard()


if __name__ == "__main__":
    main()

