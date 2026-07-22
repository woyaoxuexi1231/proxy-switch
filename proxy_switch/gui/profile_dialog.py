"""Profile add/edit dialog."""

import customtkinter as ctk
from typing import Optional

from ..core.models import Profile, ProxyConfig, ProxyAuth
from ..core import app_config


class ProfileDialog(ctk.CTkToplevel):
    """Dialog for adding or editing a proxy profile."""

    def __init__(self, parent, profile: Optional[Profile] = None,
                 defaults: Optional[ProxyConfig] = None):
        super().__init__(parent)
        self.profile = profile
        self.defaults = defaults
        self.result: Optional[Profile] = None

        self.title("Edit Profile" if profile else "Add Profile")
        self.geometry("480x480")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        self._build_ui()
        if profile:
            self._populate(profile)

        self.center_on_parent(parent)

    def center_on_parent(self, parent):
        """Center this dialog on the parent window."""
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

    def _build_ui(self):
        """Build the dialog UI."""
        self.grid_columnconfigure(1, weight=1)

        row = 0

        # Name
        ctk.CTkLabel(self, text="Profile Name:", anchor="w").grid(
            row=row, column=0, padx=(20, 10), pady=(20, 5), sticky="w")
        self.name_entry = ctk.CTkEntry(self, placeholder_text="home")
        self.name_entry.grid(row=row, column=1, padx=(0, 20), pady=(20, 5), sticky="ew")
        row += 1

        # Description
        ctk.CTkLabel(self, text="Description:", anchor="w").grid(
            row=row, column=0, padx=(20, 10), pady=5, sticky="w")
        self.desc_entry = ctk.CTkEntry(self, placeholder_text="Home network proxy")
        self.desc_entry.grid(row=row, column=1, padx=(0, 20), pady=5, sticky="ew")
        row += 1

        separator = ctk.CTkFrame(self, height=2, fg_color="#E0E0E0")
        separator.grid(row=row, column=0, columnspan=2, padx=20, pady=10, sticky="ew")
        row += 1

        # Proxy URL fields
        ctk.CTkLabel(self, text="Proxy URLs", anchor="w",
                      font=ctk.CTkFont(size=13, weight="bold")).grid(
            row=row, column=0, columnspan=2, padx=20, pady=(0, 5), sticky="w")
        row += 1

        fields = [
            ("HTTP Proxy:", "http_proxy", "http://127.0.0.1:7890"),
            ("HTTPS Proxy:", "https_proxy", "http://127.0.0.1:7890"),
            ("SOCKS5 Proxy:", "socks_proxy", "socks5://127.0.0.1:7891"),
            ("No Proxy:", "no_proxy", "localhost,127.0.0.1,::1"),
        ]

        self.entries = {}
        for label_text, key, placeholder in fields:
            ctk.CTkLabel(self, text=label_text, anchor="w").grid(
                row=row, column=0, padx=(20, 10), pady=4, sticky="w")
            entry = ctk.CTkEntry(self, placeholder_text=placeholder)
            entry.grid(row=row, column=1, padx=(0, 20), pady=4, sticky="ew")
            self.entries[key] = entry
            row += 1

        # Authentication section
        separator2 = ctk.CTkFrame(self, height=2, fg_color="#E0E0E0")
        separator2.grid(row=row, column=0, columnspan=2, padx=20, pady=10, sticky="ew")
        row += 1

        self.need_auth = ctk.CTkCheckBox(self, text="Requires Authentication",
                                          command=self._toggle_auth)
        self.need_auth.grid(row=row, column=0, columnspan=2, padx=20, pady=(0, 5), sticky="w")
        row += 1

        ctk.CTkLabel(self, text="Username:", anchor="w").grid(
            row=row, column=0, padx=(20, 10), pady=4, sticky="w")
        self.auth_user_entry = ctk.CTkEntry(self, placeholder_text="proxy_user")
        self.auth_user_entry.grid(row=row, column=1, padx=(0, 20), pady=4, sticky="ew")
        self.auth_user_entry.configure(state="disabled")
        row += 1

        ctk.CTkLabel(self, text="Password:", anchor="w").grid(
            row=row, column=0, padx=(20, 10), pady=4, sticky="w")
        self.auth_pass_entry = ctk.CTkEntry(self, placeholder_text="(leave blank to not store)",
                                             show="*")
        self.auth_pass_entry.grid(row=row, column=1, padx=(0, 20), pady=4, sticky="ew")
        self.auth_pass_entry.configure(state="disabled")
        row += 1

        # Buttons
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.grid(row=row, column=0, columnspan=2, pady=(15, 15))
        ctk.CTkButton(btn_frame, text="Cancel", width=100,
                       command=self.destroy).pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="Save", width=100,
                       command=self._save, fg_color="#2B5797").pack(side="left", padx=5)

    def _populate(self, profile: Profile):
        """Fill form with existing profile data."""
        self.name_entry.insert(0, profile.name)
        self.desc_entry.insert(0, profile.description)
        config = profile.config
        self.entries["http_proxy"].insert(0, config.http_proxy)
        self.entries["https_proxy"].insert(0, config.https_proxy)
        self.entries["socks_proxy"].insert(0, config.socks_proxy)
        self.entries["no_proxy"].insert(0, config.no_proxy)
        if config.auth.username:
            self.need_auth.select()
            self._toggle_auth()
            self.auth_user_entry.insert(0, config.auth.username)
        if config.auth.password:
            self.auth_pass_entry.insert(0, config.auth.password)

    def _toggle_auth(self):
        """Enable/disable auth fields."""
        state = "normal" if self.need_auth.get() else "disabled"
        self.auth_user_entry.configure(state=state)
        self.auth_pass_entry.configure(state=state)

    def _save(self):
        """Validate and save the profile."""
        name = self.name_entry.get().strip()
        if not name:
            self._show_error("Profile name is required.")
            return
        if name == "direct":
            self._show_error("'direct' is a reserved profile name.")
            return

        config = ProxyConfig(
            http_proxy=self.entries["http_proxy"].get().strip(),
            https_proxy=self.entries["https_proxy"].get().strip(),
            socks_proxy=self.entries["socks_proxy"].get().strip(),
            no_proxy=self.entries["no_proxy"].get().strip(),
        )
        if self.need_auth.get():
            config.auth = ProxyAuth(
                username=self.auth_user_entry.get().strip(),
                password=self.auth_pass_entry.get(),
            )

        profile = Profile(
            name=name,
            config=config,
            description=self.desc_entry.get().strip(),
        )

        app_config.save_profile(profile, self.defaults)
        self.result = profile
        self.destroy()

    def _show_error(self, msg: str):
        """Show error in a label."""
        if hasattr(self, "error_label"):
            self.error_label.destroy()
        self.error_label = ctk.CTkLabel(
            self, text=msg, text_color="red",
            font=ctk.CTkFont(size=11))
        self.error_label.grid(row=20, column=0, columnspan=2, pady=(0, 10))
