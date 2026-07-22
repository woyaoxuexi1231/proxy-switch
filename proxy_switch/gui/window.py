"""Proxy-Switch main window.

Each feature (System Proxy, APT, Docker, Git, npm, Maven) is a
separate row with its own status display, Configure, and Disable buttons.
"""

from __future__ import annotations

import threading
from pathlib import Path
from typing import Dict, Optional

import customtkinter as ctk

from .. import __version__
from ..core.models import Server
from ..core import config as cfg
from ..features import get_all, discover
from ..ssh.connection import Executor, close_all_connections

from .theme import Colors, setup_theme, font_body, font_small, font_mono
from .dialogs import ServerDialog, FeatureConfigDialog


class MainWindow(ctk.CTk):
    """Main application window."""

    def __init__(self):
        super().__init__()
        setup_theme()

        self.title(f"Proxy-Switch v{__version__}")
        self.geometry("780x720")
        self.minsize(650, 600)
        self.center_on_screen()

        # State
        self.servers: Dict[str, Server] = {}
        self.current_server: Optional[Server] = None
        self.executor: Optional[Executor] = None

        # Feature widgets: {name: (row_frame, status_label, btn_frame)}
        self._feature_rows: Dict[str, tuple] = {}

        icon_png = Path(__file__).parent.parent.parent / "assets" / "icon.png"
        icon_ico = icon_png.with_suffix(".ico")
        if icon_ico.exists():
            try:
                self.iconbitmap(str(icon_ico))
            except Exception:
                pass

        self._build_menubar()
        self._build_ui()
        self._load_servers()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # ── Menubar ────────────────────────────────────────────────────────

    def _build_menubar(self):
        bar = ctk.CTkFrame(self, height=30, corner_radius=0)
        bar.pack(fill="x")
        bar.pack_propagate(False)

        ctk.CTkButton(bar, text="File", width=50, height=25,
                       fg_color="transparent", text_color=Colors.TEXT_PRIMARY,
                       hover_color="#E0E0E0",
                       command=self._file_menu).pack(side="left", padx=2)
        ctk.CTkButton(bar, text="Reload", width=70, height=25,
                       fg_color="transparent", text_color=Colors.TEXT_PRIMARY,
                       hover_color="#E0E0E0",
                       command=self._reload_config).pack(side="left", padx=2)
        ctk.CTkButton(bar, text="Help", width=50, height=25,
                       fg_color="transparent", text_color=Colors.TEXT_PRIMARY,
                       hover_color="#E0E0E0",
                       command=self._show_about).pack(side="left", padx=2)

    # ── Main UI ────────────────────────────────────────────────────────

    def _build_ui(self):
        main = ctk.CTkFrame(self)
        main.pack(fill="both", expand=True, padx=15, pady=(10, 15))
        main.grid_columnconfigure(0, weight=1)
        main.grid_rowconfigure(2, weight=1)

        self._build_connection_area(main)
        self._build_feature_list(main)
        self._build_log_area(main)
        self._build_status_bar()

    def _build_connection_area(self, parent):
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        frame.grid_columnconfigure(0, weight=1)

        conn_row = ctk.CTkFrame(frame, fg_color="transparent")
        conn_row.pack(fill="x")

        ctk.CTkLabel(conn_row, text="Server:", anchor="w",
                      font=font_body()).pack(side="left", padx=(0, 5))
        self.server_var = ctk.StringVar(value="(no servers)")
        self.server_menu = ctk.CTkOptionMenu(
            conn_row, variable=self.server_var,
            values=["(no servers)"],
            command=self._on_server_change, width=200)
        self.server_menu.pack(side="left", padx=(0, 10))

        self.connect_btn = ctk.CTkButton(
            conn_row, text="Connect", width=90,
            command=self._toggle_connection)
        self.connect_btn.pack(side="left", padx=(0, 5))

        self.refresh_btn = ctk.CTkButton(
            conn_row, text="Refresh Status", width=110,
            command=self._refresh_all_status,
            fg_color=Colors.PRIMARY)
        self.refresh_btn.pack(side="left")

    def _build_feature_list(self, parent):
        """Build the feature list — each feature is a row with buttons."""
        container = ctk.CTkFrame(parent)
        container.grid(row=1, column=0, sticky="nsew", pady=(0, 10))
        container.grid_columnconfigure(0, weight=1)
        container.grid_rowconfigure(1, weight=1)

        # Header
        ctk.CTkLabel(container, text="Proxy / Mirror Configuration",
                      anchor="w", font=ctk.CTkFont(size=15, weight="bold")).grid(
            row=0, column=0, sticky="w", padx=15, pady=(10, 5))

        # Scrollable list of features
        scroll = ctk.CTkScrollableFrame(container)
        scroll.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))
        scroll.grid_columnconfigure(1, weight=1)  # status column stretches

        # Column headers
        ctk.CTkLabel(scroll, text="Feature", anchor="w",
                      font=ctk.CTkFont(size=12, weight="bold")).grid(
            row=0, column=0, padx=(5, 10), pady=(0, 5), sticky="w")
        ctk.CTkLabel(scroll, text="Status", anchor="w",
                      font=ctk.CTkFont(size=12, weight="bold")).grid(
            row=0, column=1, padx=5, pady=(0, 5), sticky="w")
        ctk.CTkLabel(scroll, text="Actions", anchor="w",
                      font=ctk.CTkFont(size=12, weight="bold")).grid(
            row=0, column=2, padx=5, pady=(0, 5))

        self.feature_names = sorted(discover().keys())
        for i, fname in enumerate(self.feature_names):
            mod = get_all()[fname]
            has_mirror = getattr(mod, "SUPPORTS_MIRROR", False)

            row_frame = ctk.CTkFrame(scroll, fg_color="transparent")
            row_frame.grid(row=i + 1, column=0, columnspan=3,
                           sticky="ew", pady=3)
            row_frame.grid_columnconfigure(1, weight=1)

            # Feature name
            label = fname.replace("_", " ").title()
            if has_mirror:
                label += " *"  # indicate mirror support
            ctk.CTkLabel(row_frame, text=label, anchor="w",
                          font=font_body(),
                          width=100).grid(row=0, column=0, padx=(5, 10), sticky="w")

            # Status label (updated dynamically)
            status_label = ctk.CTkLabel(
                row_frame, text="—", anchor="w",
                font=ctk.CTkFont(size=12))
            status_label.grid(row=0, column=1, padx=5, sticky="w")

            # Action buttons
            btn_frame = ctk.CTkFrame(row_frame, fg_color="transparent")
            btn_frame.grid(row=0, column=2, padx=5, sticky="e")
            ctk.CTkButton(btn_frame, text="⚙  Config", width=80,
                           height=26,
                           command=lambda n=fname: self._configure_feature(n)
                           ).pack(side="left", padx=2)
            ctk.CTkButton(btn_frame, text="✕  Off", width=60,
                           height=26,
                           fg_color=Colors.DANGER,
                           command=lambda n=fname: self._disable_feature(n)
                           ).pack(side="left", padx=2)

            self._feature_rows[fname] = (row_frame, status_label, btn_frame)

        # Separator and Refresh All button
        sep = ctk.CTkFrame(container, height=2, fg_color="#E0E0E0")
        sep.grid(row=2, column=0, sticky="ew", padx=15, pady=5)

    def _build_log_area(self, parent):
        frame = ctk.CTkFrame(parent)
        frame.grid(row=2, column=0, sticky="nsew")
        frame.grid_rowconfigure(1, weight=1)
        frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(frame, text="Status / Log", anchor="w",
                      font=ctk.CTkFont(size=13, weight="bold")).grid(
            row=0, column=0, sticky="w", padx=15, pady=(10, 5))

        self.log_text = ctk.CTkTextbox(
            frame, font=font_mono(), wrap="word", state="disabled")
        self.log_text.grid(row=1, column=0, sticky="nsew", padx=15, pady=(0, 10))

    def _build_status_bar(self):
        self.status_bar = ctk.CTkLabel(
            self, text="Ready", anchor="w", font=font_small(),
            fg_color=Colors.CARD_BORDER)
        self.status_bar.pack(fill="x", padx=0, pady=0)

    # ── Window Positioning ─────────────────────────────────────────────

    def center_on_screen(self):
        self.update_idletasks()
        w = self.winfo_width()
        h = self.winfo_height()
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        self.geometry(f"+{(sw - w) // 2}+{(sh - h) // 2}")

    def _center_popup(self, window):
        self.update_idletasks()
        window.update_idletasks()
        x = self.winfo_x() + (self.winfo_width() - window.winfo_width()) // 2
        y = self.winfo_y() + (self.winfo_height() - window.winfo_height()) // 2
        window.geometry(f"+{x}+{y}")

    # ── Server Management ──────────────────────────────────────────────

    def _load_servers(self):
        self.servers = cfg.load_servers()
        if self.servers:
            names = list(self.servers.keys())
            self.server_menu.configure(values=names)
            cur = self.server_var.get()
            if cur not in names:
                self.server_var.set(names[0])
                self._on_server_change(names[0])
        else:
            self.server_menu.configure(values=["(no servers)"])
            self.server_var.set("(no servers)")

    def _on_server_change(self, name: str):
        if name in self.servers:
            self.current_server = self.servers[name]
            self._log(f"Selected server: {name} ({self.current_server.host})")
        else:
            self.current_server = None
        self._update_status_bar()

    def _file_menu(self):
        popup = ctk.CTkToplevel(self)
        popup.title("")
        popup.geometry("200x90")
        popup.resizable(False, False)
        popup.transient(self)
        popup.grab_set()
        self._center_popup(popup)

        ctk.CTkButton(popup, text="Add Server...", anchor="w",
                       command=lambda: self._add_server(popup)).pack(
            fill="x", padx=5, pady=2)
        ctk.CTkButton(popup, text="Exit", anchor="w",
                       command=self._on_close).pack(
            fill="x", padx=5, pady=2)

    def _reload_config(self):
        self._load_servers()
        msg = "Config reloaded."
        if self.servers:
            msg += f" {len(self.servers)} server(s)"
        self._log(msg)

    def _add_server(self, parent=None):
        dialog = ServerDialog(parent or self)
        self.wait_window(dialog)
        self._load_servers()

    # ── Connection ─────────────────────────────────────────────────────

    def _toggle_connection(self):
        if self.executor and self._is_connected():
            self._disconnect()
            return
        if not self.current_server:
            self._log("Error: No server selected.")
            return

        self._log(f"Connecting to {self.current_server.label}...")
        self.connect_btn.configure(state="disabled", text="Connecting...")

        def work():
            try:
                ex = Executor(self.current_server)
                ex.connect()
                self.executor = ex
                self._log(f"✓ Connected to {self.current_server.label}")
                self.after(0, lambda: self.connect_btn.configure(
                    text="Disconnect", state="normal", fg_color=Colors.DANGER))
                self.after(0, self._update_status_bar)
                self.after(500, self._refresh_all_status)
            except Exception as e:
                self._log(f"✗ Connection failed: {e}")
                self.after(0, lambda: self.connect_btn.configure(
                    text="Connect", state="normal", fg_color=Colors.PRIMARY))

        threading.Thread(target=work, daemon=True).start()

    def _disconnect(self):
        if self.executor:
            try:
                self.executor.disconnect()
            except Exception:
                pass
            self.executor = None
        self.connect_btn.configure(text="Connect", fg_color=Colors.PRIMARY)
        self._log("Disconnected.")
        self._update_status_bar()

    def _is_connected(self) -> bool:
        if not self.executor:
            return False
        try:
            self.executor.ensure_connected()
            return True
        except Exception:
            return False

    # ── Feature Operations ─────────────────────────────────────────────

    def _configure_feature(self, fname: str):
        """Open config dialog for a specific feature."""
        if not self._check_connected():
            return

        dialog = FeatureConfigDialog(
            self, fname, executor=self.executor,
            on_done=self._on_feature_done)
        self.wait_window(dialog)
        self._update_feature_status(fname)

    def _disable_feature(self, fname: str):
        """Disable a specific feature."""
        if not self._check_connected():
            return

        mod = get_all().get(fname)
        if not mod:
            return

        self._log(f"Disabling {fname}...")

        def work():
            try:
                result = mod.disable(self.executor)
                msg = f"  {'✓' if result.success else '✗'} {fname}: {result.message}"
                self._log(msg)
                s = mod.status(self.executor)
                self.after(0, lambda: self._update_row_status(fname, s))
            except Exception as e:
                self._log(f"  ✗ {fname}: error — {e}")

        threading.Thread(target=work, daemon=True).start()

    def _refresh_all_status(self):
        """Check status of all features."""
        if not self._check_connected():
            return

        self._log("\n--- Proxy Status ---")

        def work():
            for fname, mod in sorted(get_all().items()):
                try:
                    installed = mod.detect(self.executor)
                    if not installed:
                        self._log(f"  ⏭ {fname}: NOT INSTALLED")
                        self.after(0, lambda n=fname: self._update_row_status(
                            n, None))
                        continue
                    s = mod.status(self.executor)
                    status_text = "ENABLED" if s.enabled else "disabled"
                    parts = [f"  {'●' if s.enabled else '○'} {fname}: {status_text}"]
                    if s.proxy:
                        parts.append(s.proxy)
                    if s.mirror:
                        parts.append(f"mirror={s.mirror}")
                    self._log("  |  ".join(parts))
                    self.after(0, lambda n=fname, st=s: self._update_row_status(n, st))
                except Exception as e:
                    self._log(f"  ✗ {fname}: {e}")
                    self.after(0, lambda n=fname: self._update_row_status(n, None))

        threading.Thread(target=work, daemon=True).start()

    def _on_feature_done(self, fname: str, message: str):
        """Callback after feature config dialog apply/disable."""
        self._log(f"{fname}: {message}")

    def _update_feature_status(self, fname: str):
        """Update a single feature row by querying the server."""
        mod = get_all().get(fname)
        if not mod:
            return

        def work():
            try:
                if not mod.detect(self.executor):
                    self.after(0, lambda: self._update_row_status(fname, None))
                    return
                s = mod.status(self.executor)
                self.after(0, lambda: self._update_row_status(fname, s))
            except Exception:
                self.after(0, lambda: self._update_row_status(fname, None))

        threading.Thread(target=work, daemon=True).start()

    def _update_row_status(self, fname: str, status):
        """Update the status label for a feature row."""
        if fname not in self._feature_rows:
            return
        _, label, _ = self._feature_rows[fname]

        if status is None:
            label.configure(text="NOT INSTALLED", text_color=Colors.DISABLED)
            return

        parts = []
        if status.enabled:
            parts.append("● ENABLED")
            label.configure(text_color=Colors.SUCCESS)
        else:
            parts.append("○ disabled")
            label.configure(text_color=Colors.TEXT_SECONDARY)
        if status.proxy:
            parts.append(status.proxy)
        if status.mirror:
            parts.append(f"mirror: {status.mirror}")
        label.configure(text="  |  ".join(parts))

    # ── Logging ────────────────────────────────────────────────────────

    def _log(self, message: str):
        def _append():
            self.log_text.configure(state="normal")
            self.log_text.insert("end", message + "\n")
            self.log_text.see("end")
            self.log_text.configure(state="disabled")
        self.after(0, _append)

    def _update_status_bar(self, text: str = ""):
        if text:
            self.status_bar.configure(text=text)
        elif self.executor and self._is_connected():
            name = self.current_server.name if self.current_server else "?"
            self.status_bar.configure(text=f"Connected: {name}")
        else:
            self.status_bar.configure(text="Not connected")

    def _check_connected(self) -> bool:
        if not self.executor:
            self._log("Error: Not connected. Click 'Connect' first.")
            return False
        try:
            self.executor.ensure_connected()
            return True
        except Exception as e:
            self._log(f"Connection lost: {e}")
            self.after(0, lambda: self.connect_btn.configure(text="Connect"))
            return False

    # ── Dialogs ────────────────────────────────────────────────────────

    def _show_about(self):
        about = ctk.CTkToplevel(self)
        about.title(f"About Proxy-Switch v{__version__}")
        about.geometry("350x200")
        about.resizable(False, False)
        about.transient(self)
        about.grab_set()
        self._center_popup(about)

        ctk.CTkLabel(about, text=f"Proxy-Switch v{__version__}",
                      font=ctk.CTkFont(size=18, weight="bold")).pack(pady=(20, 5))
        ctk.CTkLabel(about, text="One-click proxy configuration for Ubuntu servers",
                      wraplength=300).pack(pady=5)
        ctk.CTkLabel(about, text="\nManages: system proxy, APT, Git, Docker,\n"
                                   "npm, Maven",
                      wraplength=300, justify="center").pack(pady=5)
        ctk.CTkButton(about, text="Close", command=about.destroy).pack(pady=10)

    def _on_close(self):
        close_all_connections()
        self.destroy()
