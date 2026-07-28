#!/bin/sh
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
export XDG_CACHE_HOME="${REPO_ROOT}/.uv/cache"
export UV_TOOL_DIR="${REPO_ROOT}/.uv/tools"
export UV_PYTHON_INSTALL_DIR="${REPO_ROOT}/.uv/python"
exec "${REPO_ROOT}/.uv/bin/uvx" mcp-server-fetch "$@"
