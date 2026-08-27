import argparse
import json
import os
import platform
import shutil
import subprocess
import sys
import tempfile
import threading
import webbrowser
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import ProxyHandler, Request, build_opener

from .builder import (
    builder_route_map_path,
    builder_state_path,
    make_builder_payload,
    playwright_profile_dir,
)
from .config import (
    ACCESS_PLANS,
    AppConfig,
    SetupPermissions,
    config_path,
    load_config,
    load_permissions,
    permissions_path,
    save_config,
    save_permissions,
)
from .openapi import make_openapi_document
from .security import generate_token
from .server import create_server


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="chatgpt-codex",
        description="Local coding bridge for ChatGPT Custom GPT Actions. / ChatGPT Custom GPT Actions 的本地编程桥。",
    )
    parser.add_argument("--config", default=None, help="Path to config.json. / config.json 路径。Defaults to .chatgpt-codex/config.json.")
    parser.add_argument("--lang", choices=["auto", "en", "zh"], default="auto", help="CLI language: auto, en, or zh. / 命令行语言：auto、en 或 zh。")
    subcommands = parser.add_subparsers(dest="command", required=True)

    init_parser = subcommands.add_parser("init", help="Create a local config file. / 创建本地配置文件。")
    init_parser.add_argument("--workspace", default=".", help="Workspace ChatGPT may access. / ChatGPT 可访问的工作区。")
    init_parser.add_argument("--workspace-name", default="", help="Name for this workspace. / 这个工作区的名称。")
    init_parser.add_argument("--public-base-url", default="https://example.com", help="Public HTTPS base URL. / 公网 HTTPS 根地址。")
    init_parser.add_argument("--host", default="127.0.0.1")
    init_parser.add_argument("--port", type=int, default=8766)
    init_parser.add_argument("--force", action="store_true")

    subcommands.add_parser("doctor", help="Check local prerequisites. / 检查本地环境。")
    subcommands.add_parser("status", help="Print machine-readable AI-native local status. / 打印机器可读的 AI-native 本地状态。")
    subcommands.add_parser("ai-commands", help="Print machine-readable AI-native command catalog. / 打印机器可读的 AI-native 命令目录。")
    subcommands.add_parser("token", help="Print the configured bearer token. / 打印已配置的 bearer token。")
    subcommands.add_parser("openapi", help="Print the OpenAPI document. / 打印 OpenAPI 文档。")
    subcommands.add_parser("gpt-instructions", help="Print Custom GPT setup instructions. / 打印 Custom GPT 配置说明。")
    subcommands.add_parser("route-options", help="Explain HTTPS route choices. / 说明 HTTPS 入口选项。")
    subcommands.add_parser("chatgpt-preflight", help="Print ChatGPT Builder prerequisites and setup boundaries. / 打印 ChatGPT Builder 前提条件和自动化边界。")
    public_url_parser = subcommands.add_parser("set-public-url", help="Update public_base_url without changing token or workspaces. / 只更新 public_base_url，不改变 token 或工作区。")
    public_url_parser.add_argument("url", help="Public HTTPS base URL. / 公网 HTTPS 根地址。")
    rotate_parser = subcommands.add_parser("rotate-token", help="Rotate the bearer token and print the new token once. / 轮换 bearer token 并只打印一次新 token。")
    rotate_parser.add_argument("--ttl-minutes", type=int, default=0, help="Optional access session TTL to set while rotating. / 轮换时可选设置访问会话分钟数。")
    verify_parser = subcommands.add_parser("verify", help="Verify health, schema, and one authenticated read-only action. / 验证健康检查、schema 和一个带鉴权只读 Action。")
    verify_parser.add_argument("--base-url", default="", help="Override base URL for verification. / 覆盖验证用根地址。")
    verify_parser.add_argument("--timeout", type=int, default=10, help="Request timeout seconds. / 请求超时秒数。")
    api_smoke_parser = subcommands.add_parser("api-smoke", help="Run an interface-level smoke test in temporary workspaces. / 在临时工作区运行接口级冒烟测试。")
    api_smoke_parser.add_argument("--timeout", type=int, default=10, help="Request timeout seconds. / 请求超时秒数。")
    subcommands.add_parser("permissions", help="Print saved setup permissions. / 打印已保存的配置授权。")
    template_parser = subcommands.add_parser("permissions-template", help="Print or write a permissions template. / 打印或写入授权模板。")
    template_parser.add_argument("--output", default="", help="Optional output path. / 可选输出路径。")
    template_parser.add_argument("--force", action="store_true")
    subcommands.add_parser("open-chatgpt-login", help="Open ChatGPT login/home in the browser. / 在浏览器打开 ChatGPT 登录或首页。")
    subcommands.add_parser("open-chatgpt", help="Open ChatGPT Builder in the browser. / 在浏览器打开 ChatGPT Builder。")
    subcommands.add_parser("agent-brief", help="Print AI-native setup handoff for Codex or Claude. / 打印给 Codex 或 Claude 的自动配置说明。")
    subcommands.add_parser("ai-native", help="Alias of agent-brief. / agent-brief 的别名。")
    subcommands.add_parser("skills", help="Print the bundled skill handoff. / 打印内置 skill 交接说明。")
    subcommands.add_parser("skill", help="Alias of skills. / skills 的别名。")

    builder_parser = subcommands.add_parser("builder", help="Automate ChatGPT Builder with Playwright. / 使用 Playwright 自动化 ChatGPT Builder。")
    builder_subcommands = builder_parser.add_subparsers(dest="builder_command", required=True)
    builder_payload = builder_subcommands.add_parser("payload", help="Print Builder fields without leaking token. / 打印 Builder 字段但不泄露 token。")
    builder_payload.add_argument("--json", action="store_true", help="Print JSON output. / 输出 JSON。")
    builder_subcommands.add_parser("profile-path", help="Print the persistent Playwright profile path. / 打印持久化 Playwright profile 路径。")
    builder_open_login = builder_subcommands.add_parser("open-login", help="Open ChatGPT login in Playwright. / 用 Playwright 打开 ChatGPT 登录。")
    builder_open_login.add_argument("--dry-run", action="store_true")
    builder_doctor = builder_subcommands.add_parser("doctor", help="Check ChatGPT Builder readiness through Playwright. / 通过 Playwright 检查 Builder 就绪状态。")
    builder_doctor.add_argument("--dry-run", action="store_true")
    builder_sniff = builder_subcommands.add_parser("sniff", help="Sniff Builder internal API routes in the current Playwright session. / 在当前 Playwright 会话中嗅探 Builder 内部接口。")
    builder_sniff.add_argument("--dry-run", action="store_true")
    builder_sniff.add_argument("--output", default="", help="Route map output path. / route map 输出路径。")
    builder_configure = builder_subcommands.add_parser("configure", help="Configure the GPT Builder using UI, hybrid, or API mode. / 使用 UI、hybrid 或 API 模式配置 GPT Builder。")
    builder_configure.add_argument("--mode", choices=["ui", "hybrid", "api"], default="ui")
    builder_configure.add_argument("--visibility", choices=["private", "link", "store"], default="private")
    builder_configure.add_argument("--dry-run", action="store_true")
    builder_smoke = builder_subcommands.add_parser("smoke", help="Run a real GPT Action smoke test through ChatGPT. / 通过 ChatGPT 运行真实 GPT Action 冒烟测试。")
    builder_smoke.add_argument("--dry-run", action="store_true")

    serve_parser = subcommands.add_parser("serve", help="Start the local HTTP action server. / 启动本地 HTTP Action 服务。")
    serve_parser.add_argument("--host", default=None)
    serve_parser.add_argument("--port", type=int, default=None)
    serve_parser.add_argument("--ttl-minutes", type=int, default=0, help="Set an access expiry when starting the server. / 启动服务时设置访问过期分钟数。")

    channel_parser = subcommands.add_parser("channel", help="Register, renew, revoke, or inspect the ChatGPT Action channel. / 注册、续期、撤销或查看 ChatGPT Action 通道。")
    channel_subcommands = channel_parser.add_subparsers(dest="channel_command", required=True)
    channel_status = channel_subcommands.add_parser("status", help="Show channel status without printing the token. / 显示通道状态，不打印 token。")
    channel_status.add_argument("--show-paths", action="store_true", help="Include storage paths. / 显示存储路径。")
    channel_register = channel_subcommands.add_parser("register", help="Create the channel config for one machine and one authorized workspace. / 为当前机器和一个授权工作区创建通道配置。")
    channel_register.add_argument("--workspace", required=True, help="Workspace ChatGPT may access. / ChatGPT 可访问的工作区。")
    channel_register.add_argument("--workspace-name", default="", help="Name for this workspace. / 这个工作区的名称。")
    channel_register.add_argument("--public-base-url", required=True, help="Public HTTPS base URL. / 公网 HTTPS 根地址。")
    channel_register.add_argument("--host", default="127.0.0.1")
    channel_register.add_argument("--port", type=int, default=8766)
    channel_register.add_argument("--ttl-minutes", type=int, default=0, help="Optional short-lived access TTL. / 可选短时访问分钟数。")
    channel_register.add_argument("--force", action="store_true")
    channel_renew = channel_subcommands.add_parser("renew", help="Reactivate the channel and print the current token for Builder. / 重新激活通道并打印当前 Builder token。")
    channel_renew.add_argument("--public-base-url", default="", help="Optional updated public HTTPS base URL. / 可选更新公网 HTTPS 根地址。")
    channel_renew.add_argument("--ttl-minutes", type=int, default=0, help="Optional short-lived access TTL. Without it, access has no expiry. / 可选短时访问分钟数；不提供则不过期。")
    channel_renew.add_argument("--rotate-token", action="store_true", help="Rotate token before renewing. / 续期前轮换 token。")
    channel_subcommands.add_parser("revoke", help="Immediately disable the channel and rotate token without printing it. / 立即停用通道并轮换 token 但不打印。")

    access_parser = subcommands.add_parser("access", help="Manage access session expiry. / 管理访问会话过期时间。")
    access_subcommands = access_parser.add_subparsers(dest="access_command", required=True)
    access_subcommands.add_parser("status", help="Show access session status without printing the token. / 显示访问会话状态，不打印 token。")
    access_grant = access_subcommands.add_parser("grant", help="Grant access for a fixed number of minutes. / 授权固定分钟数访问。")
    access_grant.add_argument("--ttl-minutes", type=int, required=True, help="Access lifetime in minutes. / 访问有效分钟数。")
    access_grant.add_argument("--rotate-token", action="store_true", help="Rotate token while granting access. / 授权时同时轮换 token。")
    access_subcommands.add_parser("revoke", help="Expire access immediately and rotate the token. / 立即过期访问并轮换 token。")

    workspace_parser = subcommands.add_parser("workspace", help="Manage authorized workspaces. / 管理已授权工作区。")
    workspace_subcommands = workspace_parser.add_subparsers(dest="workspace_command", required=True)
    workspace_subcommands.add_parser("status", help="Show active workspace. / 显示当前工作区。")
    workspace_subcommands.add_parser("list", help="List authorized workspaces. / 列出已授权工作区。")
    workspace_add = workspace_subcommands.add_parser("add", help="Add an authorized workspace. / 添加已授权工作区。")
    workspace_add.add_argument("--name", required=True, help="Workspace name used in ChatGPT. / ChatGPT 中使用的工作区名称。")
    workspace_add.add_argument("--path", required=True, help="Absolute or relative local path. / 本地路径。")
    workspace_add.add_argument("--activate", action="store_true", help="Make it the active workspace now. / 立即切换为当前工作区。")
    workspace_switch = workspace_subcommands.add_parser("switch", help="Switch active workspace. / 切换当前工作区。")
    workspace_switch.add_argument("name", help="Workspace name. / 工作区名称。")

    tunnel_parser = subcommands.add_parser("tunnel", help="Start the built-in cloudflared tunnel to the local server. / 启动内置 cloudflared 隧道。")
    tunnel_parser.add_argument("--cloudflared", default="cloudflared")

    authorize_parser = subcommands.add_parser("authorize", help="Save setup choices and permissions. / 保存配置选项和授权。")
    authorize_parser.add_argument("--workspace", default=".", help="Workspace ChatGPT may access. / ChatGPT 可访问的工作区。")
    authorize_parser.add_argument("--operating-system", choices=["auto", "macos", "windows"], default="auto")
    authorize_parser.add_argument("--access-plan", choices=sorted(ACCESS_PLANS), default="local-only")
    authorize_parser.add_argument("--public-base-url", default="https://example.com")
    authorize_parser.add_argument("--hostname", default="")
    authorize_parser.add_argument("--allow-browser-automation", action="store_true")
    authorize_parser.add_argument("--allow-start-services", action="store_true")
    authorize_parser.add_argument("--allow-install-helpers", action="store_true")
    authorize_parser.add_argument("--allow-workspace-write", action="store_true")
    authorize_parser.add_argument("--allow-command-execution", action="store_true")
    authorize_parser.add_argument("--force", action="store_true")

    args = parser.parse_args(argv)
    language = _resolve_language(args.lang)
    cfg_path = Path(args.config).expanduser() if args.config else config_path(Path.cwd())

    if args.command == "init":
        workspace_path = Path(args.workspace).expanduser().resolve()
        workspace_name = args.workspace_name or workspace_path.name or "default"
        config = AppConfig(
            token=AppConfig.default(workspace_path).token,
            workspaces={workspace_name: workspace_path},
            active_workspace=workspace_name,
            host=args.host,
            port=args.port,
            public_base_url=args.public_base_url.rstrip("/"),
        )
        save_config(config, cfg_path, overwrite=args.force)
        print(f"Config written / 配置已写入: {cfg_path}")
        print("Keep this bearer token private / 请妥善保管此 bearer token:")
        print(config.token)
        return 0

    if args.command in {"agent-brief", "ai-native", "skills", "skill"}:
        print(_agent_brief())
        return 0
    if args.command == "builder" and args.builder_command == "profile-path":
        print(playwright_profile_dir())
        return 0
    if args.command == "status":
        print(json.dumps(_management_status(cfg_path, language), indent=2, ensure_ascii=False))
        return 0
    if args.command == "ai-commands":
        print(json.dumps(_ai_command_catalog(), indent=2, ensure_ascii=False))
        return 0
    if args.command == "route-options":
        print(_route_options())
        return 0
    if args.command == "chatgpt-preflight":
        print(json.dumps(_chatgpt_preflight(cfg_path, language), indent=2, ensure_ascii=False))
        return 0
    if args.command == "open-chatgpt-login":
        url = "https://chatgpt.com/"
        opened = _open_chrome_or_default(url)
        if opened:
            print(f"Opened ChatGPT login/home / 已打开 ChatGPT 登录或首页: {url}")
        else:
            print(f"Failed to open ChatGPT login/home / 打开 ChatGPT 登录或首页失败: {url}", file=sys.stderr)
        return 0 if opened else 1
    if args.command == "open-chatgpt":
        url = "https://chatgpt.com/gpts/editor"
        opened = _open_chrome_or_default(url)
        if opened:
            print(f"Opened ChatGPT Builder / 已打开 ChatGPT Builder: {url}")
        else:
            print(f"Failed to open ChatGPT Builder / 打开 ChatGPT Builder 失败: {url}", file=sys.stderr)
        return 0 if opened else 1
    if args.command == "authorize":
        perm_path = permissions_path(Path.cwd())
        permissions = SetupPermissions.create(
            workspace=Path(args.workspace),
            operating_system=_selected_os(args.operating_system),
            access_plan=args.access_plan,
            public_base_url=args.public_base_url,
            allow_browser_automation=args.allow_browser_automation,
            allow_start_services=args.allow_start_services,
            allow_install_helpers=args.allow_install_helpers,
            allow_workspace_write=args.allow_workspace_write,
            allow_command_execution=args.allow_command_execution,
            hostname=args.hostname,
        )
        save_permissions(permissions, perm_path, overwrite=args.force)
        print(f"Permissions written / 授权已写入: {perm_path}")
        print(_access_plan_summary(args.access_plan))
        return 0
    if args.command == "permissions":
        try:
            permissions = load_permissions(permissions_path(Path.cwd()))
        except FileNotFoundError:
            print("No saved permissions. Run `chatgpt-codex authorize` first. / 未找到已保存授权，请先运行 `chatgpt-codex authorize`。", file=sys.stderr)
            return 1
        print(json.dumps(permissions.to_dict(), indent=2, ensure_ascii=False))
        return 0
    if args.command == "permissions-template":
        template = _permissions_template()
        if args.output:
            target = Path(args.output).expanduser()
            if target.exists() and not args.force:
                print(f"Template already exists / 模板已存在: {target}", file=sys.stderr)
                return 1
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open("w", encoding="utf-8") as handle:
                json.dump(template, handle, indent=2, ensure_ascii=False)
                handle.write("\n")
            print(f"Template written / 模板已写入: {target}")
            return 0
        print(json.dumps(template, indent=2, ensure_ascii=False))
        return 0
    if args.command == "api-smoke":
        result = _api_smoke(args.timeout)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0 if result["ok"] else 1
    if args.command == "channel":
        if args.channel_command == "status":
            print(json.dumps(_channel_status(cfg_path, include_paths=args.show_paths), indent=2, ensure_ascii=False))
            return 0
        if args.channel_command == "register":
            return _channel_register(args, cfg_path)
    if args.command == "doctor" and not cfg_path.exists():
        return _doctor_missing_config(cfg_path)

    config = load_config(cfg_path)

    if args.command == "builder":
        return _builder_command(args, config, cfg_path)
    if args.command == "doctor":
        return _doctor(config)
    if args.command == "token":
        print(config.token)
        return 0
    if args.command == "openapi":
        print(json.dumps(make_openapi_document(config.public_base_url), indent=2, ensure_ascii=False))
        return 0
    if args.command == "gpt-instructions":
        print(_gpt_instructions(config))
        return 0
    if args.command == "set-public-url":
        config.public_base_url = args.url.rstrip("/")
        save_config(config, cfg_path, overwrite=True)
        print(json.dumps({"public_base_url": config.public_base_url}, indent=2, ensure_ascii=False))
        return 0
    if args.command == "rotate-token":
        config.token = generate_token()
        if args.ttl_minutes:
            config.grant_access(args.ttl_minutes)
        save_config(config, cfg_path, overwrite=True)
        print(json.dumps({"token": config.token, "access": config.access_status()}, indent=2, ensure_ascii=False))
        return 0
    if args.command == "verify":
        result = _verify_actions(config, args.base_url or config.public_base_url, args.timeout)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0 if result["ok"] else 1
    if args.command == "access":
        return _access_command(args, config, cfg_path)
    if args.command == "channel":
        return _channel_command(args, config, cfg_path)
    if args.command == "workspace":
        return _workspace_command(args, config, cfg_path)
    if args.command == "serve":
        if args.host:
            config.host = args.host
        if args.port:
            config.port = args.port
        if args.ttl_minutes:
            config.grant_access(args.ttl_minutes)
            save_config(config, cfg_path, overwrite=True)
        server = create_server(config, cfg_path)
        print(f"Serving / 正在服务 {config.active_workspace}:{config.workspace} at http://{config.host}:{server.server_port}")
        print(f"OpenAPI: {config.public_base_url.rstrip('/')}/openapi.json")
        print(f"Access / 访问会话: {json.dumps(config.access_status(), ensure_ascii=False)}")
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print("\nStopped / 已停止。")
        return 0
    if args.command == "tunnel":
        local_url = f"http://{config.host}:{config.port}"
        cloudflared = shutil.which(args.cloudflared)
        if not cloudflared:
            print("cloudflared not found in PATH. Install it to use this tunnel command, or provide your own public HTTPS route. / PATH 中找不到 cloudflared；如需使用此 tunnel 命令请先安装，或自行提供公网 HTTPS 入口。", file=sys.stderr)
            return 1
        return subprocess.call([cloudflared, "tunnel", "--url", local_url])

    parser.error(f"unknown command: {args.command}")
    return 2


def _doctor(config: AppConfig) -> int:
    ok = True
    print(f"OS / 操作系统: {_platform_label()}")
    print(f"Active workspace / 当前工作区: {config.active_workspace}")
    print(f"Workspace path / 工作区路径: {config.workspace}")
    if not config.workspace.exists():
        print("  FAIL workspace does not exist / 工作区不存在")
        ok = False
    else:
        print("  OK workspace exists / 工作区存在")
    print(f"Authorized workspaces / 已授权工作区: {len(config.workspaces)}")
    print(f"Local server / 本地服务: http://{config.host}:{config.port}")
    print(f"Public base URL / 公网根地址: {config.public_base_url}")
    print(f"Bearer token / Bearer token: {'OK set / 已设置' if config.token else 'FAIL missing / 缺失'}")
    access = config.access_status()
    print(f"Access session / 访问会话: {access['mode']}, active={access['active']}, expires_at={access['expires_at'] or 'not set / 未设置'}")
    if not config.token:
        ok = False
    if not access["active"]:
        ok = False
    print(f"cloudflared: {'OK found / 已找到' if shutil.which('cloudflared') else 'OPTIONAL missing / 可选，未找到，仅 tunnel 命令需要'}")
    return 0 if ok else 1


def _doctor_missing_config(cfg_path: Path) -> int:
    print(f"OS / 操作系统: {_platform_label()}")
    print(f"Config / 配置文件: {cfg_path}")
    print("  FAIL config is missing / 配置不存在")
    print("Next / 下一步:")
    print("  chatgpt-codex channel register --workspace /absolute/path/to/project --public-base-url https://actions.example.com")
    return 1


def _resolve_language(value: str = "auto") -> str:
    requested = (value or "auto").lower()
    if requested in {"en", "zh"}:
        return requested
    env_value = os.environ.get("CHATGPT_CODEX_LANG", "").lower()
    if env_value in {"en", "zh"}:
        return env_value
    locale_value = (os.environ.get("LC_ALL") or os.environ.get("LC_MESSAGES") or os.environ.get("LANG") or "").lower()
    return "zh" if locale_value.startswith("zh") else "en"


def _language_examples() -> list:
    return [
        "chatgpt-codex --lang en status",
        "chatgpt-codex --lang zh status",
        "CHATGPT_CODEX_LANG=en chatgpt-codex status",
        "CHATGPT_CODEX_LANG=zh chatgpt-codex status",
    ]


def _management_status(cfg_path: Path, language: str = "en") -> dict:
    permissions_file = permissions_path(Path.cwd())
    result = {
        "language": language,
        "language_examples": _language_examples(),
        "config_path": str(cfg_path),
        "config_exists": cfg_path.exists(),
        "permissions_path": str(permissions_file),
        "permissions_exists": permissions_file.exists(),
        "os": _platform_label(),
        "cloudflared_found": bool(shutil.which("cloudflared")),
        "node_found": bool(shutil.which("node")),
        "npx_found": bool(shutil.which("npx")),
        "builder_profile_path": str(playwright_profile_dir()),
        "configured": False,
    }
    if cfg_path.exists():
        config = load_config(cfg_path)
        result.update(
            {
                "configured": True,
                "active_workspace": config.active_workspace,
                "workspace": str(config.workspace),
                "workspaces": config.workspace_entries(),
                "local_server": f"http://{config.host}:{config.port}",
                "public_base_url": config.public_base_url,
                "openapi_url": f"{config.public_base_url.rstrip('/')}/openapi.json",
                "privacy_url": f"{config.public_base_url.rstrip('/')}/privacy",
                "token_configured": bool(config.token),
                "access": config.access_status(),
            }
        )
    if permissions_file.exists():
        permissions = load_permissions(permissions_file)
        result["permissions"] = {
            "workspace": str(permissions.workspace),
            "operating_system": permissions.operating_system,
            "access_plan": permissions.access_plan,
            "public_base_url": permissions.public_base_url,
            "allow_browser_automation": permissions.allow_browser_automation,
            "allow_start_services": permissions.allow_start_services,
            "allow_install_helpers": permissions.allow_install_helpers,
            "allow_workspace_write": permissions.allow_workspace_write,
            "allow_command_execution": permissions.allow_command_execution,
            "hostname": permissions.hostname,
        }
    return result


def _ai_command_catalog() -> dict:
    return {
        "language": [
            "chatgpt-codex --lang en <command>",
            "chatgpt-codex --lang zh <command>",
            "CHATGPT_CODEX_LANG=en chatgpt-codex <command>",
            "CHATGPT_CODEX_LANG=zh chatgpt-codex <command>",
        ],
        "setup": [
            "chatgpt-codex channel register --workspace <path> --public-base-url <url>",
            "chatgpt-codex init --workspace <path> --workspace-name <name> --public-base-url <url>",
            "chatgpt-codex authorize --workspace <path> --operating-system auto --access-plan <plan> --public-base-url <url>",
            "chatgpt-codex permissions-template --output .chatgpt-codex/permissions.json",
            "chatgpt-codex rotate-token --ttl-minutes <minutes>",
        ],
        "inspect": [
            "chatgpt-codex status",
            "chatgpt-codex doctor",
            "chatgpt-codex access status",
            "chatgpt-codex verify",
            "chatgpt-codex verify --base-url <url>",
            "chatgpt-codex api-smoke",
            "chatgpt-codex route-options",
            "chatgpt-codex workspace status",
            "chatgpt-codex workspace list",
            "chatgpt-codex channel status",
            "chatgpt-codex channel status --show-paths",
        ],
        "routing": [
            "chatgpt-codex set-public-url <url>",
        ],
        "workspace": [
            "chatgpt-codex workspace add --name <name> --path <path>",
            "chatgpt-codex workspace add --name <name> --path <path> --activate",
            "chatgpt-codex workspace switch <name>",
        ],
        "chatgpt_builder": [
            "chatgpt-codex chatgpt-preflight",
            "chatgpt-codex builder payload --json",
            "chatgpt-codex builder open-login",
            "chatgpt-codex builder doctor",
            "chatgpt-codex builder sniff",
            "chatgpt-codex builder configure --mode ui",
            "chatgpt-codex builder configure --mode hybrid",
            "chatgpt-codex builder configure --mode api",
            "chatgpt-codex builder smoke",
            "chatgpt-codex open-chatgpt-login",
            "chatgpt-codex gpt-instructions",
            "chatgpt-codex openapi",
            "chatgpt-codex token",
            "chatgpt-codex open-chatgpt",
        ],
        "runtime": [
            "chatgpt-codex serve",
            "chatgpt-codex serve --ttl-minutes <minutes>",
            "chatgpt-codex tunnel",
        ],
        "access": [
            "chatgpt-codex channel renew",
            "chatgpt-codex channel renew --public-base-url <url>",
            "chatgpt-codex channel renew --ttl-minutes <minutes>",
            "chatgpt-codex channel revoke",
            "chatgpt-codex access grant --ttl-minutes <minutes>",
            "chatgpt-codex access grant --ttl-minutes <minutes> --rotate-token",
            "chatgpt-codex access revoke",
            "chatgpt-codex rotate-token",
        ],
        "notes": [
            "status and ai-commands are machine-readable JSON",
            "status reports token_configured but never prints the bearer token",
            "normal personal-use access does not expire unless a TTL is explicitly set",
            "channel status never prints the bearer token",
            "channel register and channel renew print a bearer token for ChatGPT Builder",
            "channel revoke expires the current session and rotates the token without printing it",
            "workspace switching is limited to registered workspace names",
        ],
    }


def _channel_register(args, cfg_path: Path) -> int:
    workspace_path = Path(args.workspace).expanduser().resolve()
    workspace_name = args.workspace_name or workspace_path.name or "default"
    config = AppConfig(
        token=generate_token(),
        workspaces={workspace_name: workspace_path},
        active_workspace=workspace_name,
        host=args.host,
        port=args.port,
        public_base_url=args.public_base_url.rstrip("/"),
    )
    if args.ttl_minutes:
        config.grant_access(args.ttl_minutes)
    save_config(config, cfg_path, overwrite=args.force)
    print(json.dumps(_channel_payload(config, cfg_path, include_token=True), indent=2, ensure_ascii=False))
    return 0


def _channel_command(args, config: AppConfig, cfg_path: Path) -> int:
    if args.channel_command == "renew":
        if args.public_base_url:
            config.public_base_url = args.public_base_url.rstrip("/")
        if args.rotate_token:
            config.token = generate_token()
        if args.ttl_minutes:
            config.grant_access(args.ttl_minutes)
        else:
            config.access_expires_at = ""
        save_config(config, cfg_path, overwrite=True)
        print(json.dumps(_channel_payload(config, cfg_path, include_token=True), indent=2, ensure_ascii=False))
        return 0
    if args.channel_command == "revoke":
        access = config.revoke_access()
        config.token = generate_token()
        save_config(config, cfg_path, overwrite=True)
        print(
            json.dumps(
                {
                    "registered": True,
                    "active": False,
                    "config_path": str(cfg_path),
                    "public_base_url": config.public_base_url.rstrip("/"),
                    "active_workspace": config.active_workspace,
                    "workspace": str(config.workspace),
                    "access": access,
                    "token_rotated": True,
                },
                indent=2,
                ensure_ascii=False,
            )
        )
        return 0
    return 2


def _channel_status(cfg_path: Path, include_paths: bool = False) -> dict:
    if not cfg_path.exists():
        result = {"registered": False, "token_configured": False}
        if include_paths:
            result["config_path"] = str(cfg_path)
        return result
    config = load_config(cfg_path)
    result = {
        "registered": True,
        "active": bool(config.access_status()["active"]),
        "public_base_url": config.public_base_url.rstrip("/"),
        "openapi_url": f"{config.public_base_url.rstrip('/')}/openapi.json",
        "active_workspace": config.active_workspace,
        "workspace": str(config.workspace),
        "token_configured": bool(config.token),
        "access": config.access_status(),
    }
    if include_paths:
        result["config_path"] = str(cfg_path)
        result["storage"] = "local .chatgpt-codex/config.json, ignored by Git and chmod 600 on macOS/Linux"
    return result


def _channel_payload(config: AppConfig, cfg_path: Path, include_token: bool = False) -> dict:
    payload = {
        "registered": True,
        "active": bool(config.access_status()["active"]),
        "config_path": str(cfg_path),
        "public_base_url": config.public_base_url.rstrip("/"),
        "openapi_url": f"{config.public_base_url.rstrip('/')}/openapi.json",
        "active_workspace": config.active_workspace,
        "workspace": str(config.workspace),
        "access": config.access_status(),
        "token_configured": bool(config.token),
        "storage": "local .chatgpt-codex/config.json, ignored by Git and chmod 600 on macOS/Linux",
    }
    if include_token:
        payload["token"] = config.token
    return payload


def _access_command(args, config: AppConfig, cfg_path: Path) -> int:
    if args.access_command == "status":
        print(json.dumps(config.access_status(), indent=2, ensure_ascii=False))
        return 0
    if args.access_command == "grant":
        if args.rotate_token:
            config.token = generate_token()
        access = config.grant_access(args.ttl_minutes)
        save_config(config, cfg_path, overwrite=True)
        result = {"access": access, "token_rotated": bool(args.rotate_token)}
        if args.rotate_token:
            result["token"] = config.token
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0
    if args.access_command == "revoke":
        access = config.revoke_access()
        config.token = generate_token()
        save_config(config, cfg_path, overwrite=True)
        print(json.dumps({"access": access, "token_rotated": True}, indent=2, ensure_ascii=False))
        return 0
    return 2


def _workspace_command(args, config: AppConfig, cfg_path: Path) -> int:
    if args.workspace_command == "status":
        print(json.dumps(config.workspace_status(), indent=2, ensure_ascii=False))
        return 0
    if args.workspace_command == "list":
        print(json.dumps({"active_workspace": config.active_workspace, "workspaces": config.workspace_entries()}, indent=2, ensure_ascii=False))
        return 0
    if args.workspace_command == "add":
        config.add_workspace(args.name, Path(args.path), activate=args.activate)
        save_config(config, cfg_path, overwrite=True)
        print(f"Workspace added / 已添加工作区: {args.name} -> {Path(args.path).expanduser().resolve()}")
        if args.activate:
            print(f"Active workspace / 当前工作区: {config.active_workspace}")
        return 0
    if args.workspace_command == "switch":
        status = config.switch_workspace(args.name)
        save_config(config, cfg_path, overwrite=True)
        print(json.dumps(status, indent=2, ensure_ascii=False))
        return 0
    return 2


def _builder_command(args, config: AppConfig, cfg_path: Path) -> int:
    if args.builder_command == "payload":
        payload = make_builder_payload(config)
        if args.json:
            print(json.dumps(payload, indent=2, ensure_ascii=False))
        else:
            _print_builder_payload_text(payload)
        return 0
    if args.builder_command in {"open-login", "doctor", "sniff", "configure", "smoke"}:
        command_payload = _builder_playwright_payload(args, cfg_path)
        if getattr(args, "dry_run", False):
            print(json.dumps(command_payload, indent=2, ensure_ascii=False))
            return 0
        return subprocess.call(command_payload["command"])
    return 2


def _print_builder_payload_text(payload: dict) -> None:
    print(f"Name: {payload['gpt']['name']}")
    print(f"Description: {payload['gpt']['description']}")
    print("Instructions:")
    print(payload["gpt"]["instructions"])
    print(f"Schema URL: {payload['action']['schema_import_url']}")
    print(f"Privacy URL: {payload['action']['privacy_policy_url']}")
    print("Authentication: API key / Bearer")
    print("Token: use `chatgpt-codex token`; not printed here")
    print(f"Visibility: {payload['visibility']}")


def _builder_playwright_payload(args, cfg_path: Path) -> dict:
    root = Path.cwd()
    route_map = Path(getattr(args, "output", "") or builder_route_map_path(root)).expanduser()
    state_path = builder_state_path(root)
    command = [
        "npx",
        "--yes",
        "--package",
        "playwright",
        "node",
        str(root / "scripts" / "chatgpt_builder_playwright.mjs"),
        args.builder_command,
        "--config",
        str(cfg_path),
        "--profile",
        str(playwright_profile_dir()),
        "--state",
        str(state_path),
        "--routes",
        str(route_map),
    ]
    if args.builder_command == "configure":
        command.extend(["--mode", args.mode, "--visibility", args.visibility])
    return {
        "command": command,
        "profile_path": str(playwright_profile_dir()),
        "state_path": str(state_path),
        "route_map_path": str(route_map),
        "uses_playwright_persistent_profile": True,
        "token_printed": False,
    }


def _verify_actions(config: AppConfig, base_url: str, timeout: int) -> dict:
    base = base_url.rstrip("/")
    checks = [
        _verify_get(f"{base}/health", timeout),
        _verify_openapi(f"{base}/openapi.json", base, timeout),
        _verify_post(
            f"{base}/list_files",
            {"path": ".", "recursive": False, "max_results": 20},
            config.token,
            timeout,
        ),
    ]
    for check in checks:
        check.pop("_content", None)
    return {
        "ok": all(check["ok"] for check in checks),
        "base_url": base,
        "active_workspace": config.active_workspace,
        "workspace": str(config.workspace),
        "access": config.access_status(),
        "checks": checks,
    }


def _verify_get(url: str, timeout: int) -> dict:
    return _verify_request(Request(url, method="GET"), timeout, url)


def _verify_openapi(url: str, expected_base_url: str, timeout: int) -> dict:
    check = _verify_request(Request(url, method="GET"), timeout, url)
    if not check["ok"]:
        return check
    try:
        document = json.loads(check.pop("_content"))
        servers = document.get("servers", [])
        actual_base_url = servers[0].get("url", "") if servers else ""
        check["server_url"] = actual_base_url
        check["ok"] = actual_base_url.rstrip("/") == expected_base_url.rstrip("/")
        if not check["ok"]:
            check["error"] = f"OpenAPI server URL mismatch: {actual_base_url}"
    except (KeyError, TypeError, ValueError) as exc:
        check["ok"] = False
        check["error"] = f"invalid OpenAPI document: {exc}"
    return check


def _verify_post(url: str, body: dict, token: str, timeout: int) -> dict:
    payload = json.dumps(body).encode("utf-8")
    request = Request(
        url,
        data=payload,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
        },
    )
    return _verify_request(request, timeout, url)


def _verify_request(request: Request, timeout: int, url: str) -> dict:
    # Some Cloudflare zones block the default Python-urllib user agent. Use an
    # explicit verifier identity so the health/schema checks are distinguishable
    # from anonymous automated traffic.
    request.add_header("User-Agent", "ChatGPTCodexVerifier/0.1")
    opener = build_opener(ProxyHandler({}))
    try:
        response = opener.open(request, timeout=max(1, int(timeout or 10)))
        content = response.read().decode("utf-8", errors="replace")
        return {"url": url, "ok": 200 <= response.status < 300, "status": response.status, "preview": content[:300], "_content": content}
    except HTTPError as exc:
        content = exc.read(4096).decode("utf-8", errors="replace")
        return {"url": url, "ok": False, "status": exc.code, "error": content[:300]}
    except (OSError, URLError) as exc:
        return {"url": url, "ok": False, "status": 0, "error": str(exc)}


def _api_smoke(timeout: int) -> dict:
    with tempfile.TemporaryDirectory(prefix="chatgpt-codex-api-smoke-") as tmp:
        root = Path(tmp)
        alpha = root / "alpha"
        beta = root / "beta"
        alpha.mkdir()
        beta.mkdir()
        (alpha / "alpha.txt").write_text("alpha seed\n", encoding="utf-8")
        (beta / "beta.txt").write_text("beta seed\n", encoding="utf-8")
        config_path = root / "config.json"
        config = AppConfig(
            token="api-smoke-token",
            workspaces={"alpha": alpha, "beta": beta},
            active_workspace="alpha",
            host="127.0.0.1",
            port=0,
            public_base_url="http://127.0.0.1",
        )
        server = create_server(config, config_path)
        base_url = f"http://127.0.0.1:{server.server_port}"
        config.public_base_url = base_url
        save_config(config, config_path, overwrite=True)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        checks = []
        try:
            checks.append(_api_check("health", lambda: _api_get(f"{base_url}/health", timeout), lambda body: body["ok"] and body["active_workspace"] == "alpha"))
            checks.append(_api_check("openapi", lambda: _api_get(f"{base_url}/openapi.json", timeout), lambda body: body["servers"][0]["url"] == base_url and "/exec_command" in body["paths"]))
            checks.append(_api_check_status("auth_required", lambda: _api_post(f"{base_url}/workspace_status", {}, "", timeout), 401))
            checks.append(_api_check("workspace_status", lambda: _api_post(f"{base_url}/workspace_status", {}, config.token, timeout), lambda body: body["active_workspace"] == "alpha" and body["workspace"] == str(alpha.resolve())))
            checks.append(_api_check("list_workspaces", lambda: _api_post(f"{base_url}/list_workspaces", {}, config.token, timeout), lambda body: [item["name"] for item in body["workspaces"]] == ["alpha", "beta"]))
            checks.append(_api_check("list_files", lambda: _api_post(f"{base_url}/list_files", {"path": ".", "recursive": False}, config.token, timeout), lambda body: body["entries"][0]["path"] == "alpha.txt"))
            checks.append(_api_check("read_file", lambda: _api_post(f"{base_url}/read_file", {"path": "alpha.txt"}, config.token, timeout), lambda body: body["content"] == "alpha seed\n"))
            checks.append(_api_check("write_file", lambda: _api_post(f"{base_url}/write_file", {"path": "notes/api.txt", "content": "alpha line\nneedle\n"}, config.token, timeout), lambda body: body["bytes_written"] > 0))
            checks.append(_api_check("search_text", lambda: _api_post(f"{base_url}/search_text", {"query": "needle", "path": "."}, config.token, timeout), lambda body: body["matches"][0]["path"] == "notes/api.txt"))
            checks.append(
                _api_check(
                    "apply_patch",
                    lambda: _api_post(
                        f"{base_url}/apply_patch",
                        {
                            "patch": "\n".join(
                                [
                                    "*** Begin Patch",
                                    "*** Update File: notes/api.txt",
                                    "@@",
                                    " alpha line",
                                    "-needle",
                                    "+needle patched",
                                    "*** End Patch",
                                ]
                            )
                        },
                        config.token,
                        timeout,
                    ),
                    lambda body: body["changed_files"] == ["notes/api.txt"],
                )
            )
            checks.append(_api_check("read_after_patch", lambda: _api_post(f"{base_url}/read_file", {"path": "notes/api.txt"}, config.token, timeout), lambda body: "needle patched" in body["content"]))
            command = f"\"{sys.executable}\" -c \"from pathlib import Path; print(Path.cwd().name)\""
            checks.append(_api_check("exec_command", lambda: _api_post(f"{base_url}/exec_command", {"command": command, "cwd": ".", "timeout_seconds": 10}, config.token, timeout), lambda body: body["exit_code"] == 0 and body["stdout"].strip() == "alpha"))
            checks.append(_api_check("switch_workspace", lambda: _api_post(f"{base_url}/switch_workspace", {"name": "beta"}, config.token, timeout), lambda body: body["active_workspace"] == "beta" and body["workspace"] == str(beta.resolve())))
            checks.append(_api_check("list_files_after_switch", lambda: _api_post(f"{base_url}/list_files", {"path": ".", "recursive": False}, config.token, timeout), lambda body: body["entries"][0]["path"] == "beta.txt"))
            checks.append(_api_check_status("path_escape_blocked", lambda: _api_post(f"{base_url}/read_file", {"path": "../outside.txt"}, config.token, timeout), 400))
            checks.append(_api_check_status("dangerous_command_blocked", lambda: _api_post(f"{base_url}/exec_command", {"command": "rm -rf /tmp/nope"}, config.token, timeout), 400))
            config.revoke_access()
            save_config(config, config_path, overwrite=True)
            checks.append(_api_check_status("expired_access_blocked", lambda: _api_post(f"{base_url}/workspace_status", {}, config.token, timeout), 403))
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)

        return {
            "ok": all(check["ok"] for check in checks),
            "base_url": base_url,
            "workspace_root": str(root),
            "checks": checks,
        }


def _api_get(url: str, timeout: int) -> dict:
    return _api_request(Request(url, method="GET"), timeout)


def _api_post(url: str, body: dict, token: str, timeout: int) -> dict:
    payload = json.dumps(body).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return _api_request(Request(url, data=payload, method="POST", headers=headers), timeout)


def _api_request(request: Request, timeout: int) -> dict:
    opener = build_opener(ProxyHandler({}))
    try:
        response = opener.open(request, timeout=max(1, int(timeout or 10)))
        return {
            "status": response.status,
            "body": json.loads(response.read().decode("utf-8")),
        }
    except HTTPError as exc:
        content = exc.read().decode("utf-8", errors="replace")
        try:
            body = json.loads(content)
        except ValueError:
            body = {"error": content[:300]}
        return {"status": exc.code, "body": body}
    except (OSError, URLError) as exc:
        return {"status": 0, "body": {"error": str(exc)}}


def _api_check(name: str, call, predicate) -> dict:
    result = call()
    error = ""
    try:
        ok = result["status"] == 200 and predicate(result["body"])
    except Exception as exc:
        ok = False
        error = str(exc)
    check = {
        "name": name,
        "ok": ok,
        "status": result["status"],
        "preview": _json_preview(result["body"]),
    }
    if error:
        check["error"] = error
    return check


def _api_check_status(name: str, call, expected_status: int) -> dict:
    result = call()
    return {
        "name": name,
        "ok": result["status"] == expected_status,
        "status": result["status"],
        "preview": _json_preview(result["body"]),
    }


def _json_preview(value: object) -> str:
    return json.dumps(value, ensure_ascii=False)[:300]


def _platform_label() -> str:
    system = platform.system() or sys.platform
    release = platform.release()
    return f"{system} {release}".strip()


def _selected_os(value: str) -> str:
    if value != "auto":
        return value
    system = platform.system().lower()
    if system == "darwin":
        return "macos"
    if system == "windows":
        return "windows"
    return system or sys.platform


def _open_chrome_or_default(url: str) -> bool:
    system = platform.system().lower()
    try:
        if system == "darwin" and shutil.which("open"):
            return subprocess.call(["open", "-a", "Google Chrome", url]) == 0
        if system == "windows":
            return subprocess.call(["cmd", "/c", "start", "", "chrome", url]) == 0
    except OSError:
        pass
    return bool(webbrowser.open(url))


def _route_options() -> str:
    return """Route options / 访问入口选项

local-only:
- cloudflared required: no
- domain required: no
- ChatGPT web Actions: no, local testing only
- cloudflared：不需要
- 域名：不需要
- ChatGPT 网页 Actions：不能真实调用，仅本地测试

built-in-quick-tunnel:
- cloudflared required: yes
- domain required: no
- ChatGPT web Actions: yes, with a temporary public HTTPS URL
- cloudflared：需要
- 域名：不需要
- ChatGPT 网页 Actions：可以，使用临时公网 HTTPS 地址

custom-domain:
- cloudflared required: no for this project, unless your chosen routing uses it
- domain required: yes
- ChatGPT web Actions: yes, with your stable HTTPS domain
- cloudflared：本项目不强制，除非你的路由方案需要
- 域名：需要
- ChatGPT 网页 Actions：可以，使用稳定 HTTPS 域名

existing-https-route:
- cloudflared required: no
- domain required: no, if you already have a public HTTPS URL
- ChatGPT web Actions: yes, with that HTTPS URL
- cloudflared：不需要
- 域名：不需要，前提是已有公网 HTTPS URL
- ChatGPT 网页 Actions：可以，使用已有 HTTPS 地址
"""


def _chatgpt_preflight(cfg_path: Path, language: str = "en") -> dict:
    result = {
        "language": language,
        "chatgpt_login": {
            "required": True,
            "login_url": "https://chatgpt.com/",
            "open_command": "chatgpt-codex builder open-login",
            "agent_rule": "Open the login page and wait for the human to finish. Do not ask for passwords, cookies, sessions, or API keys.",
        },
        "account_requirements": {
            "can_create_and_edit_gpts": ["ChatGPT Pro", "ChatGPT Plus", "ChatGPT Team", "ChatGPT Enterprise", "ChatGPT Edu"],
            "free_tier": "Free users may have limited access to existing GPTs, but should not be treated as eligible to create or edit GPTs with Actions.",
            "actions_model_note": "Custom Actions are not available in Pro mode models. Use a non-Pro model that supports Actions.",
        },
        "builder_automation": {
            "editor_url": "https://chatgpt.com/gpts/editor",
            "open_command": "chatgpt-codex builder doctor",
            "fully_configurable_by_local_api": False,
            "why": "ChatGPT Builder is a web-only editor without a public stable local API. Use Playwright first; internal API replay is allowed only after same-session sniffing and validation.",
            "agent_rule": "After human login in the Playwright persistent profile, inspect the Builder page. Continue only if the editor loads and the Actions section is available.",
            "primary_path": "chatgpt-codex builder configure --mode ui",
            "internal_api_discovery": "chatgpt-codex builder sniff",
            "fallback": "Computer Use only when Playwright cannot operate the page.",
        },
        "local_requirements": {
            "public_https_required_for_chatgpt_web": True,
            "local_only_is_for_tests": True,
            "bearer_token_required": True,
            "save_visibility": "Only me unless the user intentionally wants to share access.",
        },
        "configured": False,
    }
    if cfg_path.exists():
        config = load_config(cfg_path)
        result.update(
            {
                "configured": True,
                "active_workspace": config.active_workspace,
                "workspace": str(config.workspace),
                "public_base_url": config.public_base_url.rstrip("/"),
                "openapi_url": f"{config.public_base_url.rstrip('/')}/openapi.json",
                "privacy_url": f"{config.public_base_url.rstrip('/')}/privacy",
                "token_configured": bool(config.token),
                "access": config.access_status(),
                "builder_fields": {
                    "name": "Local Coding Bridge",
                    "description": "Access and edit one authorized local workspace through a private bearer-protected Action bridge.",
                    "authentication": "API key / Bearer",
                    "schema_import_url": f"{config.public_base_url.rstrip('/')}/openapi.json",
                    "privacy_policy_url": f"{config.public_base_url.rstrip('/')}/privacy",
                    "token_command": "chatgpt-codex token",
                },
            }
        )
    return result


def _access_plan_summary(access_plan: str) -> str:
    plan = ACCESS_PLANS[access_plan]
    return (
        f"Access plan / 访问方案: {access_plan}\n"
        f"Public HTTPS required / 需要公网 HTTPS: {'yes / 是' if plan['needs_public_https'] else 'no / 否'}\n"
        f"cloudflared required / 需要 cloudflared: {'yes / 是' if plan['needs_cloudflared'] else 'no / 否'}\n"
        f"Domain required / 需要域名: {'yes / 是' if plan['needs_domain'] else 'no / 否'}"
    )


def _permissions_template() -> dict:
    return {
        "schema_version": 1,
        "workspace": "/absolute/path/to/your/project",
        "operating_system": "macos",
        "access_plan": "built-in-quick-tunnel",
        "public_base_url": "https://actions.example.com",
        "allow_browser_automation": True,
        "allow_start_services": True,
        "allow_install_helpers": True,
        "allow_workspace_write": True,
        "allow_command_execution": True,
        "hostname": "actions.example.com",
        "created_at": "",
    }


def _gpt_instructions(config: AppConfig) -> str:
    base = config.public_base_url.rstrip("/")
    return f"""Custom GPT setup / Custom GPT 配置

1. Open ChatGPT -> Explore GPTs -> Create.
   打开 ChatGPT -> Explore GPTs / 探索 GPT -> Create / 创建。
2. Instructions:
   Instructions / 指令：

You are my local coding assistant for the workspace exposed through Actions.
Use workspace_status before file, code, or command work so you can show the current local directory. Use list_workspaces and switch_workspace when I ask to view or switch projects. Only switch to authorized workspace names returned by list_workspaces. After switching, state the active workspace name and local path. Use list_files, read_file, search_text, write_file, apply_patch, and exec_command for project work. Inspect files before editing. Keep changes scoped. Do not run destructive commands unless I explicitly ask for that exact action in the current chat.

你是我的本地编程助手，通过 Actions 访问我暴露的 workspace。
当我询问文件、代码、命令或当前项目时，先使用 workspace_status 显示当前本地目录。当我要求查看或切换项目时，使用 list_workspaces 和 switch_workspace。只能切换到 list_workspaces 返回的已授权工作区名称。切换后说明当前工作区名称和本地路径。项目操作使用 list_files、read_file、search_text、write_file、apply_patch 和 exec_command。编辑前先检查文件。保持改动范围清晰。除非我在当前对话中明确要求执行某个危险操作，否则不要运行破坏性命令。

3. Actions:
   Actions / 动作：
   - Authentication / 鉴权方式: API key
   - Auth type / 类型: Bearer
   - API key: use the token printed by `chatgpt-codex token`
   - API key：填入 `chatgpt-codex token` 打印的 token
   - Import schema URL / 导入 schema 地址: {base}/openapi.json
   - Privacy policy / 隐私政策: {base}/privacy

4. Save the GPT as Only me unless you intentionally want to share access.
   保存时选择 Only me / 只有我，除非你明确想共享访问权限。
"""


def _agent_brief() -> str:
    return """Skill setup handoff / Skill 自动配置交接说明

Give this repository to Codex or Claude and ask it to use the bundled skill:

skills/chatgpt-codex/SKILL.md

Then ask it to complete the local ChatGPT Actions setup.

把这个仓库交给 Codex 或 Claude，并要求它使用内置 skill：

skills/chatgpt-codex/SKILL.md

然后让它完成本地 ChatGPT Actions 配置。

Agent mission / Agent 任务：
1. Ask only for the minimal human inputs.
   只向用户询问真人必须提供的最小信息。
2. Install the local launcher.
   安装本地启动器。
3. Save setup choices and permissions in .chatgpt-codex/permissions.json.
   将配置选项和授权保存到 .chatgpt-codex/permissions.json。
4. Register the channel for the target workspace.
   为目标 workspace 注册通道。
5. Start the local server. If ChatGPT web should call it, set up or use a public HTTPS route.
   启动本地服务。如果 ChatGPT 网页端需要调用它，请配置或使用公网 HTTPS 入口。
6. Open ChatGPT Builder with Playwright after browser automation is approved and the user has logged in manually.
   用户授权浏览器自动化并手动登录后，用 Playwright 打开 ChatGPT Builder。
7. Verify /health, /openapi.json, and at least one authenticated read-only action.
   验证 /health、/openapi.json，以及至少一个带鉴权的只读 Action。
8. Print or apply the ChatGPT Builder fields.
   打印或填写 ChatGPT Builder 字段。

Required user inputs / 需要用户提供：
- Playwright-profile human login to ChatGPT: required / Playwright profile 真人登录 ChatGPT：必须
- workspace path: required / workspace 路径：必须
- Browser human login to Cloudflare: optional / 浏览器真人登录 Cloudflare：可选
- Cloudflare-managed domain: optional / Cloudflare 管理的域名：可选
- local authorization for OS detection, route selection, helper install, service start, Playwright opening, Builder configuration after human login, workspace writes, and workspace command execution / 本地授权：允许自动识别系统、选择入口方案、安装辅助工具、启动服务、打开 Playwright、在真人登录后配置 Builder、写入 workspace、并在 workspace 内执行命令

Defaults / 默认：
- Detect macOS or Windows automatically and use port 8766 unless the user overrides it.
  自动识别 macOS 或 Windows，默认端口 8766，除非用户明确覆盖。
- If no Cloudflare login and domain are available, use a temporary HTTPS tunnel for ChatGPT web.
  没有 Cloudflare 登录和域名时，使用临时 HTTPS 隧道供 ChatGPT 网页端访问。
- If both are available, use the fixed hostname https://chatgpt-codex.<domain>.
  两者都具备时，使用固定域名 https://chatgpt-codex.<domain>。
- Use local-only only for tests or explicit user requests.
  仅在测试或用户明确要求时使用仅本地模式。
- The ChatGPT account must support Actions, and the GPT should be saved private unless the user intentionally shares access.
  ChatGPT 账号必须支持 Actions；除非用户明确要共享访问，否则 GPT 应保存为私有。

Do not ask for / 不要索要：
- ChatGPT password / ChatGPT 密码
- browser cookies / 浏览器 cookie
- OpenAI API key / OpenAI API key
- unrelated secrets / 无关密钥

Suggested command sequence on macOS / macOS 建议命令序列：
```bash
./scripts/install.sh
. .venv/bin/activate
chatgpt-codex route-options
chatgpt-codex authorize \\
  --workspace "$WORKSPACE" \\
  --operating-system auto \\
  --access-plan "$ACCESS_PLAN" \\
  --public-base-url "$PUBLIC_BASE_URL" \\
  --allow-browser-automation \\
  --allow-start-services \\
  --allow-install-helpers \\
  --allow-workspace-write \\
  --allow-command-execution
chatgpt-codex channel register --workspace "$WORKSPACE" --public-base-url "$PUBLIC_BASE_URL"
chatgpt-codex doctor
chatgpt-codex serve
```

Suggested command sequence on Windows PowerShell / Windows PowerShell 建议命令序列：
```powershell
powershell -ExecutionPolicy Bypass -File .\\scripts\\install.ps1
. .\\.venv\\Scripts\\Activate.ps1
$Workspace = "C:\\absolute\\path\\to\\project"
$PublicBaseUrl = "https://actions.example.com"
chatgpt-codex route-options
chatgpt-codex authorize `
  --workspace "$Workspace" `
  --operating-system windows `
  --access-plan built-in-quick-tunnel `
  --public-base-url "$PublicBaseUrl" `
  --allow-browser-automation `
  --allow-start-services `
  --allow-install-helpers `
  --allow-workspace-write `
  --allow-command-execution
chatgpt-codex channel register --workspace "$Workspace" --public-base-url "$PublicBaseUrl"
chatgpt-codex doctor
chatgpt-codex serve
```

In another terminal if using the built-in quick tunnel / 如果使用内置临时隧道，在另一个终端运行：
```bash
chatgpt-codex tunnel
```

If browser automation is approved and the user has logged into ChatGPT manually / 如果用户已授权浏览器自动化并手动登录 ChatGPT：
```bash
chatgpt-codex builder open-login
chatgpt-codex builder doctor
chatgpt-codex builder configure --mode ui
chatgpt-codex builder smoke
```

After verification, print / 验证后打印：
```bash
chatgpt-codex gpt-instructions
chatgpt-codex token
```

The user should paste the token only into ChatGPT Builder's Action authentication field.

用户只应把 token 粘贴到 ChatGPT Builder 的 Action 鉴权字段。
"""
