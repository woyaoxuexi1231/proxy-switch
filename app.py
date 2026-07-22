#!/usr/bin/env python3
"""Proxy-Switch: One-click proxy configuration for Ubuntu servers.

Launch the GUI application.
"""

import sys
import os

# Ensure the project root is on sys.path
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)


def main():
    """Launch the Proxy-Switch GUI."""
    try:
        import customtkinter
    except ImportError:
        print("Error: customtkinter is not installed.")
        print("Install dependencies: pip install -r requirements.txt")
        sys.exit(1)

    try:
        import paramiko
    except ImportError:
        print("Error: paramiko is not installed.")
        print("Install dependencies: pip install -r requirements.txt")
        sys.exit(1)

    # Handle command-line args for CLI mode
    if len(sys.argv) > 1 and sys.argv[1] in ("on", "off", "status", "list", "init", "--help"):
        # CLI mode - delegate to __main__
        from proxy_switch.__main__ import main as cli_main
        cli_main()
        return

    # GUI mode
    from proxy_switch.gui.main_window import MainWindow
    app = MainWindow()
    app.mainloop()


if __name__ == "__main__":
    main()
