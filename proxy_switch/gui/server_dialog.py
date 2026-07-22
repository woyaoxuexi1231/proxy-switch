"""Server add/edit dialog."""

import customtkinter as ctk
from typing import Optional

from ..core.models import Server
from ..core import app_config


class ServerDialog(ctk.CTkToplevel):
    """Dialog for adding or editing an SSH server."""

    def __init__(self, parent, server: Optional[Server] = None):
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

        # Name
        ctk.CTkLabel(self, text="Server Name:", anchor="w").grid(
            row=0, column=0, padx=(20, 10), pady=(20, 5), sticky="w")
        self.name_entry = ctk.CTkEntry(self, placeholder_text="my-ubuntu")
        self.name_entry.grid(row=0, column=1, padx=(0, 20), pady=(20, 5), sticky="ew")

        # Host
        ctk.CTkLabel(self, text="Host:", anchor="w").grid(
            row=1, column=0, padx=(20, 10), pady=5, sticky="w")
        self.host_entry = ctk.CTkEntry(self, placeholder_text="192.168.1.100")
        self.host_entry.grid(row=1, column=1, padx=(0, 20), pady=5, sticky="ew")

        # Port
        ctk.CTkLabel(self, text="SSH Port:", anchor="w").grid(
            row=2, column=0, padx=(20, 10), pady=5, sticky="w")
        self.port_entry = ctk.CTkEntry(self, placeholder_text="22")
        self.port_entry.grid(row=2, column=1, padx=(0, 20), pady=5, sticky="ew")

        # User
        ctk.CTkLabel(self, text="User:", anchor="w").grid(
            row=3, column=0, padx=(20, 10), pady=5, sticky="w")
        self.user_entry = ctk.CTkEntry(self, placeholder_text="root")
        self.user_entry.grid(row=3, column=1, padx=(0, 20), pady=5, sticky="ew")

        # Auth Mode
        ctk.CTkLabel(self, text="Auth Mode:", anchor="w").grid(
            row=4, column=0, padx=(20, 10), pady=5, sticky="w")
        self.auth_mode = ctk.CTkOptionMenu(
            self, values=["key", "password"],
            command=self._on_auth_mode_change)
        self.auth_mode.grid(row=4, column=1, padx=(0, 20), pady=5, sticky="ew")

        # SSH Key
        ctk.CTkLabel(self, text="SSH Key Path:", anchor="w").grid(
            row=5, column=0, padx=(20, 10), pady=5, sticky="w")
        self.key_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.key_frame.grid(row=5, column=1, padx=(0, 20), pady=5, sticky="ew")
        self.key_frame.grid_columnconfigure(0, weight=1)
        self.key_entry = ctk.CTkEntry(self.key_frame, placeholder_text="C:\\Users\\me\\.ssh\\id_rsa")
        self.key_entry.grid(row=0, column=0, sticky="ew", padx=(0, 5))
        self.browse_btn = ctk.CTkButton(
            self.key_frame, text="Browse", width=70,
            command=self._browse_key)
        self.browse_btn.grid(row=0, column=1)

        # Password
        ctk.CTkLabel(self, text="Password:", anchor="w").grid(
            row=6, column=0, padx=(20, 10), pady=5, sticky="w")
        self.password_entry = ctk.CTkEntry(self, placeholder_text="(leave blank for key auth)",
                                            show="*")
        self.password_entry.grid(row=6, column=1, padx=(0, 20), pady=5, sticky="ew")
        self.password_entry.configure(state="disabled")

        # Description
        ctk.CTkLabel(self, text="Description:", anchor="w").grid(
            row=7, column=0, padx=(20, 10), pady=5, sticky="w")
        self.desc_entry = ctk.CTkEntry(self, placeholder_text="Home server")
        self.desc_entry.grid(row=7, column=1, padx=(0, 20), pady=5, sticky="ew")

        # Buttons
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.grid(row=8, column=0, columnspan=2, pady=(20, 15))
        ctk.CTkButton(btn_frame, text="Cancel", width=100,
                       command=self.destroy).pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="Save", width=100,
                       command=self._save, fg_color="#2B5797").pack(side="left", padx=5)

    def _populate(self, server: Server):
        """Fill form with existing server data."""
        self.name_entry.insert(0, server.name)
        self.host_entry.insert(0, server.host)
        self.port_entry.insert(0, str(server.port))
        self.user_entry.insert(0, server.user)
        self.auth_mode.set(server.auth_mode)
        self.key_entry.insert(0, server.ssh_key)
        if server.password:
            self.password_entry.insert(0, server.password)
        self.desc_entry.insert(0, server.description)
        self._on_auth_mode_change(server.auth_mode)

    def _on_auth_mode_change(self, mode: str):
        """Toggle between key and password auth."""
        if mode == "key":
            self.key_entry.configure(state="normal")
            self.browse_btn.configure(state="normal")
            self.password_entry.configure(state="disabled")
        else:
            self.key_entry.configure(state="disabled")
            self.browse_btn.configure(state="disabled")
            self.password_entry.configure(state="normal")

    def _browse_key(self):
        """Open file browser for SSH key selection."""
        from tkinter import filedialog
        path = filedialog.askopenfilename(
            title="Select SSH Private Key",
            filetypes=[("All Files", "*.*"), ("SSH Keys", "*.pem")])
        if path:
            self.key_entry.delete(0, "end")
            self.key_entry.insert(0, path)

    def _save(self):
        """Validate and save the server."""
        name = self.name_entry.get().strip()
        host = self.host_entry.get().strip()

        if not name:
            self._show_error("Server name is required.")
            return
        if not host:
            self._show_error("Host is required.")
            return

        try:
            port = int(self.port_entry.get().strip() or "22")
        except ValueError:
            self._show_error("Port must be a number.")
            return

        server = Server(
            name=name,
            host=host,
            port=port,
            user=self.user_entry.get().strip() or "root",
            auth_mode=self.auth_mode.get(),
            ssh_key=self.key_entry.get().strip(),
            password=self.password_entry.get(),
            description=self.desc_entry.get().strip(),
        )

        app_config.save_server(server)
        self.result = server
        self.destroy()

    def _show_error(self, msg: str):
        """Show error in a label."""
        if hasattr(self, "error_label"):
            self.error_label.destroy()
        self.error_label = ctk.CTkLabel(
            self, text=msg, text_color="red",
            font=ctk.CTkFont(size=11))
        self.error_label.grid(row=9, column=0, columnspan=2, pady=(0, 10))
