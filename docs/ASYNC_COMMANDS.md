# Command Execution Design / 命令执行设计

## 背景

之前尝试把 `execCommand` 扩展成“短等待 + `command_id` + `pollCommand`”的会话模型，但实际体验并没有比原始同步版更好。

主要问题是：

- Action 面变复杂了，GPT 需要理解 `command_id`、cursor、poll lifecycle；
- OpenAPI 和 system instructions 需要额外解释一整套状态机；
- 很多普通命令本来一次返回最终结果就够了，却被迫承担长任务设计成本；
- Builder 字段长度和模型使用成本都变高了。

因此新的方向是：**回到同步 `execCommand`，不再暴露 `pollCommand`。**

## 核心设计

Action 模型只保留：

```text
execCommand
```

语义保持简单：

```text
execCommand(command, cwd, timeout_seconds, max_stdout_bytes, max_stderr_bytes)
  -> wait until completion or timeout
  -> return final stdout, stderr, exit_code, and timed_out
```

服务端不再返回：

```text
command_id
status
pid
next_stdout_cursor
next_stderr_cursor
pollCommand
```

## 返回模型

`execCommand` 返回同步最终结果，重点字段保持为：

```text
command
cwd
exit_code
duration_ms
stdout
stderr
stdout_bytes
stderr_bytes
stdout_truncated
stderr_truncated
timed_out
```

规则：

- 非零退出码仍然是正常命令结果，不升级成 Action error；
- 超时通过 `timed_out` 和 `exit_code: null` 表达；
- `stdout` / `stderr` 保留原始文本；
- 截断只影响返回体大小，不改变真实 `stdout_bytes` / `stderr_bytes`。

## 为什么不保留 pollCommand

这次设计回退的核心判断是：当前产品更需要“稳定、低心智负担、容易写 prompt”，而不是“命令会话抽象”。

同步 `execCommand` 的优势：

- OpenAPI 更短，更容易被 Builder 接受；
- GPT 不需要学习额外 command session 语义；
- 服务端不需要维护跨请求命令状态；
- 调试时更直观，请求和结果是一一对应的。

代价也明确：

- 长命令期间不能通过第二个 Action 续读增量日志；
- GPT 不能依赖 API 自身实现命令级别的观察循环。

当前阶段接受这个 tradeoff。

## 长命令体验

长命令的用户体验不再通过 `pollCommand` 实现，而是通过 system instructions 约束 agent 的协作方式。

新的要求只有一条：

```text
When a command is taking a while, provide a brief progress update at least every 10 seconds.
```

也就是说：

- command 执行事实仍然由 `execCommand` 返回；
- 等待期间的沟通节奏由 agent 负责；
- 不为了“进度汇报”再引入 command session、cursor 或额外轮询接口。

## System Instructions 配套

system instructions 只需要轻量补充：

- `getWorkspaceStatus` 按需调用，不再每次 preflight；
- 主动读取适用的 `AGENTS.md` / `AGENTS.override.md`；
- 优先使用文件和搜索工具；
- 命令统一通过同步 `execCommand` 执行；
- 如果命令耗时较长，至少每 10 秒向用户汇报一次简短进展；
- 用户要求原始日志时，保留 `stdout` / `stderr` 原文。

## Scope

本轮不做：

```text
pollCommand
cancelCommand
command session persistence
incremental log cursors
process identity API
```

如果未来再次评估异步命令，应以新的独立设计重新讨论，而不是在当前接口上继续叠加。

## Design Summary

```text
command execution -> synchronous execCommand only
command identity  -> no public command session
progress UX       -> agent reports progress every 10 seconds when waiting
raw output        -> final stdout/stderr returned directly
server state      -> no cross-request command manager
```

核心原则：**把命令接口重新做回简单可靠的同步调用，把进度沟通留给 agent，而不是把 ChatGPT Actions 扩展成会话式终端。**
