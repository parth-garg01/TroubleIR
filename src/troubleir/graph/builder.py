"""Build a SettingsGraph from the deeplinks catalog for screen hierarchy resolution."""
import json
import re
import os
from typing import Optional

# Screen hierarchy extracted from Samsung Settings structure
SETTINGS_HIERARCHY = {
    "Settings": {
        "Display": {
            "Brightness": {},
            "Adaptive brightness": {},
            "Eye comfort shield": {},
            "Dark mode": {},
            "Night mode": {},
            "Navigation bar": {
                "Button order": {},
                "Gesture sensitivity": {},
            },
            "Screen timeout": {},
            "Screen resolution": {},
            "Motion smoothness": {},
            "Screen zoom": {},
            "Always On Display": {},
            "Screensaver": {},
            "Touch sensitivity": {},
            "Color mode": {},
        },
        "Battery and device care": {
            "Battery": {
                "Battery usage": {},
                "Power saving": {},
                "Ultra power saving": {},
                "Background usage limits": {},
                "Protect battery": {},
                "Wireless PowerShare": {},
                "Adaptive charging": {},
                "More battery settings": {},
            },
            "Storage": {},
            "Memory": {},
            "Device care": {},
        },
        "Connections": {
            "Wi-Fi": {
                "Wi-Fi calling": {},
            },
            "Bluetooth": {},
            "Mobile data": {},
            "Hotspot": {},
            "Airplane mode": {},
            "NFC": {},
            "Location": {
                "Location services": {
                    "Wi-Fi scanning": {},
                },
            },
        },
        "Apps": {
            "App management": {},
            "Default apps": {},
        },
        "General management": {
            "Date and time": {},
            "Reset": {
                "Reset settings": {},
                "Factory data reset": {},
            },
        },
        "Accessibility": {
            "Visibility enhancements": {
                "Extra dim": {},
            },
        },
        "About phone": {
            "Software information": {
                "Build number": {},
            },
        },
        "Advanced features": {
            "Game Booster": {},
        },
        "Sound": {
            "Volume": {},
            "Do Not Disturb": {},
            "Notification sounds": {},
        },
        "Security and privacy": {
            "Biometrics and security": {},
        },
        "Software update": {},
        "Developer options": {
            "Background process limit": {},
            "Window animation scale": {},
            "Transition animation scale": {},
            "Animator duration scale": {},
        },
    }
}


def _flatten_hierarchy(node: dict, path: list[str], result: dict) -> None:
    for name, children in node.items():
        current_path = path + [name]
        result[name.lower()] = current_path
        if children:
            _flatten_hierarchy(children, current_path, result)


def build_screen_index() -> dict[str, list[str]]:
    """Return mapping from screen_name_lower -> full path list."""
    index = {}
    _flatten_hierarchy(SETTINGS_HIERARCHY, [], index)
    return index


_SCREEN_INDEX: dict[str, list[str]] | None = None


def get_screen_index() -> dict[str, list[str]]:
    global _SCREEN_INDEX
    if _SCREEN_INDEX is None:
        _SCREEN_INDEX = build_screen_index()
    return _SCREEN_INDEX


def save_graph(path: str = "data/processed/settings_graph.json") -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump({"hierarchy": SETTINGS_HIERARCHY, "index": get_screen_index()}, f, indent=2)


if __name__ == "__main__":
    save_graph()
    print("SettingsGraph saved.")
