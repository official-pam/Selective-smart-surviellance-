"""Local, source-specific storage for dashboard restricted-zone drawings."""

import hashlib
import json
from pathlib import Path


def camera_source_id(source: str) -> str:
    """Hash the source string so camera URLs/passwords are not saved in files."""
    return hashlib.sha256(str(source).strip().encode("utf-8")).hexdigest()


def load_zone(source: str, config_path: Path) -> dict | None:
    """Load one source's saved zone, if the local configuration is valid."""
    if not source or not config_path.is_file():
        return None

    try:
        configuration = json.loads(config_path.read_text(encoding="utf-8"))
        zones = configuration.get("zones", {})
        if not isinstance(zones, dict):
            return None
        region = zones.get(camera_source_id(source))
        return region if isinstance(region, dict) else None
    except (OSError, json.JSONDecodeError, AttributeError, TypeError):
        return None


def save_zone(source: str, region: dict, config_path: Path) -> None:
    """Save one zone while preserving other camera zones in the same file."""
    if not source:
        raise ValueError("Connect the camera or video before saving its boundary.")
    if not isinstance(region, dict):
        raise ValueError("The restricted-zone configuration must be a dictionary.")

    zones = {}
    if config_path.is_file():
        try:
            existing = json.loads(config_path.read_text(encoding="utf-8"))
            saved_zones = existing.get("zones", {})
            if isinstance(saved_zones, dict):
                zones.update(saved_zones)
        except (OSError, json.JSONDecodeError, AttributeError):
            pass

    zones[camera_source_id(source)] = region
    config_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = config_path.with_suffix(".tmp")
    temporary_path.write_text(
        json.dumps({"zones": zones}, indent=2),
        encoding="utf-8",
    )
    temporary_path.replace(config_path)


def clear_zone(source: str, config_path: Path) -> None:
    """Remove one source's zone without deleting other saved camera zones."""
    if not source or not config_path.is_file():
        return

    try:
        configuration = json.loads(config_path.read_text(encoding="utf-8"))
        zones = configuration.get("zones", {})
        if not isinstance(zones, dict):
            return

        zones.pop(camera_source_id(source), None)
        if zones:
            temporary_path = config_path.with_suffix(".tmp")
            temporary_path.write_text(
                json.dumps({"zones": zones}, indent=2),
                encoding="utf-8",
            )
            temporary_path.replace(config_path)
        else:
            config_path.unlink()
    except (OSError, json.JSONDecodeError, AttributeError):
        return
