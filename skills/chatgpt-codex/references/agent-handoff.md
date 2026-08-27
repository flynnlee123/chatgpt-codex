# Agent Handoff / Agent 交接提示

## Copyable Prompt / 可复制提示词

```text
Please use the chatgpt-codex skill in this repository to set up my ChatGPT local coding bridge.

Ask me only for the minimal human inputs:
- confirm I am logged into ChatGPT in the Playwright persistent profile
- workspace path
- optional: confirm I am logged into Cloudflare in a browser
- optional: Cloudflare-managed domain
- local authorization for you to detect the OS, choose the route, install needed helpers, start services, open the Playwright browser, configure Builder after human login, write the workspace, and execute commands inside the workspace

Use a temporary HTTPS tunnel when I do not provide Cloudflare login plus a domain. Use the fixed hostname chatgpt-codex.<domain> when both are available.

Then install, configure, start, verify, and give me the exact ChatGPT Builder fields. Do not ask me to choose the OS, access plan, port, TTL, or subdomain unless I explicitly override defaults. Do not set a TTL unless I explicitly ask for a short-lived session.

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

然后完成安装、配置、启动、验证，并给我可直接填写到 ChatGPT Builder 的字段。除非我明确要覆盖默认值，不要问我选择操作系统、访问方案、端口、TTL 或子域名。除非我明确要求短时会话，否则不要设置 TTL。

不要索要我的 ChatGPT 密码、浏览器 cookie、OpenAI API key 或无关密钥。
```

## Completion Checklist / 完成检查

- Minimal human inputs collected.
- 已收集真人必须提供的最小信息。
- Local launcher installed with the macOS or Windows installer.
- 已使用 macOS 或 Windows 安装脚本安装本地启动器。
- Setup choices saved in `.chatgpt-codex/permissions.json`.
- 已在 `.chatgpt-codex/permissions.json` 保存配置选项。
- If manual editing is preferred, root `permissions.example.json` copied with the OS helper script.
- 如果偏好手工编辑，已用对应操作系统辅助脚本复制根目录的 `permissions.example.json`。
- Channel registered with `chatgpt-codex channel register`, creating `.chatgpt-codex/config.json` with the workspace path, public URL, and token.
- 已用 `chatgpt-codex channel register` 注册通道，在 `.chatgpt-codex/config.json` 中写入 workspace 路径、公网 URL 和 token。
- Machine-readable local state checked with `chatgpt-codex status` and command catalog checked with `chatgpt-codex ai-commands`.
- 已用 `chatgpt-codex status` 检查机器可读本地状态，并用 `chatgpt-codex ai-commands` 检查命令目录。
- Extra projects registered with `chatgpt-codex workspace add` when the user provides more authorized workspaces.
- 当用户提供更多已授权工作区时，已用 `chatgpt-codex workspace add` 登记额外项目。
- Local server started with `chatgpt-codex serve`.
- 已用 `chatgpt-codex serve` 启动本地服务。
- Public HTTPS route available when ChatGPT web access is required.
- 需要 ChatGPT 网页端访问时，公网 HTTPS 路由可用。
- Final public URL saved with `chatgpt-codex channel renew --public-base-url`.
- 已用 `chatgpt-codex channel renew --public-base-url` 保存最终公网 URL。
- Channel status checked with `chatgpt-codex channel status`.
- 已用 `chatgpt-codex channel status` 检查通道状态。
- Temporary tunnel used by default; fixed hostname `chatgpt-codex.<domain>` used when Cloudflare login and domain are available.
- 默认使用临时隧道；当 Cloudflare 登录和域名都具备时，使用固定域名 `chatgpt-codex.<domain>`。
- `/health` works.
- `/health` 可访问。
- `/openapi.json` works.
- `/openapi.json` 可访问。
- Authenticated read-only Action works.
- 带鉴权只读 Action 可用。
- `chatgpt-codex api-smoke` passes, including expiry and safety-block checks.
- `chatgpt-codex api-smoke` 通过，包括过期和安全拦截检查。
- `chatgpt-codex verify` passes.
- `chatgpt-codex verify` 通过。
- Builder fields printed.
- 已打印 Builder 字段。
- GPT instructions include `workspace_status` and `switch_workspace`, and require showing the current local directory after each switch; `workspace_status` includes the authorized workspace list.
- GPT Instructions 包含 `workspace_status` 和 `switch_workspace`，并要求每次切换后显示当前本地目录；`workspace_status` 已包含授权工作区列表。
- If browser automation is approved, ChatGPT Builder configured after the user logs in manually.
- 如果用户授权浏览器自动化，已在用户手动登录后配置 ChatGPT Builder。
