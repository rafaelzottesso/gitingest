"""Configuration for the server."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path

from fastapi.templating import Jinja2Templates

MAX_DISPLAY_SIZE: int = 300_000

# Slider configuration (if updated, update the logSliderToSize function in src/static/js/utils.js)
DEFAULT_FILE_SIZE_KB: int = 5 * 1024  # 5 mb
MAX_FILE_SIZE_KB: int = 100 * 1024  # 100 mb

EXAMPLE_REPOS: list[dict[str, str]] = [
    {"name": "Gitingest", "url": "https://github.com/coderamp-labs/gitingest"},
    {"name": "FastAPI", "url": "https://github.com/fastapi/fastapi"},
    {"name": "Flask", "url": "https://github.com/pallets/flask"},
    {"name": "Excalidraw", "url": "https://github.com/excalidraw/excalidraw"},
    {"name": "ApiAnalytics", "url": "https://github.com/tom-draper/api-analytics"},
]


# Version and repository configuration
APP_REPOSITORY = os.getenv("APP_REPOSITORY", "https://github.com/coderamp-labs/gitingest")
APP_VERSION = os.getenv("APP_VERSION", "unknown")
APP_VERSION_URL = os.getenv("APP_VERSION_URL", "https://github.com/coderamp-labs/gitingest")


def get_version_info() -> dict[str, str]:
    """Get version information including display version and link.

    Returns
    -------
    dict[str, str]
        Dictionary containing 'version' and 'version_link' keys.

    """
    # Use pre-computed values from GitHub Actions
    display_version = APP_VERSION
    version_link = APP_VERSION_URL

    # Fallback to repository root if no URL is provided
    if version_link == APP_REPOSITORY or not version_link:
        version_link = f"{APP_REPOSITORY.rstrip('/')}/tree/main"

    return {
        "version": display_version,
        "version_link": version_link,
    }


# Use absolute path to templates directory
templates_dir = Path(__file__).parent / "templates"
templates = Jinja2Templates(directory=templates_dir)


static_dir = Path(__file__).parent.parent / "static"
_static_hash_cache: dict[str, tuple[float, str]] = {}


def static_url(path: str) -> str:
    """Return a ``/static/...`` URL with a content hash, e.g. ``/static/js/utils.js?v=1a2b3c4d``.

    The hash changes whenever the file changes, so browsers and CDNs download the new version
    automatically while unchanged files stay cached. Hashes are cached per file modification time.
    """
    file_path = static_dir / path
    try:
        mtime = file_path.stat().st_mtime
    except OSError:
        return f"/static/{path}"

    cached = _static_hash_cache.get(path)
    if cached is None or cached[0] != mtime:
        digest = hashlib.md5(file_path.read_bytes(), usedforsecurity=False).hexdigest()[:8]
        cached = (mtime, digest)
        _static_hash_cache[path] = cached

    return f"/static/{path}?v={cached[1]}"


templates.env.globals["static_url"] = static_url
