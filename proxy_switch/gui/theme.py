"""Theme configuration for the Proxy-Switch GUI.

Uses CustomTkinter's built-in theme system with custom color overrides.
"""

import customtkinter as ctk

# ── Color Palette ───────────────────────────────────────────────────────

class Colors:
    """Central color definitions."""
    PRIMARY = "#2B5797"       # Deep blue - main accent
    PRIMARY_HOVER = "#1A3F73"
    SUCCESS = "#2E7D32"       # Green - enabled/proxy active
    SUCCESS_BG = "#E8F5E9"    # Light green background
    DANGER = "#C62828"        # Red - error/disconnected
    WARNING = "#F57F17"       # Amber - warning
    DISABLED = "#9E9E9E"     # Gray - not installed
    BG_LIGHT = "#F5F5F5"
    BG_DARK = "#2B2B2B"
    TEXT_PRIMARY = "#212121"
    TEXT_SECONDARY = "#757575"
    CARD_BG = "#FFFFFF"
    CARD_BORDER = "#E0E0E0"


# ── Apply Theme ─────────────────────────────────────────────────────────

def setup_theme():
    """Configure the CustomTkinter appearance."""
    ctk.set_appearance_mode("system")  # Auto: light/dark based on system
    ctk.set_default_color_theme("blue")

    # Custom theme colors
    ctk.ThemeManager.theme["color_phase"] = {
        "phase1": Colors.PRIMARY,
        "phase2": Colors.SUCCESS,
    }


# ── Fonts ───────────────────────────────────────────────────────────────

def font_heading():
    """Heading font for section titles."""
    return ctk.CTkFont(size=16, weight="bold")


def font_subheading():
    """Sub-heading font."""
    return ctk.CTkFont(size=13, weight="bold")


def font_body():
    """Body text font."""
    return ctk.CTkFont(size=13)


def font_small():
    """Small/caption font."""
    return ctk.CTkFont(size=11)


def font_mono():
    """Monospace font for log output."""
    return ctk.CTkFont(size=12, family="Consolas")
