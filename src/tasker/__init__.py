"""tasker — file-based task tracker for git repos."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("mcp-tasker")
except PackageNotFoundError:
    __version__ = "unknown"
