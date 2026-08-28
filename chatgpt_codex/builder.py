import copy
import json
import os
import platform
import re
from pathlib import Path
from typing import Any, Dict

from .config import AppConfig, DEFAULT_CONFIG_DIR


DEFAULT_GPT_NAME = "Local Coding Bridge"
DEFAULT_GPT_DESCRIPTION = "Access and edit one authorized local workspace through a private bearer-protected Action bridge."
DEFAULT_VISIBILITY = "private"
BUILDER_STATE_FILE = "builder.json"
BUILDER_ROUTE_MAP_FILE = "builder-routes.json"
SECRET_KEYS = {"authorization", "cookie", "set-cookie", "api_key", "token", "password", "secret"}

DEFAULT_SYSTEM_INSTRUCTIONS = """You are my local coding assistant for the workspace exposed through Actions.

Use `getWorkspaceStatus` when I ask about the current project, when the active workspace is ambiguous, before switching projects, or when a workspace-related action fails. Do not treat it as a mandatory preflight before every file, code, or command task.

When I ask to view or switch projects, call `getWorkspaceStatus`, then use `switchWorkspace` only with an authorized workspace name returned by `getWorkspaceStatus`. After switching, briefly state the active workspace name and local path.

At the start of real project work in a workspace, check whether `AGENTS.md` or `AGENTS.override.md` applies at the workspace root. If work moves into a deeper subdirectory, check for deeper-scoped instruction files there. Do not recursively scan the whole repository only to find these files, and do not reread them when the scope has not changed.

For project work, use:
- `listFiles` for shallow discovery.
- `readFile` for one file or a bounded line range.
- `readFiles` for several known files.
- `searchText` for source/text search.
- `writeFile` and `applyPatch` for edits.
- `execCommand` for builds, tests, Git inspection, package scripts, or workflows not efficiently handled by dedicated tools.

Prefer dedicated file/search tools over equivalent shell commands.

When exploring a project, start shallow, read only high-signal files, batch independent reads with `readFiles`, use `searchText` context before another read, and prefer bounded line ranges after locating relevant symbols. Avoid unnecessarily reading or enumerating large parts of the repository.

Inspect the target file and relevant surrounding code before editing. Keep changes scoped and avoid unrelated refactors or formatting churn. Prefer `applyPatch` for targeted edits.

After changes, inspect the modified area and run the narrowest useful validation when appropriate. If a command is taking a while, send me a brief progress update at least every 10 seconds until it finishes.

Treat tool results as the source of truth. If output is truncated, narrow the query instead of assuming the result is complete. When I ask for raw logs, preserve raw stdout/stderr instead of replacing them with a summary.

Do not run destructive or irreversible commands unless I explicitly request that exact action in the current chat."""


def make_builder_payload(config: AppConfig, include_token: bool = False) -> Dict[str, Any]:
    base = config.public_base_url.rstrip("/")
    action = {
        "authentication": {"type": "api_key", "auth_type": "bearer"},
        "schema_import_url": f"{base}/openapi.json",
        "privacy_policy_url": f"{base}/privacy",
        "token_command": "chatgpt-codex token",
    }
    if include_token:
        action["api_key"] = config.token
    return {
        "gpt": {
            "name": DEFAULT_GPT_NAME,
            "description": DEFAULT_GPT_DESCRIPTION,
            "instructions": builder_instructions(),
        },
        "action": action,
        "visibility": DEFAULT_VISIBILITY,
        "workspace": {
            "active_workspace": config.active_workspace,
            "path": str(config.workspace),
            "workspaces": config.workspace_entries(),
        },
        "token_configured": bool(config.token),
        "access": config.access_status(),
        "automation": {
            "primary": "playwright",
            "fallback": "computer-use",
            "submit_modes": ["ui", "hybrid", "api"],
            "profile_path": str(playwright_profile_dir()),
            "route_map_path": str(builder_route_map_path(Path.cwd())),
            "rules": [
                "Use Playwright with a persistent profile by default.",
                "Use internal API replay only inside the same Playwright browser context.",
                "Never print cookies, sessions, bearer tokens, or API keys.",
                "Fallback to Computer Use only when Playwright cannot operate the page.",
            ],
        },
    }


def builder_instructions() -> str:
    return DEFAULT_SYSTEM_INSTRUCTIONS


def builder_state_path(base_dir: Path) -> Path:
    return Path(base_dir) / DEFAULT_CONFIG_DIR / BUILDER_STATE_FILE


def builder_route_map_path(base_dir: Path) -> Path:
    return Path(base_dir) / DEFAULT_CONFIG_DIR / BUILDER_ROUTE_MAP_FILE


def playwright_profile_dir() -> Path:
    override = os.environ.get("CHATGPT_CODEX_PLAYWRIGHT_PROFILE", "").strip()
    if override:
        return Path(override).expanduser()
    system = platform.system().lower()
    if system == "darwin":
        return Path.home() / "Library" / "Application Support" / "chatgpt-codex" / "playwright-profile"
    if system == "windows":
        local_app_data = os.environ.get("LOCALAPPDATA", "")
        base = Path(local_app_data) if local_app_data else Path.home() / "AppData" / "Local"
        return base / "chatgpt-codex" / "playwright-profile"
    state_home = os.environ.get("XDG_STATE_HOME", "")
    base = Path(state_home) if state_home else Path.home() / ".local" / "state"
    return base / "chatgpt-codex" / "playwright-profile"


def redact_secret(value: Any) -> Any:
    if isinstance(value, dict):
        result = {}
        for key, item in value.items():
            if _is_secret_key(str(key)):
                result[key] = "[REDACTED]"
            else:
                result[key] = redact_secret(item)
        return result
    if isinstance(value, list):
        return [redact_secret(item) for item in value]
    if isinstance(value, str):
        parsed = _try_parse_json(value)
        if parsed is not None:
            return json.dumps(redact_secret(parsed), ensure_ascii=False)
        return _redact_secret_text(value)
    return copy.deepcopy(value)


def _is_secret_key(key: str) -> bool:
    lowered = key.lower()
    return lowered in SECRET_KEYS or any(part in lowered for part in ["authorization", "cookie", "api_key", "token", "password", "secret"])


def _try_parse_json(value: str):
    raw = value.strip()
    if not raw or raw[0] not in "[{":
        return None
    try:
        return json.loads(raw)
    except ValueError:
        return None


def _redact_secret_text(value: str) -> str:
    redacted = re.sub(r"Bearer\s+[A-Za-z0-9._~+/=-]+", "Bearer [REDACTED]", value, flags=re.IGNORECASE)
    redacted = re.sub(r"(?i)(session|token|api[_-]?key|password|secret)=([^;&\s]+)", r"\1=[REDACTED]", redacted)
    return redacted
