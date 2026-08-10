#!/bin/sh
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
export XDG_CACHE_HOME="${REPO_ROOT}/.uv/cache"
export UV_TOOL_DIR="${REPO_ROOT}/.uv/tools"
export UV_PYTHON_INSTALL_DIR="${REPO_ROOT}/.uv/python"
# readabilipy runs `npm install` for its JS readability extractor; the default
# ~/.npm cache is root-owned on this host (EACCES), so give npm a writable
# per-clone cache and silence its notices (they would corrupt the MCP stdout
# wire if printed). Uncommitted local fix — required for HTML extraction.
export npm_config_cache="${REPO_ROOT}/.uv/npm-cache"
export npm_config_loglevel=silent
exec "${REPO_ROOT}/.uv/bin/uvx" mcp-server-fetch "$@"
