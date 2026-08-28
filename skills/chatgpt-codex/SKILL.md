---
name: chatgpt-codex
description: Set up and verify this repository as a ChatGPT local coding bridge. Use when the user asks Codex, Claude, or another AI agent to install ChatGPT Codex, collect minimal human inputs, configure a workspace, start the local server, set up or use a public HTTPS route, verify ChatGPT Actions endpoints, or produce the final ChatGPT Builder fields.
---

# ChatGPT Codex

Use this skill to turn this repository into a working local coding bridge for ChatGPT web.

使用本 skill，将本仓库配置成 ChatGPT 网页版可调用的本地编程桥。

## Workflow / 流程

1. Ask only for the minimal human inputs before changing local state.
2. Run `chatgpt-codex chatgpt-preflight` before browser work.
3. If login is needed, open `chatgpt-codex builder open-login` and wait for the human to finish login in the Playwright persistent profile.
4. Open ChatGPT Builder and confirm the account can create or edit a GPT with Actions.
5. Install the local launcher.
6. Save setup permissions in `.chatgpt-codex/permissions.json`.
7. Create config for the target workspace.
8. Start the local server and set up or use a public HTTPS route when ChatGPT web access is needed.
9. Use Playwright with a dedicated persistent profile as the primary ChatGPT Builder automation path.
10. Use internal API sniffing only as a same-session acceleration layer, then refresh the Builder page and verify.
11. Use Computer Use only as a fallback when Playwright cannot operate the page.
12. Verify health, schema, and one authenticated read-only action.
13. Print or apply the final ChatGPT Builder fields.

中文：

1. 修改本地状态前，只向用户询问真人必须提供的最小信息。
2. 浏览器操作前运行 `chatgpt-codex chatgpt-preflight`。
3. 如需登录，运行 `chatgpt-codex builder open-login` 打开 Playwright 持久化 profile，并等待真人完成登录。
4. 打开 ChatGPT Builder，确认账号可以创建或编辑带 Actions 的 GPT。
5. 安装本地启动器。
6. 将配置授权保存到 `.chatgpt-codex/permissions.json`。
7. 为目标 workspace 创建配置。
8. 启动本地服务；当需要 ChatGPT 网页端访问时，配置或使用公网 HTTPS 入口。
9. 默认使用带独立持久化 profile 的 Playwright 作为 ChatGPT Builder 自动化主路径。
10. 内部 API 嗅探只作为同会话加速层，之后必须刷新 Builder 页面并验证。
11. 只有 Playwright 无法操作页面时，才用 Computer Use 兜底。
12. 验证健康检查、schema，以及一个带鉴权的只读 Action。
13. 打印或填写最终可用于 ChatGPT Builder 的字段。

For a copyable user prompt and detailed checklist, read `references/agent-handoff.md`.

如需可复制提示词和详细检查清单，读取 `references/agent-handoff.md`。

## Closed Loop / 功能闭环

The setup is complete only when all of these are true:

只有全部满足时才算完成：

- minimal human inputs and local authorization are recorded;
- 已记录真人最小输入和本地授权；
- `.chatgpt-codex/config.json` exists with `workspaces` and `active_workspace`;
- `.chatgpt-codex/config.json` 已存在，并包含 `workspaces` 和 `active_workspace`；
- `chatgpt-codex status` is readable by the agent;
- agent 可以读取 `chatgpt-codex status`；
- local server is running;
- 本地服务已运行；
- final public URL is saved with `chatgpt-codex channel renew --public-base-url`;
- 最终公网 URL 已用 `chatgpt-codex channel renew --public-base-url` 保存；
- `chatgpt-codex verify` passes;
- `chatgpt-codex verify` 通过；
- ChatGPT Builder has the current schema URL and bearer token;
- ChatGPT Builder 已配置当前 schema URL 和 bearer token；
- GPT chat can show and switch the active workspace using Actions.
- GPT 对话可以通过 Actions 显示并切换当前工作区。
- Playwright Builder automation can produce payloads, inspect login/editor readiness, sniff Builder routes, and run a smoke test.
- Playwright Builder 自动化可以生成 payload、检查登录和编辑器就绪状态、嗅探 Builder 路由，并运行冒烟测试。

## Required Inputs / 必要信息

Ask for:

询问：

- Human login to ChatGPT in the Playwright persistent profile: required. The user logs in manually; the agent only operates after login.
- 在 Playwright 持久化 profile 中真人登录 ChatGPT：必须。用户手动登录；agent 只在登录后操作。
- Workspace path: required, for example `/Users/me/project/demo`.
- Workspace 路径：必须，例如 `/Users/me/project/demo`。
- Browser human login to Cloudflare: optional, only for a stable Cloudflare-managed hostname.
- 浏览器真人登录 Cloudflare：可选，仅在需要稳定的 Cloudflare 托管域名时使用。
- Cloudflare-managed domain: optional. When provided, always use the fixed hostname `chatgpt-codex.<domain>`, for example `chatgpt-codex.hutiefang.net`.
- Cloudflare 管理的域名：可选。提供时固定使用 `chatgpt-codex.<domain>`，例如 `chatgpt-codex.hutiefang.net`。
- Local authorization: required. Confirm the agent may detect the OS, choose the route, install needed helpers, start local services, open the Playwright browser, configure ChatGPT Builder after human login, write the workspace, and execute commands inside the workspace.
- 本地授权：必须。确认 agent 可以自动识别系统、选择入口方案、安装必要辅助工具、启动本地服务、打开 Playwright 浏览器、在真人登录后配置 ChatGPT Builder、写入 workspace，并在 workspace 内执行命令。

Do not ask the user to choose an operating system, access plan, local port, or subdomain unless they explicitly want to override defaults. Detect the OS, use port `8766`, and choose the route automatically.

不要要求用户选择操作系统、访问方案、本地端口或子域名，除非用户明确要覆盖默认值。自动识别系统，默认使用端口 `8766`，并自动选择入口方案。

Route defaults:

入口默认规则：

- If no Cloudflare login and domain are available, use a temporary HTTPS tunnel for ChatGPT web.
- 如果没有 Cloudflare 登录和域名，使用临时 HTTPS 隧道供 ChatGPT 网页端访问。
- If Cloudflare login and a managed domain are available, configure the stable hostname `chatgpt-codex.<domain>`.
- 如果已登录 Cloudflare 且有托管域名，配置稳定域名 `chatgpt-codex.<domain>`。
- Use local-only only for tests or explicit user requests.
- 仅在测试或用户明确要求时使用仅本地模式。
- The ChatGPT account must support GPT Actions to create or configure the GPT. Save it private unless the user intentionally shares access.
- ChatGPT 账号必须支持 GPT Actions 才能创建或配置 GPT。除非用户明确要共享访问，否则保存为私有。
- Treat Free tier as not eligible for creating or editing GPTs. Paid plans such as Pro, Plus, Team, Enterprise, and Edu can create GPTs, but custom Actions do not run in Pro mode models. If the editor does not expose Actions, stop before local setup work becomes wasted effort.
- 将免费账号视为不能创建或编辑 GPT。Pro、Plus、Team、Enterprise、Edu 等付费套餐可以创建 GPT，但自定义 Actions 不能运行在 Pro mode 模型中。如果编辑器没有显示 Actions，在继续本地配置前停止。

Never ask for ChatGPT passwords, browser cookies, OpenAI API keys, or unrelated secrets.

不要索要 ChatGPT 密码、浏览器 cookie、OpenAI API key 或无关密钥。

## Builder Automation / Builder 自动化

Primary path:

主路径：

- Use `chatgpt-codex builder open-login` to open ChatGPT in a Playwright persistent profile. This profile is dedicated to this tool and does not reuse daily Chrome.
- 使用 `chatgpt-codex builder open-login` 在 Playwright 持久化 profile 中打开 ChatGPT。这个 profile 专用于本工具，不复用日常 Chrome。
- The Chrome plugin is not a default dependency. Only use it if the user explicitly wants to reuse an already logged-in Chrome session.
- Chrome 插件不是默认依赖。只有用户明确要求复用已登录的 Chrome 会话时才使用。
- Use `chatgpt-codex builder doctor` after the human logs in to check the Builder page and Actions availability.
- 用户登录后，用 `chatgpt-codex builder doctor` 检查 Builder 页面和 Actions 是否可用。
- Use `chatgpt-codex builder payload --json` as the single source of truth for GPT name, description, instructions, schema URL, privacy URL, auth type, and visibility. It does not print the bearer token.
- 使用 `chatgpt-codex builder payload --json` 作为 GPT 名称、描述、instructions、schema URL、privacy URL、鉴权类型和可见性的唯一字段来源。它不会打印 bearer token。
- Use `chatgpt-codex builder configure --mode ui` to prefill name/description/instructions; then complete Add Action + bearer token + save by hand. It waits and auto-captures the saved GPT URL so `builder smoke` works end to end.
- 使用 `chatgpt-codex builder configure --mode ui` 预填名称/描述/指令；然后手动完成 添加 Action + 填 token + 保存。它会等待并自动捕获保存后的 GPT 地址，让 `builder smoke` 端到端可用。

Internal API acceleration:

内部 API 加速：

- Use `chatgpt-codex builder sniff` to capture the Builder's internal route shape while the user or Playwright performs one save/configure flow.
- 使用 `chatgpt-codex builder sniff`，在用户或 Playwright 执行一次保存或配置流程时捕获 Builder 内部路由形状。
- The route map is saved as `.chatgpt-codex/builder-routes.json`, redacted, ignored by Git, and local to this machine.
- route map 保存为 `.chatgpt-codex/builder-routes.json`，会脱敏，被 Git 忽略，并且只属于本机。
- Replay internal API calls only inside the same Playwright browser context. Do not export cookies, sessions, or headers.
- 内部 API replay 只能在同一个 Playwright 浏览器会话中执行。不要导出 cookie、session 或 headers。
- Treat captured internal routes as unstable. If validation fails, fall back to UI automation.
- 将捕获到的内部路由视为不稳定。如果验证失败，回退到 UI 自动化。

Fallback:

兜底：

- Use Computer Use only when Playwright cannot operate the page because selectors broke, controls are not accessible, or a visual/system dialog blocks progress.
- 只有在 Playwright 因 selector 失效、控件不可访问、视觉或系统弹窗阻塞而无法操作页面时，才使用 Computer Use 兜底。
- Before claiming completion, run `chatgpt-codex builder smoke` or perform the equivalent real GPT `getWorkspaceStatus` Action test.
- 声称完成前，运行 `chatgpt-codex builder smoke`，或执行等价的真实 GPT `getWorkspaceStatus` Action 测试。

## Commands / 命令

Permissions template:

授权模板：

- `permissions.example.json` lives in the repository root and is safe to commit.
- `permissions.example.json` 位于仓库根目录，可以安全提交。
- The real local authorization file is `.chatgpt-codex/permissions.json` and is ignored by Git.
- 真实本机授权文件是 `.chatgpt-codex/permissions.json`，会被 Git 忽略。
- For manual editing, copy the template with `./scripts/prepare-permissions.sh` on macOS or `.\scripts\prepare-permissions.ps1` on Windows PowerShell.
- 如需手工编辑，macOS 用 `./scripts/prepare-permissions.sh` 复制模板，Windows PowerShell 用 `.\scripts\prepare-permissions.ps1`。
- If the user already provided answers, prefer `chatgpt-codex authorize` because it writes validated values.
- 如果用户已提供答案，优先使用 `chatgpt-codex authorize`，因为它会写入校验后的值。

AI-native management:

AI-native 管理：

- Start with `chatgpt-codex status` to read machine-readable local state.
- 先运行 `chatgpt-codex status` 读取机器可读的本地状态。
- `status` reports `node_found`, `npx_found`, and `builder_profile_path`; Node/npx are needed for Playwright Builder automation, not for the local server.
- `status` 会报告 `node_found`、`npx_found` 和 `builder_profile_path`；Node/npx 是 Playwright Builder 自动化需要的，本地服务本身不需要。
- Use `chatgpt-codex chatgpt-preflight` before browser setup. It prints plan prerequisites, login handoff commands, Builder automation boundaries, and Builder fields without printing the token.
- 浏览器配置前先用 `chatgpt-codex chatgpt-preflight`。它会打印套餐前提、登录交接命令、Builder 自动化边界和 Builder 字段，但不会打印 token。
- Use `chatgpt-codex builder payload --json`, `chatgpt-codex builder doctor`, `chatgpt-codex builder configure --mode ui`, `chatgpt-codex builder sniff`, and `chatgpt-codex builder smoke` for the Builder workflow.
- Builder 流程使用 `chatgpt-codex builder payload --json`、`chatgpt-codex builder doctor`、`chatgpt-codex builder configure --mode ui`、`chatgpt-codex builder sniff` 和 `chatgpt-codex builder smoke`。
- Use `chatgpt-codex builder open-login` when the user must log in. Open the Playwright browser, wait for the user to say login is complete, then continue with `chatgpt-codex builder doctor`.
- 用户需要登录时用 `chatgpt-codex builder open-login`。打开 Playwright 浏览器，等待用户确认登录完成，再用 `chatgpt-codex builder doctor` 继续。
- Use `chatgpt-codex ai-commands` to discover the local command catalog.
- 用 `chatgpt-codex ai-commands` 获取本地命令目录。
- Use `chatgpt-codex channel register --workspace <path> --public-base-url <url>` for first registration. It stores the public URL and token in `.chatgpt-codex/config.json` under the local repository root.
- 首次注册通道时使用 `chatgpt-codex channel register --workspace <path> --public-base-url <url>`。它会把公网 URL 和 token 存在本地仓库根目录的 `.chatgpt-codex/config.json`。
- Use `chatgpt-codex channel renew --public-base-url <url>` after a tunnel or custom route gives the final public URL.
- 隧道或自定义入口给出最终公网 URL 后，用 `chatgpt-codex channel renew --public-base-url <url>` 保存。
- Use `chatgpt-codex api-smoke` before browser work to test Action interfaces directly in temporary workspaces.
- 浏览器操作前用 `chatgpt-codex api-smoke` 在临时工作区直接测试 Action 接口。
- Use `chatgpt-codex serve` for normal personal use. Do not add a TTL unless the user explicitly wants a short-lived session.
- 普通个人自用时使用 `chatgpt-codex serve`。除非用户明确需要短时会话，否则不要添加 TTL。
- Use `chatgpt-codex channel status` for token-safe inspection, `chatgpt-codex channel revoke` when exposure should stop immediately, and `chatgpt-codex channel renew` to reactivate the channel.
- 用 `chatgpt-codex channel status` 做不泄露 token 的检查；需要立即停止暴露时用 `chatgpt-codex channel revoke`；需要重新激活时用 `chatgpt-codex channel renew`。
- Use `chatgpt-codex verify` for the final health/schema/read-only action check.
- 用 `chatgpt-codex verify` 做最终健康检查、schema 和只读 Action 验证。
- `status` reports whether a token exists but never prints the bearer token itself.
- `status` 只报告 token 是否存在，不打印 bearer token 原文。

Install on macOS:

macOS 安装：

```bash
./scripts/install.sh
. .venv/bin/activate
```

Install on Windows PowerShell:

Windows PowerShell 安装：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\install.ps1
. .\.venv\Scripts\Activate.ps1
```

Configure:

配置：

```bash
chatgpt-codex route-options
chatgpt-codex authorize \
  --workspace "$WORKSPACE" \
  --operating-system auto \
  --access-plan "$ACCESS_PLAN" \
  --public-base-url "$PUBLIC_BASE_URL" \
  --allow-browser-automation \
  --allow-start-services \
  --allow-install-helpers \
  --allow-workspace-write \
  --allow-command-execution
```

```bash
chatgpt-codex channel register --workspace "$WORKSPACE" --public-base-url "$PUBLIC_BASE_URL"
chatgpt-codex doctor
```

Optional additional authorized projects:

可选添加更多已授权项目：

```bash
chatgpt-codex workspace add --name "$PROJECT_NAME" --path "$PROJECT_PATH"
chatgpt-codex workspace list
```

Do not let ChatGPT switch to arbitrary paths. It may only use workspace names returned by `workspace_status`.

不要让 ChatGPT 切换到任意路径。它只能使用 `workspace_status` 返回的工作区名称。

Windows PowerShell:

Windows PowerShell：

```powershell
$Workspace = "C:\absolute\path\to\project"
$PublicBaseUrl = "https://actions.example.com"
chatgpt-codex channel register --workspace "$Workspace" --public-base-url "$PublicBaseUrl"
chatgpt-codex doctor
```

Access plan rules:

入口方案规则：

- `local-only`: no public HTTPS, no `cloudflared`, no domain; do not configure ChatGPT Actions.
- `local-only`：不需要公网 HTTPS、不需要 `cloudflared`、不需要域名；不要配置 ChatGPT Actions。
- `built-in-quick-tunnel`: public HTTPS required, `cloudflared` required, domain not required.
- `built-in-quick-tunnel`：需要公网 HTTPS，需要 `cloudflared`，不需要域名。
- `custom-domain`: public HTTPS required, domain required, `cloudflared` only if the user's routing choice uses it.
- `custom-domain`：需要公网 HTTPS，需要域名；只有用户选择的路由方式需要时才需要 `cloudflared`。
- `existing-https-route`: public HTTPS required, no `cloudflared` or new domain required.
- `existing-https-route`：需要公网 HTTPS；不需要 `cloudflared` 或新域名。

Agent route selection:

Agent 入口选择：

- Set `ACCESS_PLAN=built-in-quick-tunnel` when the user did not provide Cloudflare login plus a managed domain.
- 当用户没有提供 Cloudflare 登录和托管域名时，设置 `ACCESS_PLAN=built-in-quick-tunnel`。
- Set `ACCESS_PLAN=custom-domain` when both are available, and set `PUBLIC_BASE_URL=https://chatgpt-codex.<domain>`.
- 当两者都具备时，设置 `ACCESS_PLAN=custom-domain`，并设置 `PUBLIC_BASE_URL=https://chatgpt-codex.<domain>`。
- Set `ACCESS_PLAN=local-only` only for local tests or explicit user requests.
- 仅在本地测试或用户明确要求时设置 `ACCESS_PLAN=local-only`。

Start the local server:

启动本地服务：

```bash
chatgpt-codex serve
```

If the user chooses the built-in quick tunnel:

如果用户选择内置临时隧道：

```bash
chatgpt-codex tunnel
```

After the public URL is known:

拿到公网 URL 后：

```bash
chatgpt-codex channel renew --public-base-url "$PUBLIC_BASE_URL"
chatgpt-codex channel status
chatgpt-codex verify
```

If the user approved browser automation, use Playwright first:

如果用户已授权浏览器自动化，优先使用 Playwright：

```bash
chatgpt-codex chatgpt-preflight
chatgpt-codex builder open-login
chatgpt-codex builder doctor
chatgpt-codex builder configure --mode ui
chatgpt-codex builder smoke
```

Use `builder sniff` when you need to discover the ChatGPT Builder internal API shape. Replay only in the same Playwright browser context, then refresh and verify. Do not request or store ChatGPT credentials, cookies, or API keys. Computer Use is a fallback, not a default dependency.

需要发现 ChatGPT Builder 内部 API 形状时使用 `builder sniff`。replay 只能在同一个 Playwright 浏览器会话中进行，然后刷新并验证。不要索要或保存 ChatGPT 凭据、cookie 或 API key。Computer Use 是兜底，不是默认依赖。

In the GPT conversation, project switching flow is:

GPT 对话中的项目切换流程：

1. Call `getWorkspaceStatus` on demand: when the user asks about the current project, the active workspace is ambiguous, the user wants to switch projects, or a workspace-related Action fails.
2. When the user wants to switch projects, call `getWorkspaceStatus` first, then use `switchWorkspace` only with an authorized workspace name from that result.
3. At the start of real project work, proactively check the applicable `AGENTS.md` / `AGENTS.override.md` for the current scope.
4. If `execCommand` returns a running command session, continue with `pollCommand` instead of restarting the same command.

中文：

1. 按需调用 `getWorkspaceStatus`：当用户询问当前项目、当前 workspace 有歧义、要切换项目，或 workspace 相关 Action 异常时使用。
2. 用户要求切换项目时，先调用 `getWorkspaceStatus` 获取已授权 workspace，再用 `switchWorkspace` 切换。
3. 开始实质项目工作时，主动检查当前 scope 适用的 `AGENTS.md` / `AGENTS.override.md`。
4. 如果 `execCommand` 返回仍在运行的 command session，用 `pollCommand` 续读输出，不要重启同一个命令。

## Verification / 验证

Before saying setup is complete, verify. For local-only testing, use the local server URL. For ChatGPT web use, use the public HTTPS URL.

确认完成前，必须验证。仅本地测试时使用本地服务地址；ChatGPT 网页端真实使用时使用公网 HTTPS 地址。

Preferred AI-native verification:

优先使用 AI-native 验证：

```bash
chatgpt-codex api-smoke
chatgpt-codex channel status
chatgpt-codex verify
```

```bash
curl --noproxy '*' "$PUBLIC_BASE_URL/health"
curl --noproxy '*' "$PUBLIC_BASE_URL/openapi.json"
```

Windows PowerShell:

Windows PowerShell：

```powershell
curl.exe --noproxy "*" "$PublicBaseUrl/health"
curl.exe --noproxy "*" "$PublicBaseUrl/openapi.json"
```

Then test one authenticated read-only action:

然后测试一个带鉴权的只读 Action：

```bash
TOKEN="$(chatgpt-codex token)"
curl --noproxy '*' \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"path":".","recursive":false,"max_results":20}' \
  "$PUBLIC_BASE_URL/list_files"
```

Windows PowerShell:

Windows PowerShell：

```powershell
$Token = chatgpt-codex token
curl.exe --noproxy "*" `
  -H "Authorization: Bearer $Token" `
  -H "Content-Type: application/json" `
  -d '{"path":".","recursive":false,"max_results":20}' `
  "$PublicBaseUrl/list_files"
```

## Final Handoff / 最终交付

Print:

打印：

```bash
chatgpt-codex gpt-instructions
chatgpt-codex token
```

Tell the user to paste the token only into the ChatGPT Builder Action authentication field.

告诉用户只把 token 粘贴到 ChatGPT Builder 的 Action 鉴权字段。
