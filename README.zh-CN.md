# ChatGPT 本地编程桥

[English](README.md) | [简体中文](README.zh-CN.md)

通过 Custom GPT Actions，把 ChatGPT 网页版变成本地编程助手。

本地服务只依赖 Python 标准库即可运行。ChatGPT 网页端不能直接访问 `localhost`，所以真实使用 ChatGPT Actions 时需要一个公网 HTTPS 入口。内置 `tunnel` 命令使用 `cloudflared`；你也可以提供自己的 HTTPS 入口。

## 功能

- 作为 AI-native 配置工具使用：把仓库交给 Codex 或 Claude，回答少量配置问题，然后等待它完成配置和验证。
- 为一个已注册本地 workspace 暴露带 Bearer 鉴权的 HTTP API。
- 让自定义 GPT 可以在该 workspace 内列文件、读文件、搜索、写文件、打 patch、执行命令。
- 自动生成 ChatGPT Actions 可导入的 OpenAPI 文档。
- 所有路径都限制在配置的 workspace 内。
- 默认拦截常见危险命令。

## 环境要求

- 支持 macOS 和 Windows。
- Python 3.9 或更新版本。
- Builder 自动化需要带 `npx` 的 Node.js/npm。本地服务本身不需要 Node。
- 一个能创建带 Actions 的 Custom GPT 的 ChatGPT 账号或套餐。不要假设免费账号可以创建或编辑 GPT；先运行 `chatgpt-codex chatgpt-preflight`，并在登录后检查 Builder 页面。
- 本地系统允许该工具读写你配置的 workspace。
- 可选：`cloudflared`，仅用于内置 `chatgpt-codex tunnel` 命令。
- 可选：如果你想使用 `chatgpt-codex.example.com` 这类稳定域名，需要一个 Cloudflare 管理的域名。

## 真人必须提供的信息

- 在 Playwright 持久化 profile 中真人登录 ChatGPT：必须。Agent 不得索要 ChatGPT 密码、cookie、会话或 API key。
- Workspace 路径：必须，例如 `/Users/me/project/demo`。
- 浏览器真人登录 Cloudflare：可选，仅用于稳定的 Cloudflare 托管域名。
- Cloudflare 管理的域名：可选。如果提供，固定主机名是 `chatgpt-codex.<domain>`。
- 本地授权：允许 agent 自动识别系统、选择入口方案、安装必要辅助工具、启动服务、打开 Playwright 浏览器、在真人登录后配置 Builder、写入 workspace，并在 workspace 内执行命令。

默认行为：如果没有 Cloudflare 登录和域名，agent 使用临时 HTTPS 隧道供 ChatGPT 网页端访问。如果两者都具备，agent 可以配置稳定域名 `chatgpt-codex.<domain>`。仅本地模式只用于测试或用户明确要求。

## Skills 自动配置

把这个仓库交给 Codex 或 Claude，让它使用内置 skill：

- [skills/chatgpt-codex/SKILL.md](skills/chatgpt-codex/SKILL.md)

Agent 可读入口：

- [AGENTS.md](AGENTS.md)
- [CLAUDE.md](CLAUDE.md)
- [docs/AI_NATIVE.md](docs/AI_NATIVE.md)

也可以通过 CLI 打印交接说明：

```bash
chatgpt-codex skill
chatgpt-codex ai-native
chatgpt-codex agent-brief
```

## 语言

CLI 支持为机器可读状态和命令目录选择语言：

```bash
chatgpt-codex --lang en status
chatgpt-codex --lang zh status
CHATGPT_CODEX_LANG=en chatgpt-codex ai-commands
CHATGPT_CODEX_LANG=zh chatgpt-codex ai-commands
```

README 已按语言拆分。使用文件顶部链接在英文和中文之间切换。

## 保存本地授权

自动化之前，把用户的配置选项和授权保存到本仓库本地的 `.chatgpt-codex/permissions.json`。

根目录的 `permissions.example.json` 是安全模板。用户可以手动复制，也可以让 AI agent 用 `chatgpt-codex authorize` 生成真实文件。

macOS 辅助脚本：

```bash
./scripts/prepare-permissions.sh
```

Windows PowerShell 辅助脚本：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\prepare-permissions.ps1
```

生成校验后的授权文件：

```bash
chatgpt-codex authorize \
  --workspace /absolute/path/to/your/project \
  --operating-system auto \
  --access-plan built-in-quick-tunnel \
  --public-base-url https://temporary-or-stable-url.example.com \
  --allow-browser-automation \
  --allow-start-services \
  --allow-install-helpers \
  --allow-workspace-write \
  --allow-command-execution
```

Windows PowerShell：

```powershell
chatgpt-codex authorize `
  --workspace "C:\absolute\path\to\your\project" `
  --operating-system auto `
  --access-plan built-in-quick-tunnel `
  --public-base-url https://temporary-or-stable-url.example.com `
  --allow-browser-automation `
  --allow-start-services `
  --allow-install-helpers `
  --allow-workspace-write `
  --allow-command-execution
```

## AI-Native 本地命令管理

Agent 应优先使用机器可读命令：

```bash
chatgpt-codex --lang zh status
chatgpt-codex ai-commands
chatgpt-codex chatgpt-preflight
chatgpt-codex channel status
chatgpt-codex api-smoke
chatgpt-codex access status
chatgpt-codex set-public-url https://your-current-public-url
chatgpt-codex channel renew --public-base-url https://your-current-public-url
chatgpt-codex verify
```

`status` 会报告配置路径、当前 workspace、已注册 workspaces、本地/公网 URL、辅助工具状态、语言和 token 是否已配置。它永远不会打印 bearer token 原文。

`ai-commands` 会打印本地命令目录，覆盖语言选择、配置、检查、workspace 切换、Builder 字段、运行时和访问生命周期。

`chatgpt-preflight` 会打印 ChatGPT 侧前提条件、登录入口、Builder 自动化边界，以及从当前本地配置推导出的 Builder 字段；它不会打印 bearer token 原文。

`api-smoke` 会启动一个临时本地服务并直接测试 Action 接口：鉴权、健康检查、schema、workspace 状态/列表、有限深度文件列表、扁平行范围读取和批量读取、带上下文搜索、文件写入/补丁、结构化命令执行、workspace 切换和安全拦截。它不会触碰你的真实 workspace。

## Builder 自动化

默认 Builder 路径是 Playwright，并使用独立的持久化 profile。它不复用用户日常 Chrome profile，Chrome 插件不是默认依赖。用户只需要在 Playwright 浏览器里手动登录一次；GPT 保存后属于用户自己的 ChatGPT 账号，在普通浏览器里刷新也能看到。

常用命令：

```bash
chatgpt-codex builder profile-path
chatgpt-codex builder payload --json
chatgpt-codex builder open-login
chatgpt-codex builder doctor
chatgpt-codex builder configure --mode ui
chatgpt-codex builder configure --mode hybrid
chatgpt-codex builder sniff
chatgpt-codex builder smoke
```

`builder payload --json` 会生成 GPT 名称、描述、instructions、schema URL、privacy URL、可见性和自动化元数据，但不会打印 bearer token。

`builder open-login` 会用 Playwright 持久化 profile 打开 ChatGPT。用户手动登录后，`builder doctor` 检查 Builder 页面是否能加载，以及 Actions 是否可用。

`builder configure --mode ui` 会预填 GPT 名称、描述和 instructions，然后保持浏览器打开并等待你添加 Action、粘贴 bearer token、设置隐私/可见性并保存。当你打开保存后的 GPT 时，它会自动把 `https://chatgpt.com/g/...` 地址写入 `.chatgpt-codex/builder.json`，于是 `builder smoke` 能端到端运行。添加 Action 和粘贴 token 有意保留手动：Builder 这部分 UI 没有稳定控件。`builder configure --mode hybrid` 在此基础上同时捕获脱敏后的 Builder 网络流量。`builder sniff` 是显式内部 API 发现流程：在打开的浏览器里执行一次 Builder 保存或配置动作，然后按 `Ctrl-C`，脱敏后的 route map 会保存到 `.chatgpt-codex/builder-routes.json`。

内部 API replay 必须留在同一个 Playwright 浏览器会话中执行。不要导出 cookie、session 或 ChatGPT 凭据。内部路由只作为不稳定的加速数据；验证不通过就回退到 UI 自动化。Computer Use 是视觉兜底，只在 Playwright 无法操作控件、弹窗或页面变化时使用。

## 通道生命周期

首次注册会把当前本地工具安装绑定到你传入的指定 workspace 路径：

```bash
chatgpt-codex channel register \
  --workspace /absolute/path/to/your/project \
  --public-base-url https://chatgpt-codex.example.com
```

它会把公网 URL、已注册 workspace 路径、当前 workspace 名称和生成的 bearer token 存到本仓库根目录下的 `.chatgpt-codex/config.json`。这是本项目的正常本地密钥做法：`.chatgpt-codex/` 会被 Git 忽略，macOS/Linux 上配置文件会写成私有权限。不要提交或公开它。

生命周期命令：

```bash
chatgpt-codex channel status
chatgpt-codex channel revoke
chatgpt-codex channel renew
chatgpt-codex channel renew --public-base-url https://new-public-url.example.com
chatgpt-codex channel renew --ttl-minutes 120
```

`channel status` 永不打印 token。`channel revoke` 会立即停用通道并静默轮换 token。`channel renew` 会重新激活访问，并只为 ChatGPT Builder 打印一次当前 token。

底层命令仍保留给高级用法：`chatgpt-codex rotate-token` 会打印新 token，`chatgpt-codex access revoke` 会让访问过期并静默轮换 token。

## 产品闭环流程

1. 收集真人最小输入和本地授权。
2. 运行 `chatgpt-preflight`；如需登录，运行 `builder open-login` 打开 Playwright 持久化 profile，并等待真人完成登录。
3. 运行 `builder doctor`，确认账号可以创建或编辑带 Actions 的 GPT。
4. 安装并运行 `channel register` 创建 `.chatgpt-codex/config.json`。
5. 登记已授权 workspaces，并选择 `active_workspace`。
6. 启动本地服务。
7. 启动或提供公网 HTTPS 入口。
8. 用 `channel renew --public-base-url <url>` 或 `set-public-url` 保存最终公网 URL。
9. 先运行 `api-smoke` 做直接接口测试，再对运行中的入口运行 `verify`。
10. 用 `builder configure --mode ui` 配置 ChatGPT Builder，或在 route 验证后使用 `builder sniff` 加 `builder configure --mode api`。
11. 在 GPT 对话里，按需使用 `getWorkspaceStatus`，主动读取适用的 `AGENTS.md`，并在等待长命令时至少每 10 秒简要汇报一次进展。

## 手动配置

macOS 终端：

```bash
git clone git@github.com:hutiefang76/chatgpt-codex.git
cd chatgpt-codex
./scripts/install.sh
. .venv/bin/activate
chatgpt-codex channel register \
  --workspace /absolute/path/to/your/project \
  --public-base-url https://chatgpt-codex.example.com
chatgpt-codex serve
```

Windows PowerShell：

```powershell
git clone git@github.com:hutiefang76/chatgpt-codex.git
cd chatgpt-codex
powershell -ExecutionPolicy Bypass -File .\scripts\install.ps1
. .\.venv\Scripts\Activate.ps1
chatgpt-codex channel register `
  --workspace "C:\absolute\path\to\your\project" `
  --public-base-url https://chatgpt-codex.example.com
chatgpt-codex serve
```

如果 PowerShell 阻止激活脚本，在当前终端运行 `Set-ExecutionPolicy -Scope Process Bypass -Force`，然后重新激活。

默认情况下，访问会一直有效，直到服务停止或运行 `chatgpt-codex channel revoke`。这是推荐的个人自用模式。如果你明确想使用短时会话，可以用 `chatgpt-codex serve --ttl-minutes 120` 启动。

## 公网 HTTPS 入口

若要让 ChatGPT 网页端调用本地 API，需要通过公网 HTTPS 入口暴露服务。使用内置临时隧道时，在另一个终端运行：

```bash
chatgpt-codex tunnel
```

如果已有自己的 HTTPS 入口，把它指向：

```text
http://127.0.0.1:8766
```

拿到公网 URL 后：

```bash
chatgpt-codex api-smoke
chatgpt-codex channel renew --public-base-url https://your-current-public-url
chatgpt-codex channel status
chatgpt-codex verify
```

入口方案：

- `local-only`：不需要 `cloudflared`，不需要域名，仅本地测试。
- `built-in-quick-tunnel`：需要 `cloudflared`，不需要域名，提供临时公网 HTTPS URL。
- `custom-domain`：需要域名；本项目不强制 `cloudflared`，除非你的路由方案需要。
- `existing-https-route`：如果已有公网 HTTPS URL，不需要 `cloudflared`，也不需要新域名。

## 在 GPT 里切换项目

先在本地登记每个项目。GPT 只能在这些已授权名称之间切换，不能切换到对话里临时输入的任意路径。

```bash
chatgpt-codex workspace add --name demo --path /Users/me/project/demo --activate
chatgpt-codex workspace add --name notes --path "/Users/me/project/notes"
chatgpt-codex workspace list
```

在 ChatGPT 里，用户可以直接说：

```text
当前项目是什么？
切换到 notes
列一下当前目录
```

GPT 应在当前 workspace 相关、要切换项目，或 workspace 状态有歧义时调用 `getWorkspaceStatus`；只用它返回的已授权名称调用 `switchWorkspace`，并在切换后简要说明当前本地目录。开始实质项目工作时，应主动读取适用的 `AGENTS.md` 或 `AGENTS.override.md`。当命令执行时间较长时，等待期间至少每 10 秒给用户一个简短进展更新。

## ChatGPT Builder 配置

如果 `.chatgpt-codex/permissions.json` 已授权浏览器自动化，Codex 应在用户手动登录后优先使用 Playwright：

```bash
chatgpt-codex chatgpt-preflight
chatgpt-codex builder open-login
chatgpt-codex builder doctor
chatgpt-codex builder payload --json
chatgpt-codex builder configure --mode ui
chatgpt-codex builder smoke
```

登录步骤应该是明确的人机交接：先打开 Playwright 浏览器给用户，等用户完成登录，再检查 Builder 页面。本地 CLI 不能单独证明账号资格；可靠检查是 `https://chatgpt.com/gpts/editor` 是否能加载，并且是否显示 Configure 和 Actions 控件。ChatGPT Builder 配置是网页端能力，所以本地代码负责生成和验证字段，由 Playwright 填写网页编辑器。

如需发现内部 API，运行：

```bash
chatgpt-codex builder sniff
chatgpt-codex builder configure --mode api
```

这会把 replay 限制在同一个 Playwright 浏览器会话中，并通过刷新 Builder 页面验证。如果验证失败，使用 `builder configure --mode ui` 或 Computer Use 兜底。

打印要粘贴到 Builder 里的配置说明：

```bash
chatgpt-codex gpt-instructions
```

在 ChatGPT Builder 中：

1. 打开 `Explore GPTs` -> `Create`。
2. 把打印的内容粘贴到 GPT instructions。
3. 添加一个 Action。
4. Authentication 选择 `API key`。
5. Auth type 选择 `Bearer`。
6. API key 填入 `chatgpt-codex token` 输出的 token。
7. Import schema URL 填：`https://your-domain/openapi.json`。
8. Privacy policy 填：`https://your-domain/privacy`。
9. 保存时建议选择 `Only me`，除非你明确想共享它。

## 可用 Actions

- `list_files`：列出文件和目录。
- `read_file`：读取 UTF-8 文件。
- `read_files`：一次读取多个已知 UTF-8 文件。
- `search_text`：搜索 workspace 文本。
- `write_file`：创建或替换文件。
- `apply_patch`：应用受限的 `apply_patch` 风格补丁。
- `exec_command`：通过安全检查后执行 shell 命令。
- `workspace_status`：显示当前 workspace 名称和本地路径。
- `switch_workspace`：按名称切换到已授权 workspace。

文件系统 primitive 会返回结构化字节数和截断元数据。`list_files` 默认只列出浅层内容（`recursive: false`），并支持有限 `max_depth` 以及 `include`/`exclude` glob；`read_file` 支持扁平的可选 `start_line`/`end_line` 和行号；`read_files` 保留结构化 `files` 数组，但每个元素使用扁平的 `start_line`/`end_line`，并支持单文件与总字节预算；`search_text` 支持大小写、正则、glob、前后文和输出限制；`exec_command` 同步返回最终命令结果，包括耗时、字节数、输出截断、超时状态，非零退出码也作为正常命令结果返回。

公开 Action 返回字段保持精简且统一：文件路径统一使用 `path`，文件大小使用 `size_bytes` 和 `returned_bytes`，代码行范围使用 `start_line` 和 `end_line`，搜索命中使用 `matched_text` 和 `line_text`；`workspace_status` 返回一个 `active_workspace` 对象、授权 `workspaces` 列表和 `access`；错误统一为 `{error: {code, message}}`。

## 安全模型

更完整的生命周期说明见 [docs/SECURITY.md](docs/SECURITY.md)。

这个工具会让 ChatGPT 真正访问你的本地 workspace。请把 bearer token 当作密码保管。

内置防护：

- 所有文件路径必须位于配置的 workspace 内。
- 通道注册会把工具绑定到 `.chatgpt-codex/config.json` 中记录的指定 workspace 路径。
- 项目切换仅限 `.chatgpt-codex/config.json` 中登记过的 workspaces。
- 文件列表和搜索会跳过 `.git`、`.venv`、`node_modules`、缓存等实现细节目录。
- 所有 POST Actions 都要求 `Authorization: Bearer <token>`。
- 仅知道公网隧道地址不能执行 Actions。没有 bearer token 时，POST Actions 会返回 `401`。
- 个人自用模式默认不过期。如需可选过期，可使用 `serve --ttl-minutes` 或 `access grant --ttl-minutes`。
- `rotate-token` 会更换 bearer token；运行中的服务会在每次 Action 前从配置重新读取 token。
- `channel revoke` 会立即让访问过期，并轮换 token 但不打印新密钥；`channel renew` 会重新激活访问，并打印供 Builder 使用的 token。
- 默认拦截 `rm -rf`（任意 flag 顺序）、`dd of=`、`find -delete`、`git reset --hard`、`sudo`、`reboot`、`mkfs` 以及向裸磁盘设备写入等操作。这个黑名单只是尽力而为的防护栏、不是沙箱：有 shell 访问就总能绕过，所以真正的保障是在 ChatGPT 里逐个审查 Action，并只对单个受限 workspace 运行，绝不要对你的家目录运行。
- 本项目不需要你的 ChatGPT 密码、cookie 或 OpenAI API key。

仍然要注意：

- 不要公开 `.chatgpt-codex/config.json`。
- 不要共享使用你私人 bearer token 的 GPT。
- 在 ChatGPT 里确认 Action 调用前，先检查它要执行的内容。
- 只把它指向具体项目目录，不要直接指向 home 目录。

## 开发

macOS 运行测试：

```bash
python3 -m unittest discover -s tests
```

Windows PowerShell 运行测试：

```powershell
py -3 -m unittest discover -s tests
```

无需安装直接运行：

```bash
python3 -m chatgpt_codex --help
```

Windows PowerShell：

```powershell
py -3 -m chatgpt_codex --help
```

在对应终端按 `Ctrl-C` 停止 server 和 tunnel。
