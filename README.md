# ChatGPT Codex

[English](README.md) | [Chinese](README.zh-CN.md)

Use ChatGPT web as a ChatGPT local coding bridge through Custom GPT Actions.

The local server runs with only the Python standard library. ChatGPT web cannot reach `localhost` directly, so a public HTTPS route is required for real ChatGPT Actions use. The built-in `tunnel` command uses `cloudflared`; you can also provide your own HTTPS route.

## What It Does

- Works as an AI-native setup tool: give the repository to Codex or Claude, answer a few setup questions, then wait for it to configure and verify the bridge.
- Exposes a bearer-protected HTTP API for one registered local workspace.
- Lets a Custom GPT list, read, search, write, patch, and run commands in that workspace.
- Generates an OpenAPI document that ChatGPT Actions can import.
- Keeps all paths sandboxed under the configured workspace.
- Blocks common destructive shell commands by default.

## Requirements

- Supported OS: macOS and Windows.
- Python 3.9 or newer.
- Node.js/npm with `npx` for Playwright Builder automation. The local server itself does not require Node.
- A ChatGPT account or plan that can create Custom GPTs with Actions. Do not assume Free tier can create or edit GPTs; run `chatgpt-codex chatgpt-preflight` and check the Builder page after login.
- Local OS permission to read and write the workspace you configure.
- Optional: `cloudflared`, only for the built-in `chatgpt-codex tunnel` command.
- Optional: a Cloudflare-managed domain if you want a stable hostname such as `chatgpt-codex.example.com`.

## Minimal Human Inputs

- Human login to ChatGPT in the Playwright persistent profile is required. The agent must not ask for ChatGPT passwords, cookies, sessions, or API keys.
- Workspace path is required, for example `/Users/me/project/demo`.
- Browser human login to Cloudflare is optional, only for a stable Cloudflare-managed custom hostname.
- A Cloudflare-managed domain is optional. If provided, the fixed hostname is `chatgpt-codex.<domain>`.
- One local authorization is required: allow the agent to detect the OS, choose the route, install needed helpers, start the service, open the Playwright browser, configure Builder after human login, write the workspace, and execute commands inside the workspace.

Defaults: if no Cloudflare login and domain are provided, the agent uses a temporary HTTPS tunnel for ChatGPT web. If both are available, the agent may configure the stable hostname `chatgpt-codex.<domain>`. Local-only mode is for tests or explicit user requests.

## Skills Setup

Give this repository to Codex or Claude and ask it to use the bundled skill:

- [skills/chatgpt-codex/SKILL.md](skills/chatgpt-codex/SKILL.md)

Useful agent entry files:

- [AGENTS.md](AGENTS.md)
- [CLAUDE.md](CLAUDE.md)
- [docs/AI_NATIVE.md](docs/AI_NATIVE.md)

The same handoff can be printed from the CLI:

```bash
chatgpt-codex skill
chatgpt-codex ai-native
chatgpt-codex agent-brief
```

## Language

The CLI supports language selection for machine-readable status and command discovery:

```bash
chatgpt-codex --lang en status
chatgpt-codex --lang zh status
CHATGPT_CODEX_LANG=en chatgpt-codex ai-commands
CHATGPT_CODEX_LANG=zh chatgpt-codex ai-commands
```

The README is split by language. Use the links at the top of the file to switch between English and Chinese.

## Save Local Authorization

Before automation, save the user's setup choices and permissions in the repository-local `.chatgpt-codex/permissions.json`.

The root file `permissions.example.json` is a safe template. A user can copy it manually, or an AI agent can generate the real file with `chatgpt-codex authorize`.

macOS helper:

```bash
./scripts/prepare-permissions.sh
```

Windows PowerShell helper:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\prepare-permissions.ps1
```

Generate validated permissions:

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

Windows PowerShell:

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

## AI-Native CLI Management

Agents should use machine-readable commands first:

```bash
chatgpt-codex --lang en status
chatgpt-codex ai-commands
chatgpt-codex chatgpt-preflight
chatgpt-codex channel status
chatgpt-codex api-smoke
chatgpt-codex access status
chatgpt-codex set-public-url https://your-current-public-url
chatgpt-codex channel renew --public-base-url https://your-current-public-url
chatgpt-codex verify
```

`status` reports config paths, active workspace, registered workspaces, local/public URLs, helper availability, language, and whether a token is configured. It never prints the bearer token itself.

`ai-commands` prints the local command catalog for language selection, setup, inspection, workspace switching, Builder fields, runtime, and access lifecycle.

`chatgpt-preflight` prints the ChatGPT-side prerequisites, the login URL, the Builder automation boundary, and the exact Builder fields derived from the current local config without printing the bearer token.

`api-smoke` starts a temporary local server and tests the Action interfaces directly: auth, health, schema, workspace status/listing, bounded file listing, flat line-range and batch reads, contextual search, file write/patch, structured command execution, workspace switching, and safety blocks. It does not touch your real workspace.

## Builder Automation

The default Builder path is Playwright with a dedicated persistent profile. It does not reuse the user's daily Chrome profile, and the Chrome plugin is not a default dependency. The user logs in once inside the Playwright browser, then the saved GPT belongs to the user's ChatGPT account and is visible from normal browsers too.

Useful commands:

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

`builder payload --json` produces the GPT name, description, instructions, schema URL, privacy URL, visibility, and automation metadata without printing the bearer token.

`builder open-login` opens ChatGPT in the Playwright persistent profile. After the user logs in manually, `builder doctor` checks whether the Builder page loads and whether Actions appear available.

`builder configure --mode ui` prefills the GPT name, description, and instructions, then keeps the browser open and waits while you add the Action, paste the bearer token, set privacy/visibility, and save. When you open the saved GPT, it auto-captures the `https://chatgpt.com/g/...` URL into `.chatgpt-codex/builder.json` so `builder smoke` can run end to end. Adding the Action and pasting the token stay manual on purpose: the Builder UI for those steps has no stable controls. `builder configure --mode hybrid` does the same while also capturing redacted Builder network traffic. `builder sniff` is the explicit internal API discovery flow: perform one Builder save/configure action in the opened browser, press `Ctrl-C`, and the redacted route map is saved to `.chatgpt-codex/builder-routes.json`.

Internal API replay must stay inside the same Playwright browser context. Do not export cookies, sessions, or ChatGPT credentials. Treat internal routes as unstable acceleration data; if they do not validate, fall back to UI automation. Computer Use is the visual fallback for controls, dialogs, or page changes that Playwright cannot operate.

## Channel Lifecycle

First registration binds this local tool install to the exact workspace path you pass:

```bash
chatgpt-codex channel register \
  --workspace /absolute/path/to/your/project \
  --public-base-url https://chatgpt-codex.example.com
```

This stores the public URL, registered workspace path, active workspace name, and generated bearer token in `.chatgpt-codex/config.json` under this repository root. This is the normal local-secret pattern here: `.chatgpt-codex/` is ignored by Git, and config files are written as private files on macOS/Linux. Do not commit or publish it.

Lifecycle commands:

```bash
chatgpt-codex channel status
chatgpt-codex channel revoke
chatgpt-codex channel renew
chatgpt-codex channel renew --public-base-url https://new-public-url.example.com
chatgpt-codex channel renew --ttl-minutes 120
```

`channel status` never prints the token. `channel revoke` disables the channel immediately and rotates the token silently. `channel renew` reactivates access and prints the current token once for ChatGPT Builder.

Low-level commands are still available for advanced use: `chatgpt-codex rotate-token` prints a new token, and `chatgpt-codex access revoke` expires access and rotates the token without printing it.

## Closed-loop product flow

1. Collect minimal human inputs and local authorization.
2. Run `chatgpt-preflight`; if needed, open `builder open-login` and wait for the human to finish login in the Playwright persistent profile.
3. Run `builder doctor` and confirm the account can create or edit a GPT with Actions.
4. Install and run `channel register` to create `.chatgpt-codex/config.json`.
5. Register authorized workspaces and select `active_workspace`.
6. Start the local server.
7. Start or provide a public HTTPS route.
8. Save the final public URL with `channel renew --public-base-url <url>` or `set-public-url`.
9. Run `api-smoke` for direct interface testing, then `verify` against the running route.
10. Configure ChatGPT Builder with `builder configure --mode ui`, or use `builder sniff` plus `builder configure --mode api` after route validation.
11. In GPT chat, use `getWorkspaceStatus` and `switchWorkspace` before file or command work.

## Manual Setup

macOS Terminal:

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

Windows PowerShell:

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

If PowerShell blocks activation, run `Set-ExecutionPolicy -Scope Process Bypass -Force` in that terminal and retry activation.

By default, access stays active until the server is stopped or `chatgpt-codex channel revoke` is run. This is the recommended personal-use mode. If you intentionally want a short-lived session, start with `chatgpt-codex serve --ttl-minutes 120`.

## Public HTTPS Route

For ChatGPT web to call the local API, expose it through a public HTTPS route. With the built-in quick tunnel, run in another terminal:

```bash
chatgpt-codex tunnel
```

If you already have your own HTTPS route, point it at:

```text
http://127.0.0.1:8766
```

After the public URL is known:

```bash
chatgpt-codex api-smoke
chatgpt-codex channel renew --public-base-url https://your-current-public-url
chatgpt-codex channel status
chatgpt-codex verify
```

Route choices:

- `local-only`: no `cloudflared`, no domain, local testing only.
- `built-in-quick-tunnel`: requires `cloudflared`, no domain, gives a temporary public HTTPS URL.
- `custom-domain`: requires a domain, but this project does not require `cloudflared` unless your chosen routing does.
- `existing-https-route`: no `cloudflared` and no new domain if you already have a public HTTPS URL.

## Switching Projects In GPT

Register every project locally first. GPT can only switch between these authorized names; it cannot switch to an arbitrary path typed in chat.

```bash
chatgpt-codex workspace add --name demo --path /Users/me/project/demo --activate
chatgpt-codex workspace add --name notes --path "/Users/me/project/notes"
chatgpt-codex workspace list
```

In ChatGPT, the user can say:

```text
What is the current project?
Switch to notes.
List the current directory.
```

The GPT should call `getWorkspaceStatus` and `switchWorkspace`, then show the active local directory before file, code, or command work. `getWorkspaceStatus` includes the authorized workspace list.

## ChatGPT Builder Setup

If browser automation is approved in `.chatgpt-codex/permissions.json`, Codex should use Playwright first after the user logs in manually:

```bash
chatgpt-codex chatgpt-preflight
chatgpt-codex builder open-login
chatgpt-codex builder doctor
chatgpt-codex builder payload --json
chatgpt-codex builder configure --mode ui
chatgpt-codex builder smoke
```

The login step should be an explicit handoff: open the Playwright browser for the user, wait for them to finish, then inspect the Builder page. The local CLI cannot prove account eligibility by itself; the reliable check is whether `https://chatgpt.com/gpts/editor` loads and exposes the Configure and Actions controls. ChatGPT Builder configuration is web-only, so the local code generates and verifies the fields while Playwright fills the web editor.

For internal API discovery, run:

```bash
chatgpt-codex builder sniff
chatgpt-codex builder configure --mode api
```

This keeps replay inside the same Playwright browser context and validates by refreshing the Builder page. If validation fails, use `builder configure --mode ui` or Computer Use fallback.

Print the exact setup text:

```bash
chatgpt-codex gpt-instructions
```

In ChatGPT Builder:

1. Open `Explore GPTs` -> `Create`.
2. Paste the printed instructions into the GPT instructions.
3. Add an Action.
4. Authentication: `API key`.
5. Auth type: `Bearer`.
6. API key: output of `chatgpt-codex token`.
7. Import schema URL: `https://your-domain/openapi.json`.
8. Privacy policy: `https://your-domain/privacy`.
9. Save as `Only me` unless you intentionally want to share it.

## Available Actions

- `list_files`: list files and directories.
- `read_file`: read a UTF-8 file.
- `read_files`: read multiple known UTF-8 files in one call.
- `search_text`: search workspace text.
- `write_file`: create or replace a file.
- `apply_patch`: apply a limited `apply_patch` style patch.
- `exec_command`: run a shell command after safety checks.
- `workspace_status`: show the active workspace name and local path.
- `switch_workspace`: switch to an authorized workspace by name.

The filesystem primitives return structured byte counts and truncation metadata. `list_files` defaults to shallow listing (`recursive: false`) and supports bounded `max_depth` plus `include`/`exclude` globs; `read_file` supports optional flat `start_line`/`end_line` fields and line numbers; `read_files` keeps a structured `files` array with flat per-file `start_line`/`end_line` fields and applies per-file and total byte budgets; `search_text` supports case sensitivity, regex, globs, surrounding context, and output limits; `exec_command` reports duration, byte counts, output truncation, timeout state, and non-zero exit codes without turning them into Action errors.

The public Action response vocabulary is intentionally compact: file paths use `path`, file sizes use `size_bytes` and `returned_bytes`, selected line ranges use `start_line` and `end_line`, search matches use `matched_text` and `line_text`, `workspace_status` returns one `active_workspace` object, the authorized `workspaces` list, and `access`, and errors use `{error: {code, message}}`.

## Security Model

Detailed lifecycle notes live in [docs/SECURITY.md](docs/SECURITY.md).

This tool gives ChatGPT real access to a local workspace. Treat the bearer token like a password.

Built-in guardrails:

- All file paths must stay inside the configured workspace.
- Channel registration binds the tool to the specific workspace path recorded in `.chatgpt-codex/config.json`.
- Project switching is limited to workspaces registered in `.chatgpt-codex/config.json`.
- Hidden implementation state such as `.git`, `.venv`, `node_modules`, and caches are skipped by file listing and search.
- POST actions require `Authorization: Bearer <token>`.
- The public tunnel URL alone cannot run Actions. Without the bearer token, POST Actions return `401`.
- Personal-use access does not expire by default. Optional expiry is available with `serve --ttl-minutes` or `access grant --ttl-minutes`.
- `rotate-token` changes the bearer token; a running server reloads the token from config before each Action.
- `channel revoke` immediately expires access and rotates the token without printing the new secret; `channel renew` reactivates access and prints the token for Builder.
- Commands like `rm -rf` (in any flag order), `dd of=`, `find -delete`, `git reset --hard`, `sudo`, `reboot`, `mkfs`, and writes to raw disk devices are blocked. This deny-list is a best-effort guardrail, not a sandbox: with real shell access it can always be bypassed, so the actual safeguards are reviewing each Action in ChatGPT and running against one scoped workspace, never your home directory.
- The project never needs your ChatGPT password, cookies, or OpenAI API key.

Still important:

- Do not publish your `.chatgpt-codex/config.json`.
- Do not share a GPT that uses your private bearer token.
- Review action confirmations in ChatGPT before approving calls.
- Run it against one project workspace, not your home directory.

## Development

Run tests on macOS:

```bash
python3 -m unittest discover -s tests
```

Run tests on Windows PowerShell:

```powershell
py -3 -m unittest discover -s tests
```

Run without installing:

```bash
python3 -m chatgpt_codex --help
```

Windows PowerShell:

```powershell
py -3 -m chatgpt_codex --help
```

Stop the server and tunnel with `Ctrl-C` in their terminals.
