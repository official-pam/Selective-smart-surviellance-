"""Paths for local-only surveillance data."""

import os
from pathlib import Path


def get_private_data_directory(project_root=None):
    """Return a writable, per-user directory for biometric and event data.

    SELECTIVE_SURVEILLANCE_DATA_DIR can override the default when an operator
    wants to keep the data on another local disk. On Windows, the default is
    under Local AppData; on macOS and Linux it is under the user's data folder.
    """
    configured_path = os.environ.get("SELECTIVE_SURVEILLANCE_DATA_DIR")
    if configured_path:
        data_directory = Path(configured_path).expanduser()
    else:
        if os.name == "nt" and os.environ.get("LOCALAPPDATA"):
            data_directory = (
                Path(os.environ["LOCALAPPDATA"])
                / "SelectiveSmartSurveillance"
            )
        elif os.name == "darwin":
            data_directory = (
                Path.home()
                / "Library"
                / "Application Support"
                / "SelectiveSmartSurveillance"
            )
        else:
            data_directory = (
                Path.home()
                / ".local"
                / "share"
                / "selective-smart-surveillance"
            )

    try:
        data_directory.mkdir(parents=True, exist_ok=True)
        return data_directory
    except OSError:
        # Some managed or protected Windows environments block Local AppData.
        # Keep a local-only fallback beside the project instead of failing app startup.
        if configured_path:
            raise
        if project_root is None:
            raise
        fallback_directory = Path(project_root) / "runtime_data"
        fallback_directory.mkdir(parents=True, exist_ok=True)
        return fallback_directory
