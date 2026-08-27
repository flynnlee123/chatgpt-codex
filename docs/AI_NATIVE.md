# AI-Native Setup / AI-Native 自动配置

This repository can be operated directly by Codex or Claude.

这个仓库可以直接交给 Codex 或 Claude 操作。

The primary agent entry is the bundled skill:

主要 agent 入口是仓库内置 skill：

- `skills/chatgpt-codex/SKILL.md`

## User Prompt / 用户可直接复制的提示词

```text
Please use the chatgpt-codex skill in this repository to set up my ChatGPT local coding bridge.

Ask me only for the minimal human inputs:
- confirm I am logged into ChatGPT in the Playwright persistent profile
- workspace path
- optional: confirm I am logged into Cloudflare in a browser
- optional: Cloudflare-managed domain
- local authorization for you to detect the OS, choose the route, install needed helpers, start services, open the Playwright browser, configure Builder after human login, write the workspace, and execute commands inside the workspace

Use a temporary HTTPS tunnel when I do not provide Cloudflare login plus a domain. Use the fixed hostname chatgpt-codex.<domain> when both are available.

Then install, configure, start, verify, and give me the exact ChatGPT Builder fields. Do not ask me to choose the OS, access plan, port, or subdomain unless I explicitly override defaults.

Do not ask for my ChatGPT password, browser cookies, OpenAI API key, or unrelated secrets.
```

```text
请使用本仓库里的 chatgpt-codex skill，把这个仓库配置成我的 ChatGPT 本地编程桥。

只问我真人必须提供的最小信息：
- 确认我已在 Playwright 持久化 profile 中登录 ChatGPT
- workspace 路径
- 可选：确认我已在浏览器登录 Cloudflare
- 可选：Cloudflare 管理的域名
- 本地授权：允许你自动识别系统、选择入口方案、安装必要辅助工具、启动服务、打开 Playwright 浏览器、在真人登录后配置 Builder、写入 workspace，并在 workspace 内执行命令

如果我没有同时提供 Cloudflare 登录和域名，使用临时 HTTPS 隧道。如果两者都具备，使用固定域名 chatgpt-codex.<domain>。

然后完成安装、配置、启动、验证，并给我可直接填写到 ChatGPT Builder 的字段。除非我明确要覆盖默认值，不要问我选择操作系统、访问方案、端口或子域名。

不要索要我的 ChatGPT 密码、浏览器 cookie、OpenAI API key 或无关密钥。
```

## Agent Checklist / Agent 检查清单

- Collect only the minimal human inputs before changing local state.
- 修改本地状态前只收集真人必须提供的最小信息。
- Run `./scripts/install.sh` on macOS or `.\scripts\install.ps1` on Windows PowerShell.
- macOS 运行 `./scripts/install.sh`；Windows PowerShell 运行 `.\scripts\install.ps1`。
- Run `chatgpt-codex channel register --workspace <path> --public-base-url <url>` for the first channel registration.
- 首次注册通道时运行 `chatgpt-codex channel register --workspace <path> --public-base-url <url>`。
- Use `chatgpt-codex status` and `chatgpt-codex ai-commands` for machine-readable local management.
- 使用 `chatgpt-codex status` 和 `chatgpt-codex ai-commands` 做机器可读的本地管理。
- Run `chatgpt-codex chatgpt-preflight` before browser setup. It reports account prerequisites, login handoff commands, Builder limits, and Builder fields without printing the bearer token.
- 浏览器配置前运行 `chatgpt-codex chatgpt-preflight`。它会报告账号前提、登录交接命令、Builder 边界和 Builder 字段，但不会打印 bearer token。
- After a tunnel or route provides the final URL, run `chatgpt-codex channel renew --public-base-url <url>` or `chatgpt-codex set-public-url <url>`.
- 隧道或入口给出最终 URL 后，运行 `chatgpt-codex channel renew --public-base-url <url>` 或 `chatgpt-codex set-public-url <url>`。
- Add extra authorized projects with `chatgpt-codex workspace add --name <name> --path <path>`.
- 用 `chatgpt-codex workspace add --name <name> --path <path>` 添加额外已授权项目。
- Run `chatgpt-codex route-options` and `chatgpt-codex authorize` to save choices in `.chatgpt-codex/permissions.json`.
- 运行 `chatgpt-codex route-options` 和 `chatgpt-codex authorize`，把选项保存到 `.chatgpt-codex/permissions.json`。
- If the user wants manual file editing, copy root `permissions.example.json` with `scripts/prepare-permissions.sh` or `scripts/prepare-permissions.ps1`.
- 如果用户想手工编辑文件，用 `scripts/prepare-permissions.sh` 或 `scripts/prepare-permissions.ps1` 复制根目录的 `permissions.example.json`。
- Run `chatgpt-codex doctor`.
- 运行 `chatgpt-codex doctor`。
- Start `chatgpt-codex serve`. Do not set a TTL for normal personal use unless the user asks for a short-lived session.
- 启动 `chatgpt-codex serve`。普通个人自用不要设置 TTL，除非用户明确要求短时会话。
- Use a temporary HTTPS tunnel when no Cloudflare login/domain are provided; use `chatgpt-codex.<domain>` when both are provided.
- 没有 Cloudflare 登录/域名时使用临时 HTTPS 隧道；两者都提供时使用 `chatgpt-codex.<domain>`。
- Open ChatGPT Builder with `chatgpt-codex builder open-login` and `chatgpt-codex builder doctor` after browser automation is approved.
- 用户授权浏览器自动化后，用 `chatgpt-codex builder open-login` 和 `chatgpt-codex builder doctor` 打开并检查 ChatGPT Builder。
- If internal API acceleration is needed, run `chatgpt-codex builder sniff`, replay only in the same Playwright browser context, then refresh and verify. Stop if the editor or Actions section is unavailable.
- 如果需要内部 API 加速，运行 `chatgpt-codex builder sniff`；replay 只能在同一个 Playwright 浏览器会话中进行，然后刷新并验证。如果编辑器或 Actions 区域不可用，停止。
- Ensure GPT instructions mention `workspace_status` and `switch_workspace` for showing and switching the current local directory; `workspace_status` includes the authorized workspace list.
- 确保 GPT Instructions 写明用 `workspace_status` 和 `switch_workspace` 显示并切换当前本地目录；`workspace_status` 已包含授权 workspace 列表。
- Run `chatgpt-codex api-smoke` before browser work to test the Action interfaces directly in temporary workspaces.
- 浏览器操作前运行 `chatgpt-codex api-smoke`，在临时工作区里直接测试 Action 接口。
- Use `chatgpt-codex channel status` to inspect registration without leaking the token. Use `chatgpt-codex channel revoke` to disable the channel, and `chatgpt-codex channel renew` to reactivate it.
- 用 `chatgpt-codex channel status` 查看注册状态且不泄露 token。用 `chatgpt-codex channel revoke` 停用通道，用 `chatgpt-codex channel renew` 重新激活。
- Use `chatgpt-codex rotate-token` only when Builder auth must be refreshed manually.
- 只有在需要手动刷新 Builder 鉴权时才用 `chatgpt-codex rotate-token`。
- Verify `/health`, `/openapi.json`, and one authenticated read-only action.
- 验证 `/health`、`/openapi.json` 和一个带鉴权的只读 Action。
- Prefer `chatgpt-codex verify` for machine-readable final verification.
- 优先用 `chatgpt-codex verify` 做机器可读的最终验证。
- Print `chatgpt-codex gpt-instructions`.
- 打印 `chatgpt-codex gpt-instructions`。
- Give the user the token privately for the Builder auth field.
- 将 token 私下交给用户，用于 Builder 鉴权字段。
