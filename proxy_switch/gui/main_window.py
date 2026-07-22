"""Proxy-Switch main window.

The primary GUI window for managing proxy configurations on remote servers.
"""

import os
import sys
import threading
from datetime import datetime
from typing import Dict, List, Optional

import customtkinter as ctk

from .. import __version__
from ..core.models import Server, Profile, ProxyConfig
from ..core import app_config
from ..backends import get_all_backends, get_backends
from ..ssh.executor import Executor
from ..ssh.connection import close_connection, close_all_connections

from .theme import Colors, setup_theme, font_heading, font_body, font_small, font_mono
from .server_dialog import ServerDialog
from .profile_dialog import ProfileDialog


class MainWindow(ctk.CTk):
    """Main application window."""

    def __init__(self):
        super().__init__()

        setup_theme()

        self.title(f"Proxy-Switch v{__version__}")
        self.geometry("750x680")
        self.minsize(650, 580)

        # State
        self.servers: Dict[str, Server] = {}
        self.profiles: Dict[str, Profile] = {}
        self.current_server: Optional[Server] = None
        self.current_profile: Optional[Profile] = None
        self.executor: Optional[Executor] = None
        self._is_applying = False

        # Icon
        icon_path = os.path.join(os.path.dirname(__file__), "..", "..", "assets", "icon.ico")
        if os.path.exists(icon_path):
            try:
                self.iconbitmap(icon_path)
            except Exception:
                pass

        self._build_menubar()
        self._build_ui()

        # Load config
        self._refresh_config()

        # Set protocol for clean shutdown
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # ── UI Construction ─────────────────────────────────────────────────

    def _build_menubar(self):
        """Build the macOS/Windows menu bar."""
        self.menu_bar = ctk.CTkFrame(self, height=30, corner_radius=0)
        self.menu_bar.pack(fill="x")
        self.menu_bar.pack_propagate(False)

        # File menu simulation with buttons
        file_btn = ctk.CTkButton(self.menu_bar, text="File", width=50,
                                 height=25, fg_color="transparent",
                                 text_color=Colors.TEXT_PRIMARY,
                                 hover_color="#E0E0E0",
                                 command=self._file_menu)
        file_btn.pack(side="left", padx=2)

        settings_btn = ctk.CTkButton(self.menu_bar, text="Settings", width=70,
                                      height=25, fg_color="transparent",
                                      text_color=Colors.TEXT_PRIMARY,
                                      hover_color="#E0E0E0",
                                      command=self._open_settings)
        settings_btn.pack(side="left", padx=2)

        help_btn = ctk.CTkButton(self.menu_bar, text="Help", width=50,
                                  height=25, fg_color="transparent",
                                  text_color=Colors.TEXT_PRIMARY,
                                  hover_color="#E0E0E0",
                                  command=self._show_about)
        help_btn.pack(side="left", padx=2)

    def _build_ui(self):
        """Build the main interface."""
        # Main container
        main = ctk.CTkFrame(self)
        main.pack(fill="both", expand=True, padx=15, pady=(10, 15))
        main.grid_columnconfigure(0, weight=1)
        main.grid_rowconfigure(3, weight=1)

        # ── Connection Area ──────────────────────────────────────────
        conn_frame = ctk.CTkFrame(main, fg_color="transparent")
        conn_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        conn_frame.grid_columnconfigure((0, 1, 2), weight=1)

        # Server selector
        ctk.CTkLabel(conn_frame, text="Server:", anchor="w",
                      font=font_body()).grid(row=0, column=0, padx=(0, 5), pady=2, sticky="w")
        self.server_var = ctk.StringVar(value="(no servers)")
        self.server_menu = ctk.CTkOptionMenu(
            conn_frame, variable=self.server_var,
            values=["(no servers)"],
            command=self._on_server_change,
            width=180)
        self.server_menu.grid(row=1, column=0, padx=(0, 10), sticky="ew")

        # Profile selector
        ctk.CTkLabel(conn_frame, text="Profile:", anchor="w",
                      font=font_body()).grid(row=0, column=1, padx=(0, 5), pady=2, sticky="w")
        self.profile_var = ctk.StringVar(value="(no profiles)")
        self.profile_menu = ctk.CTkOptionMenu(
            conn_frame, variable=self.profile_var,
            values=["(no profiles)"],
            command=self._on_profile_change,
            width=180)
        self.profile_menu.grid(row=1, column=1, padx=(0, 10), sticky="ew")

        # Connection button
        self.connect_btn = ctk.CTkButton(
            conn_frame, text="Connect", width=80,
            command=self._toggle_connection)
        self.connect_btn.grid(row=1, column=2, padx=(0, 0), sticky="e")

        # ── Tools Selection ──────────────────────────────────────────
        tools_frame = ctk.CTkFrame(main)
        tools_frame.grid(row=1, column=0, sticky="ew", pady=(0, 10))
        tools_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(tools_frame, text="Apply to:", anchor="w",
                      font=font_heading()).pack(anchor="w", padx=15, pady=(10, 5))

        self.tool_vars: Dict[str, ctk.BooleanVar] = {}
        tool_grid = ctk.CTkFrame(tools_frame, fg_color="transparent")
        tool_grid.pack(fill="x", padx=15, pady=(0, 10))

        all_tools = [
            ("system_env", "System Environment", True),
            ("apt", "APT", True),
            ("git", "Git", True),
            ("docker", "Docker", True),
            ("maven", "Maven", True),
            ("gradle", "Gradle", False),
            ("npm", "npm", True),
            ("pip", "pip", True),
            ("curl", "curl", True),
            ("wget", "wget", True),
            ("snap", "Snap", False),
        ]

        for i, (key, label, default) in enumerate(all_tools):
            var = ctk.BooleanVar(value=default)
            self.tool_vars[key] = var
            cb = ctk.CTkCheckBox(tool_grid, text=label, variable=var,
                                  font=font_body())
            cb.grid(row=i // 4, column=i % 4, padx=(0, 15), pady=3, sticky="w")

        # ── Action Buttons ───────────────────────────────────────────
        actions = ctk.CTkFrame(main, fg_color="transparent")
        actions.grid(row=2, column=0, sticky="ew", pady=(0, 10))

        self.apply_btn = ctk.CTkButton(
            actions, text="⚡  Apply Proxy",
            command=self._apply_proxy,
            fg_color=Colors.SUCCESS,
            hover_color="#1B5E20",
            height=35, width=130,
            font=ctk.CTkFont(size=13, weight="bold"))
        self.apply_btn.pack(side="left", padx=(0, 8))

        self.disable_btn = ctk.CTkButton(
            actions, text="✕  Disable Proxy",
            command=self._disable_proxy,
            fg_color=Colors.DANGER,
            hover_color="#B71C1C",
            height=35, width=130,
            font=ctk.CTkFont(size=13))
        self.disable_btn.pack(side="left", padx=(0, 8))

        self.refresh_btn = ctk.CTkButton(
            actions, text="⟳  Refresh Status",
            command=self._refresh_status,
            fg_color=Colors.PRIMARY,
            height=35, width=130,
            font=ctk.CTkFont(size=13))
        self.refresh_btn.pack(side="left", padx=(0, 8))

        # ── Status / Log Area ────────────────────────────────────────
        log_frame = ctk.CTkFrame(main)
        log_frame.grid(row=3, column=0, sticky="nsew")
        log_frame.grid_rowconfigure(1, weight=1)
        log_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(log_frame, text="Status / Log", anchor="w",
                      font=font_heading()).grid(
            row=0, column=0, sticky="w", padx=15, pady=(10, 5))

        self.log_text = ctk.CTkTextbox(
            log_frame, font=font_mono(),
            wrap="word", state="disabled")
        self.log_text.grid(row=1, column=0, sticky="nsew", padx=15, pady=(0, 10))

        # ── Status Bar ───────────────────────────────────────────────
        self.status_bar = ctk.CTkLabel(
            self, text="Ready",
            anchor="w", font=font_small(),
            fg_color=Colors.CARD_BORDER)
        self.status_bar.pack(fill="x", padx=0, pady=0)

    # ── Configuration Loading ───────────────────────────────────────────

    def _refresh_config(self):
        """Reload profiles and servers from config files."""
        self.profiles = app_config.load_config()
        self.servers = app_config.load_servers()

        # Update server dropdown
        if self.servers:
            names = list(self.servers.keys())
            self.server_menu.configure(values=names)
            current = self.server_var.get()
            if current not in names:
                self.server_var.set(names[0])
                self._on_server_change(names[0])
        else:
            self.server_menu.configure(values=["(no servers)"])
            self.server_var.set("(no servers)")

        # Update profile dropdown
        if self.profiles:
            names = list(self.profiles.keys())
            self.profile_menu.configure(values=names)
            current = self.profile_var.get()
            if current not in names:
                # Default to first non-"direct" profile
                preferred = [n for n in names if n != "direct"]
                if preferred:
                    self.profile_var.set(preferred[0])
                    self._on_profile_change(preferred[0])
                else:
                    self.profile_var.set(names[0])
                    self._on_profile_change(names[0])
        else:
            self.profile_menu.configure(values=["(no profiles)"])
            self.profile_var.set("(no profiles)")

    # ── Event Handlers ──────────────────────────────────────────────────

    def _on_server_change(self, name: str):
        """Handle server selection change."""
        if name in self.servers:
            self.current_server = self.servers[name]
            self._log(f"Selected server: {name} ({self.current_server.host})")
        else:
            self.current_server = None
        self._update_status_bar()

    def _on_profile_change(self, name: str):
        """Handle profile selection change."""
        if name in self.profiles:
            self.current_profile = self.profiles[name]
            config = self.current_profile.config
            if config.is_enabled:
                self._log(f"Selected profile: {name} → {config.primary_proxy}")
            else:
                self._log(f"Selected profile: {name} (direct / no proxy)")
        else:
            self.current_profile = None
        self._update_status_bar()

    def _toggle_connection(self):
        """Connect or disconnect from the selected server."""
        if self.executor and self._is_connected():
            self._disconnect()
            return

        if not self.current_server:
            self._log("Error: No server selected.")
            return

        self._log(f"Connecting to {self.current_server.label}...")
        self.connect_btn.configure(state="disabled", text="Connecting...")
        self._update_status_bar("Connecting...")

        def connect_thread():
            try:
                executor = Executor(self.current_server)
                executor.connect()
                self.executor = executor
                self._log(f"✓ Connected to {self.current_server.label}")
                self.after(0, lambda: self.connect_btn.configure(
                    text="Disconnect", state="normal",
                    fg_color=Colors.DANGER))
                self.after(0, self._update_status_bar)
                # Auto-refresh status
                self.after(500, self._refresh_status)
            except Exception as e:
                self._log(f"✗ Connection failed: {e}")
                self.after(0, lambda: self.connect_btn.configure(
                    text="Connect", state="normal",
                    fg_color=Colors.PRIMARY))

        threading.Thread(target=connect_thread, daemon=True).start()

    def _disconnect(self):
        """Disconnect from the server."""
        if self.executor:
            try:
                self.executor.disconnect()
            except Exception:
                pass
            self.executor = None
        self.connect_btn.configure(text="Connect", fg_color=Colors.PRIMARY)
        self._log(f"Disconnected.")
        self._update_status_bar()

    def _is_connected(self) -> bool:
        """Check if we have an active connection."""
        if not self.executor:
            return False
        try:
            self.executor.ensure_connected()
            return True
        except Exception:
            return False

    # ── Proxy Operations ─────────────────────────────────────────────────

    def _apply_proxy(self):
        """Apply proxy configuration to the remote server."""
        if not self._check_connection(): return
        if not self.current_profile:
            self._log("Error: No profile selected.")
            return

        profile = self.current_profile
        config = profile.config
        if not config.is_enabled:
            self._log(f"Profile '{profile.name}' has no proxy configured. Use 'Disable' instead.")
            return

        tools = [k for k, v in self.tool_vars.items() if v.get()]
        if not tools:
            self._log("No tools selected. Check at least one tool.")
            return

        self._set_buttons_state("disabled")
        proxy_dict = config.to_dict()
        self._log(f"\n{'='*50}")
        self._log(f"Applying profile: {profile.name}")
        self._log(f"Proxy: {config.primary_proxy}")
        if config.no_proxy:
            self._log(f"No-Proxy: {config.no_proxy}")
        self._log(f"Tools: {', '.join(tools)}")
        self._log(f"{'='*50}")

        def apply_thread():
            try:
                backends = get_backends(tools)
                results = []
                for bname, bcls in backends.items():
                    try:
                        backend = bcls()
                        if not backend.can_apply(self.executor):
                            self._log(f"  ⏭  {bname:15s}  skipped (not installed)")
                            results.append((bname, "skipped"))
                            continue
                        result = backend.enable(proxy_dict, self.executor)
                        if result.get("success"):
                            self._log(f"  ✓  {bname:15s}  enabled")
                            results.append((bname, "enabled"))
                        else:
                            self._log(f"  ✗  {bname:15s}  {result.get('message', 'failed')}")
                            results.append((bname, "failed"))
                    except Exception as e:
                        self._log(f"  ✗  {bname:15s}  error: {e}")
                        results.append((bname, "error"))

                enabled = sum(1 for _, s in results if s == "enabled")
                failed = sum(1 for _, s in results if s in ("failed", "error"))
                skipped = sum(1 for _, s in results if s == "skipped")
                self._log(f"{'='*50}")
                self._log(f"Done: {enabled} enabled, {failed} failed, {skipped} skipped.")
            except Exception as e:
                self._log(f"Error: {e}")
            finally:
                self.after(0, lambda: self._set_buttons_state("normal"))

        threading.Thread(target=apply_thread, daemon=True).start()

    def _disable_proxy(self):
        """Disable proxy on the remote server."""
        if not self._check_connection(): return

        tools = [k for k, v in self.tool_vars.items() if v.get()]
        if not tools:
            self._log("No tools selected. Check at least one tool.")
            return

        self._set_buttons_state("disabled")
        self._log(f"\n{'='*50}")
        self._log(f"Disabling proxy for: {', '.join(tools)}")
        self._log(f"{'='*50}")

        def disable_thread():
            try:
                backends = get_backends(tools)
                results = []
                for bname, bcls in backends.items():
                    try:
                        backend = bcls()
                        if not backend.can_apply(self.executor):
                            self._log(f"  ⏭  {bname:15s}  skipped (not installed)")
                            continue
                        result = backend.disable(self.executor)
                        if result.get("success"):
                            self._log(f"  ✓  {bname:15s}  disabled")
                        else:
                            self._log(f"  ✗  {bname:15s}  {result.get('message', '')}")
                    except Exception as e:
                        self._log(f"  ✗  {bname:15s}  error: {e}")

                self._log(f"{'='*50}")
                self._log("Done. Proxy disabled.")
            except Exception as e:
                self._log(f"Error: {e}")
            finally:
                self.after(0, lambda: self._set_buttons_state("normal"))

        threading.Thread(target=disable_thread, daemon=True).start()

    def _refresh_status(self):
        """Check proxy status on the remote server."""
        if not self._check_connection(): return

        self._set_buttons_state("disabled")
        self._log(f"\n--- Proxy Status ---")

        def status_thread():
            try:
                backends = get_all_backends()
                # First detect which tools are installed
                self._log(f"{'Tool':20s} {'Status':12s} Proxy URL")
                self._log("-" * 60)
                for bname, bcls in backends.items():
                    try:
                        backend = bcls()
                        if not backend.can_apply(self.executor):
                            self._log(f"{bname:20s} {'NOT INSTALLED':12s}")
                            continue
                        s = backend.status(self.executor)
                        status = "ENABLED" if s.get("enabled") else "disabled"
                        proxy = s.get("proxy", "") or ""
                        self._log(f"{bname:20s} {status:12s} {proxy}")
                    except Exception as e:
                        self._log(f"{bname:20s} {'ERROR':12s} {e}")
            except Exception as e:
                self._log(f"Error getting status: {e}")
            finally:
                self.after(0, lambda: self._set_buttons_state("normal"))

        threading.Thread(target=status_thread, daemon=True).start()

    # ── Logging ─────────────────────────────────────────────────────────

    def _log(self, message: str):
        """Append a message to the log area."""
        def _append():
            self.log_text.configure(state="normal")
            self.log_text.insert("end", message + "\n")
            self.log_text.see("end")
            self.log_text.configure(state="disabled")
        self.after(0, _append)

    def _update_status_bar(self, text: str = ""):
        """Update the status bar text."""
        if text:
            self.status_bar.configure(text=text)
        elif self.executor and self._is_connected():
            server_name = self.current_server.name if self.current_server else "?"
            self.status_bar.configure(
                text=f"Connected: {server_name}  |  Profile: {self.profile_var.get()}")
        else:
            self.status_bar.configure(text="Not connected")

    def _check_connection(self) -> bool:
        """Check if connected, log message if not."""
        if not self.executor:
            self._log("Error: Not connected to any server. Click 'Connect' first.")
            return False
        try:
            self.executor.ensure_connected()
            return True
        except Exception as e:
            self._log(f"Connection lost: {e}")
            self.after(0, lambda: self.connect_btn.configure(text="Connect"))
            return False

    def _set_buttons_state(self, state: str):
        """Enable or disable action buttons."""
        for btn in [self.apply_btn, self.disable_btn, self.refresh_btn]:
            btn.configure(state=state)

    # ── Menu Actions ────────────────────────────────────────────────────

    def _file_menu(self):
        """Show file menu popup."""
        # Simple popup menu simulation
        dialog = ctk.CTkToplevel(self)
        dialog.title("")
        dialog.geometry("200x120")
        dialog.resizable(False, False)
        dialog.transient(self)
        dialog.grab_set()

        ctk.CTkButton(dialog, text="Add Server...", anchor="w",
                       command=lambda: self._add_server(dialog)).pack(
            fill="x", padx=5, pady=2)
        ctk.CTkButton(dialog, text="Add Profile...", anchor="w",
                       command=lambda: self._add_profile(dialog)).pack(
            fill="x", padx=5, pady=2)
        ctk.CTkButton(dialog, text="Exit", anchor="w",
                       command=self._on_close).pack(
            fill="x", padx=5, pady=(2, 5))

    def _open_settings(self):
        """Open settings dialog."""
        # For now, just trigger a refresh
        self._refresh_config()
        self._log("Config reloaded.")

    def _add_server(self, parent=None):
        """Open dialog to add a new server."""
        parent_window = parent or self
        dialog = ServerDialog(parent_window)
        self.wait_window(dialog)
        self._refresh_config()

    def _add_profile(self, parent=None):
        """Open dialog to add a new profile."""
        parent_window = parent or self
        dialog = ProfileDialog(parent_window)
        self.wait_window(dialog)
        self._refresh_config()

    def _show_about(self):
        """Show about dialog."""
        about = ctk.CTkToplevel(self)
        about.title(f"About Proxy-Switch v{__version__}")
        about.geometry("350x200")
        about.resizable(False, False)
        about.transient(self)
        about.grab_set()

        ctk.CTkLabel(about, text=f"Proxy-Switch v{__version__}",
                      font=ctk.CTkFont(size=18, weight="bold")).pack(pady=(20, 5))
        ctk.CTkLabel(about, text="One-click proxy configuration for Ubuntu servers",
                      wraplength=300).pack(pady=5)
        ctk.CTkLabel(about, text="\nManages: system env, APT, Git, Docker,\n"
                                   "Maven, Gradle, npm, pip, curl, wget, Snap",
                      wraplength=300, justify="center").pack(pady=5)
        ctk.CTkButton(about, text="Close", command=about.destroy).pack(pady=10)

    def _on_close(self):
        """Clean shutdown."""
        close_all_connections()
        self.destroy()
