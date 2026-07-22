#!/usr/bin/env python3
"""Proxy-Switch: One-click proxy configuration for Ubuntu servers.

Launch the GUI application.

Usage:
    python app.py              — GUI mode
    python app.py on <profile> — CLI mode
    python app.py status       — CLI mode
"""

from __future__ import annotations

import os
import sys

# Ensure project root is on sys.path
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)


def main() -> None:
    """Launch Proxy-Switch in GUI or CLI mode."""
    try:
        import customtkinter  # noqa: F401
    except ImportError:
        print("Error: customtkinter is not installed.")
        print("Install dependencies: pip install -r requirements.txt")
        sys.exit(1)

    try:
        import paramiko  # noqa: F401
    except ImportError:
        print("Error: paramiko is not installed.")
        print("Install dependencies: pip install -r requirements.txt")
        sys.exit(1)

    # CLI mode if command-line args are given
    if len(sys.argv) > 1 and sys.argv[1] in ("on", "off", "status", "list", "init", "--help"):
        from proxy_switch.__main__ import main as cli_main
        cli_main()
        return

    # GUI mode
    from proxy_switch.gui.window import MainWindow
    app = MainWindow()
    app.mainloop()


if __name__ == "__main__":
    main()
