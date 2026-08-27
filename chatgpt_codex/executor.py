import subprocess
import time
from pathlib import Path
from typing import Dict

from .security import CommandPolicy, PathSandbox


class CommandExecutor:
    """Run shell commands inside the workspace after safety checks.

    通过安全检查后，在 workspace 内执行 shell 命令。
    """

    def __init__(self, workspace: Path, policy=None):
        self.sandbox = PathSandbox(Path(workspace))
        self.policy = policy or CommandPolicy()

    def run(
        self,
        command: str,
        cwd: str = ".",
        timeout_seconds: int = 60,
        max_output: int = 20000,
        max_stdout_bytes=None,
        max_stderr_bytes=None,
    ) -> Dict[str, object]:
        safe_command = self.policy.validate(command)
        safe_cwd = self.sandbox.resolve(cwd)
        stdout_limit = max(1, int(max_stdout_bytes or max_output or 20000))
        stderr_limit = max(1, int(max_stderr_bytes or max_output or 20000))
        started = time.monotonic()
        timed_out = False
        exit_code = None
        stdout_raw = ""
        stderr_raw = ""
        try:
            completed = subprocess.run(
                safe_command,
                cwd=str(safe_cwd),
                shell=True,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=max(1, int(timeout_seconds or 60)),
            )
            exit_code = completed.returncode
            stdout_raw = _as_text(completed.stdout)
            stderr_raw = _as_text(completed.stderr)
        except subprocess.TimeoutExpired as exc:
            timed_out = True
            stdout_raw = _as_text(getattr(exc, "stdout", None) or getattr(exc, "output", None))
            stderr_raw = _as_text(getattr(exc, "stderr", None))

        stdout, stdout_truncated = _truncate(stdout_raw, stdout_limit)
        stderr, stderr_truncated = _truncate(stderr_raw, stderr_limit)
        duration_ms = int((time.monotonic() - started) * 1000)
        return {
            "command": safe_command,
            "cwd": str(safe_cwd),
            "exit_code": exit_code,
            "duration_ms": duration_ms,
            "stdout": stdout,
            "stderr": stderr,
            "stdout_bytes": _utf8_size(stdout_raw),
            "stderr_bytes": _utf8_size(stderr_raw),
            "stdout_truncated": stdout_truncated,
            "stderr_truncated": stderr_truncated,
            "timed_out": timed_out,
        }


def _as_text(value) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return str(value)


def _utf8_size(value: str) -> int:
    return len(value.encode("utf-8"))


def _truncate(value: str, max_output: int):
    limit = max(1, int(max_output or 20000))
    data = value.encode("utf-8")
    if len(data) <= limit:
        return value, False
    return data[:limit].decode("utf-8", errors="ignore"), True
