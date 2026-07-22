"""Server dialog and per-feature configuration dialogs."""

from __future__ import annotations

from types import ModuleType
from typing import Optional

import customtkinter as ctk

from ..core.models import Server, Result
from ..core import config as cfg
from ..features import get_all


# ═══════════════════════════════════════════════════════════════════════════
# Server Dialog
# ═══════════════════════════════════════════════════════════════════════════


class ServerDialog(ctk.CTkToplevel):
    """Dialog for adding or editing an SSH server."""

    def __init__(self, parent: ctk.CTk, server: Optional[Server] = None):
        super().__init__(parent)
        self.server = server
        self.result: Optional[Server] = None

        self.title("Edit Server" if server else "Add Server")
        self.geometry("480x400")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        self._build_ui()
        if server:
            self._populate(server)
        self._center_on_parent(parent)

    def _center_on_parent(self, parent: ctk.CTk) -> None:
        self.update_idletasks()
        pw = parent.winfo_width()
        ph = parent.winfo_height()
        px = parent.winfo_x()
        py = parent.winfo_y()
        w = self.winfo_width()
        h = self.winfo_height()
        x = px + (pw - w) // 2
        y = py + (ph - h) // 2
        self.geometry(f"+{x}+{y}")

    def _build_ui(self) -> None:
        self.grid_columnconfigure(1, weight=1)
        row = 0
        fields = [
            ("Server Name:", "name", "my-ubuntu"),
            ("Host:", "host", "192.168.1.100"),
            ("SSH Port:", "port", "22"),
            ("User:", "user", "root"),
        ]
        self.entries = {}
        for label, key, placeholder in fields:
            ctk.CTkLabel(self, text=label, anchor="w").grid(
                row=row, column=0, padx=(20, 10), pady=(5, 3), sticky="w")
            entry = ctk.CTkEntry(self, placeholder_text=placeholder)
            entry.grid(row=row, column=1, padx=(0, 20), pady=(5, 3), sticky="ew")
            self.entries[key] = entry
            row += 1

        ctk.CTkLabel(self, text="Auth Mode:", anchor="w").grid(
            row=row, column=0, padx=(20, 10), pady=(5, 3), sticky="w")
        self.auth_mode = ctk.CTkOptionMenu(
            self, values=["key", "password"],
            command=self._on_auth_mode_change)
        self.auth_mode.grid(row=row, column=1, padx=(0, 20), pady=(5, 3), sticky="ew")
        row += 1

        ctk.CTkLabel(self, text="SSH Key Path:", anchor="w").grid(
            row=row, column=0, padx=(20, 10), pady=(5, 3), sticky="w")
        key_frame = ctk.CTkFrame(self, fg_color="transparent")
        key_frame.grid(row=row, column=1, padx=(0, 20), pady=(5, 3), sticky="ew")
        key_frame.grid_columnconfigure(0, weight=1)
        self.key_entry = ctk.CTkEntry(key_frame, placeholder_text="~/.ssh/id_rsa")
        self.key_entry.grid(row=0, column=0, sticky="ew", padx=(0, 5))
        ctk.CTkButton(key_frame, text="Browse", width=70,
                       command=self._browse_key).grid(row=0, column=1)
        row += 1

        ctk.CTkLabel(self, text="Password:", anchor="w").grid(
            row=row, column=0, padx=(20, 10), pady=(5, 3), sticky="w")
        self.password_entry = ctk.CTkEntry(self, placeholder_text="(leave blank for key auth)",
                                           show="*")
        self.password_entry.grid(row=row, column=1, padx=(0, 20), pady=(5, 3), sticky="ew")
        self.password_entry.configure(state="disabled")
        row += 1

        ctk.CTkLabel(self, text="Description:", anchor="w").grid(
            row=row, column=0, padx=(20, 10), pady=(5, 3), sticky="w")
        self.desc_entry = ctk.CTkEntry(self, placeholder_text="Home server")
        self.desc_entry.grid(row=row, column=1, padx=(0, 20), pady=(5, 3), sticky="ew")
        row += 1

        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.grid(row=row, column=0, columnspan=2, pady=(15, 15))
        ctk.CTkButton(btn_frame, text="Cancel", width=100,
                       command=self.destroy).pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="Save", width=100,
                       command=self._save, fg_color="#2B5797").pack(side="left", padx=5)

    def _populate(self, server: Server) -> None:
        self.entries["name"].insert(0, server.name)
        self.entries["host"].insert(0, server.host)
        self.entries["port"].insert(0, str(server.port))
        self.entries["user"].insert(0, server.user)
        self.auth_mode.set(server.auth_mode)
        self.key_entry.insert(0, server.ssh_key)
        if server.password:
            self.password_entry.insert(0, server.password)
        self.desc_entry.insert(0, server.description)
        self._on_auth_mode_change(server.auth_mode)

    def _on_auth_mode_change(self, mode: str) -> None:
        if mode == "key":
            self.key_entry.configure(state="normal")
            self.password_entry.configure(state="disabled")
        else:
            self.key_entry.configure(state="disabled")
            self.password_entry.configure(state="normal")

    def _browse_key(self) -> None:
        from tkinter import filedialog
        path = filedialog.askopenfilename(
            title="Select SSH Private Key",
            filetypes=[("All Files", "*.*"), ("SSH Keys", "*.pem")])
        if path:
            self.key_entry.delete(0, "end")
            self.key_entry.insert(0, path)

    def _save(self) -> None:
        name = self.entries["name"].get().strip()
        host = self.entries["host"].get().strip()
        if not name:
            self._show_error("Server name is required.")
            return
        if not host:
            self._show_error("Host is required.")
            return
        try:
            port = int(self.entries["port"].get().strip() or "22")
        except ValueError:
            self._show_error("Port must be a number.")
            return
        server = Server(
            name=name, host=host, port=port,
            user=self.entries["user"].get().strip() or "root",
            auth_mode=self.auth_mode.get(),
            ssh_key=self.key_entry.get().strip(),
            password=self.password_entry.get(),
            description=self.desc_entry.get().strip(),
        )
        cfg.save_server(server)
        self.result = server
        self.destroy()

    def _show_error(self, msg: str) -> None:
        if hasattr(self, "error_label"):
            self.error_label.destroy()
        self.error_label = ctk.CTkLabel(
            self, text=msg, text_color="red", font=ctk.CTkFont(size=11))
        self.error_label.grid(row=20, column=0, columnspan=2, pady=(0, 10))


# ═══════════════════════════════════════════════════════════════════════════
# Feature Config Dialog
# ═══════════════════════════════════════════════════════════════════════════


class FeatureConfigDialog(ctk.CTkToplevel):
    """Configuration dialog for a single feature module.

    Shows proxy fields (and mirror if the feature supports it).
    Pre-fills current values detected from the server.
    """

    def __init__(self, parent: ctk.CTk, feature_name: str,
                 executor=None, on_done=None):
        super().__init__(parent)
        self.feature_name = feature_name
        self.mod = get_all().get(feature_name)
        self.executor = executor
        self.on_done = on_done  # callback after apply/disable

        if not self.mod:
            self.destroy()
            return

        has_mirror = getattr(self.mod, "SUPPORTS_MIRROR", False)
        self.geometry("420x380" if has_mirror else "420x320")
        self.title(f"Configure {feature_name.replace('_', ' ').title()}")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        self._build_ui(has_mirror)
        self._detect_status()
        self._center_on_parent(parent)

    def _center_on_parent(self, parent: ctk.CTk) -> None:
        self.update_idletasks()
        pw = parent.winfo_width()
        ph = parent.winfo_height()
        px = parent.winfo_x()
        py = parent.winfo_y()
        w = self.winfo_width()
        h = self.winfo_height()
        x = px + (pw - w) // 2
        y = py + (ph - h) // 2
        self.geometry(f"+{x}+{y}")

    def _build_ui(self, has_mirror: bool) -> None:
        self.grid_columnconfigure(1, weight=1)

        # Description
        desc = getattr(self.mod, "DESCRIPTION", "")
        ctk.CTkLabel(self, text=desc, anchor="w",
                      font=ctk.CTkFont(size=11),
                      text_color="gray").grid(
            row=0, column=0, columnspan=2, padx=20, pady=(15, 10), sticky="w")

        # Fields
        row = 1
        self.entries = {}

        ctk.CTkLabel(self, text="HTTP Proxy:", anchor="w").grid(
            row=row, column=0, padx=(20, 10), pady=4, sticky="w")
        self.http_entry = ctk.CTkEntry(self, placeholder_text="http://proxy:port")
        self.http_entry.grid(row=row, column=1, padx=(0, 20), pady=4, sticky="ew")
        self.entries["http_proxy"] = self.http_entry
        row += 1

        ctk.CTkLabel(self, text="HTTPS Proxy:", anchor="w").grid(
            row=row, column=0, padx=(20, 10), pady=4, sticky="w")
        self.https_entry = ctk.CTkEntry(self, placeholder_text="http://proxy:port")
        self.https_entry.grid(row=row, column=1, padx=(0, 20), pady=4, sticky="ew")
        self.entries["https_proxy"] = self.https_entry
        row += 1

        ctk.CTkLabel(self, text="No Proxy:", anchor="w").grid(
            row=row, column=0, padx=(20, 10), pady=4, sticky="w")
        self.no_proxy_entry = ctk.CTkEntry(
            self, placeholder_text="localhost,127.0.0.1,::1")
        self.no_proxy_entry.grid(row=row, column=1, padx=(0, 20), pady=4, sticky="ew")
        self.entries["no_proxy"] = self.no_proxy_entry
        row += 1

        if has_mirror:
            ctk.CTkLabel(self, text="Mirror URL:", anchor="w",
                          font=ctk.CTkFont(size=12, weight="bold")).grid(
                row=row, column=0, padx=(20, 10), pady=(10, 4), sticky="w")
            self.mirror_entry = ctk.CTkEntry(
                self, placeholder_text="https://registry.npmjs.org/")
            self.mirror_entry.grid(row=row, column=1, padx=(0, 20), pady=(10, 4), sticky="ew")
            self.entries["mirror"] = self.mirror_entry
            row += 1

        # Status display
        sep = ctk.CTkFrame(self, height=2, fg_color="#E0E0E0")
        sep.grid(row=row, column=0, columnspan=2, padx=20, pady=(15, 5), sticky="ew")
        row += 1

        self.status_label = ctk.CTkLabel(
            self, text="Status: detecting...", anchor="w",
            font=ctk.CTkFont(size=12))
        self.status_label.grid(row=row, column=0, columnspan=2, padx=20, pady=2, sticky="w")
        row += 1

        # Buttons
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.grid(row=row, column=0, columnspan=2, pady=(15, 15))

        ctk.CTkButton(btn_frame, text="Apply", width=90,
                       command=self._apply,
                       fg_color="#2E7D32").pack(side="left", padx=4)
        ctk.CTkButton(btn_frame, text="Disable", width=90,
                       command=self._disable,
                       fg_color="#C62828").pack(side="left", padx=4)
        ctk.CTkButton(btn_frame, text="Cancel", width=90,
                       command=self.destroy).pack(side="left", padx=4)

    def _detect_status(self) -> None:
        """Fetch current status and pre-fill form fields."""
        def work():
            try:
                s = self.mod.status(self.executor)
                self.after(0, lambda: self._fill_status(s))
            except Exception as e:
                self.after(0, lambda: self.status_label.configure(
                    text=f"Status: detection failed — {e}"))

        import threading
        threading.Thread(target=work, daemon=True).start()

    def _fill_status(self, s) -> None:
        """Pre-fill form with detected status values."""
        if s.proxy:
            # Try to fill http/https — heuristic: if same URL, put in both
            if not self.http_entry.get():
                self.http_entry.insert(0, s.proxy)
            if not self.https_entry.get():
                self.https_entry.insert(0, s.proxy)
        if s.mirror and "mirror" in self.entries:
            if not self.entries["mirror"].get():
                self.entries["mirror"].insert(0, s.mirror)

        status_parts = []
        if s.enabled:
            status_parts.append("● ENABLED")
        else:
            status_parts.append("○ DISABLED")
        if s.proxy:
            status_parts.append(f"Proxy: {s.proxy}")
        if s.mirror:
            status_parts.append(f"Mirror: {s.mirror}")
        self.status_label.configure(text="Status:  " + "  |  ".join(status_parts))

    def _get_proxy_config(self) -> dict:
        """Build proxy_config dict from form fields."""
        config = {
            "http_proxy": self.http_entry.get().strip(),
            "https_proxy": self.https_entry.get().strip(),
            "no_proxy": self.no_proxy_entry.get().strip(),
        }
        if "mirror" in self.entries:
            config["mirror"] = self.entries["mirror"].get().strip()
        return config

    def _apply(self) -> None:
        """Apply proxy config for this feature."""
        proxy_config = self._get_proxy_config()
        if not proxy_config.get("http_proxy") and not proxy_config.get("https_proxy"):
            self._show_error("At least one proxy URL is required.")
            return

        self._set_buttons_state("disabled")
        self.status_label.configure(text="Applying...")

        def work():
            try:
                result = self.mod.enable(proxy_config, self.executor)
                self.after(0, lambda: self._on_result(result))
            except Exception as e:
                self.after(0, lambda: self._show_error(str(e)))
            finally:
                self.after(0, lambda: self._set_buttons_state("normal"))

        import threading
        threading.Thread(target=work, daemon=True).start()

    def _disable(self) -> None:
        """Disable proxy for this feature."""
        self._set_buttons_state("disabled")
        self.status_label.configure(text="Disabling...")

        def work():
            try:
                result = self.mod.disable(self.executor)
                self.after(0, lambda: self._on_result(result))
            except Exception as e:
                self.after(0, lambda: self._show_error(str(e)))
            finally:
                self.after(0, lambda: self._set_buttons_state("normal"))

        import threading
        threading.Thread(target=work, daemon=True).start()

    def _on_result(self, result) -> None:
        """Handle enable/disable result."""
        if result.success:
            self._detect_status()
            if self.on_done:
                self.on_done(self.feature_name, result.message)
        else:
            self._show_error(result.message)

    def _set_buttons_state(self, state: str) -> None:
        for child in self.winfo_children():
            if isinstance(child, ctk.CTkButton):
                child.configure(state=state)

    def _show_error(self, msg: str) -> None:
        self.status_label.configure(text=f"Error: {msg}", text_color="red")
