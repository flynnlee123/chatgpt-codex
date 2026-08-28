# GPT System Instructions Design / GPT 系统指令设计

## 背景

默认 system instructions 需要解决三件事：

1. 不要把 `getWorkspaceStatus` 变成每回合固定 preflight；
2. 要主动读取项目里的 `AGENTS.md` / `AGENTS.override.md`；
3. 对长命令只补充一条轻量协作规则，不再引入 `pollCommand` 这类额外接口语义。

新的设计目标是：**保留高价值工作方式约束，但避免把 prompt 写成一份 API 说明书。**

## 设计原则

- 按需调用工具，不做低价值仪式化步骤；
- 主动遵守项目内的 agent instructions；
- 文件和搜索工作优先用专用工具；
- 命令保持同步 `execCommand`；
- 长命令期间只要求稳定沟通节奏；
- 工具结果是事实源。

## Workspace Status

`getWorkspaceStatus` 保留，但改成按需调用。

推荐使用场景：

- 用户问当前项目；
- 当前 workspace 有歧义；
- 用户要求切换项目；
- workspace 相关 Action 失败，需要确认状态。

不建议把它写成固定流程：

```text
用户让我改文件
  -> 不需要先强制 getWorkspaceStatus
  -> 直接 list/read/search 即可
```

## AGENTS.md

agent 应主动发现并遵守适用的 `AGENTS.md` / `AGENTS.override.md`。

推荐语义：

- 开始一个 workspace 的实质项目工作时，先检查根目录是否存在适用的 instruction 文件；
- 如果任务进入更深子目录，再检查该 scope 是否有更深层规则；
- scope 不变时，不需要每回合重复读取；
- 当前聊天中的直接用户指令优先于仓库 instruction 文件。

不需要新增专用 Action。继续使用 `listFiles` / `readFile` 即可。

## Commands

命令模型保持简单：

```text
execCommand = run one synchronous command and return the final result
```

system instructions 不再需要解释：

```text
pollCommand
command_id
cursor
running session lifecycle
```

对命令工具只需要表达两件事：

- build、test、Git、package scripts 等适合用 `execCommand`；
- 用户要求原始日志时，保留 `stdout` / `stderr` 原文。

## Progress Reporting

关于长命令，system instructions 只保留这一条：

```text
When a command is taking a while, provide a brief progress update at least every 10 seconds.
```

这是协作要求，不是新的 API 设计。

含义是：

- agent 在等待长命令时要保持沟通；
- 进展更新可以很短，例如“still running, checking again shortly”；
- 不为了进度汇报增加新的 OpenAPI primitive。

## Recommended System Instruction Shape

最终默认 system instructions 应表达这些核心规则：

```text
1. Use getWorkspaceStatus on demand, not as a mandatory preflight.
2. Proactively read applicable AGENTS.md or AGENTS.override.md files.
3. Prefer dedicated file and search tools for source work.
4. Use execCommand for build, test, Git, and similar command-line workflows.
5. When a command is taking a while, provide a brief progress update at least every 10 seconds.
6. Preserve raw stdout/stderr when the user asks for raw logs.
7. Treat tool results as the source of truth.
8. Avoid destructive operations unless explicitly requested.
```

## OpenAPI Boundary

职责仍然保持清晰分工：

```text
OpenAPI
  -> action names
  -> request / response fields

System Instructions
  -> when to use which action
  -> how to combine tools
  -> how the agent should collaborate with the user
```

因此：

- `execCommand` 的同步返回结构由 OpenAPI 描述；
- 10 秒进展汇报规则放在 system instructions；
- `AGENTS.md` 的主动读取策略也放在 system instructions。

## Design Summary

```text
workspace status -> on demand
AGENTS.md        -> proactively discovered and followed
commands         -> synchronous execCommand only
progress UX      -> brief update at least every 10 seconds when waiting
raw logs         -> preserve stdout/stderr when requested
```

核心方向：**减少 prompt 里的流程负担，把高价值规则留给 system instructions，把接口细节留给 OpenAPI。**
