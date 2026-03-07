"""Theme manager with persistence for deutschbuddy."""

from __future__ import annotations

import json
from pathlib import Path
from platformdirs import user_config_dir

from textual.app import App

from deutschbuddy.themes import ALL_NEON_THEMES, THEME_CHOICES


THEME_CONFIG_DIR = Path(user_config_dir("deutschbuddy"))
THEME_CONFIG_FILE = THEME_CONFIG_DIR / "theme.json"

DEFAULT_THEME = "neon_cyberpunk"


def get_theme_config_path() -> Path:
    """Get the path to the theme configuration file."""
    return THEME_CONFIG_FILE


def load_saved_theme() -> str:
    """Load the saved theme name from config file.

    Returns:
        The saved theme name, or DEFAULT_THEME if no theme is saved.
    """
    config_path = get_theme_config_path()
    if not config_path.exists():
        return DEFAULT_THEME

    try:
        data = json.loads(config_path.read_text(encoding="utf-8"))
        return data.get("theme", DEFAULT_THEME)
    except (json.JSONDecodeError, OSError):
        return DEFAULT_THEME


def save_theme(theme_name: str) -> None:
    """Save the theme name to config file.

    Args:
        theme_name: The name of the theme to save.
    """
    THEME_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    config_path = get_theme_config_path()
    config_path.write_text(
        json.dumps({"theme": theme_name}, indent=2), encoding="utf-8"
    )


def register_neon_themes(app: App) -> None:
    """Register all neon themes with the application.

    Args:
        app: The Textual application instance.
    """
    for theme in ALL_NEON_THEMES:
        app.register_theme(theme)


def apply_theme(app: App, theme_name: str) -> None:
    """Apply a theme to the application and save it.

    Args:
        app: The Textual application instance.
        theme_name: The name of the theme to apply.
    """
    if theme_name in app.available_themes:
        app.theme = theme_name
        save_theme(theme_name)


def get_theme_choices() -> dict[str, str]:
    """Get available theme choices for UI selection.

    Returns:
        Dictionary mapping theme names to display names.
    """
    return THEME_CHOICES
