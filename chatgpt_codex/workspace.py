import fnmatch
import json
import os
import re
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence

from .security import PathSandbox


# Skip implementation details and heavyweight dependency/cache folders by
# default so ChatGPT sees the project, not tool internals.
# 默认跳过实现细节和较重的依赖/缓存目录，让 ChatGPT 看到项目本身。
IGNORED_NAMES = {
    ".DS_Store",
    ".git",
    ".hg",
    ".mypy_cache",
    ".pytest_cache",
    ".svn",
    ".venv",
    "__pycache__",
    "node_modules",
    "venv",
}

DEFAULT_READ_MAX_BYTES = 200000
DEFAULT_BATCH_MAX_BYTES_PER_FILE = 30000
DEFAULT_BATCH_MAX_TOTAL_BYTES = 100000
DEFAULT_SEARCH_MAX_OUTPUT_BYTES = 200000


class WorkspaceTools:
    """File, search, patch, and write tools scoped to one workspace.

    限定在单个 workspace 内的文件、搜索、补丁和写入工具。
    """

    def __init__(self, workspace: Path):
        self.sandbox = PathSandbox(Path(workspace))
        self.workspace = self.sandbox.workspace

    def list_files(
        self,
        path: str = ".",
        recursive: bool = False,
        pattern: str = "*",
        max_results: int = 200,
        max_depth: Optional[int] = None,
        include: Optional[Sequence[str]] = None,
        exclude: Optional[Sequence[str]] = None,
    ) -> Dict[str, object]:
        root = self.sandbox.resolve(path)
        entries: List[Dict[str, object]] = []
        max_results = max(1, int(max_results or 200))
        if max_depth is not None and int(max_depth) < 0:
            raise ValueError("max_depth must be non-negative")

        for candidate in self._walk(
            root,
            recursive=bool(recursive),
            max_depth=None if max_depth is None else int(max_depth),
            exclude=exclude,
        ):
            relative = self.sandbox.relative(candidate)
            if (
                relative == "."
                or self._is_ignored(candidate)
                or not _glob_matches(relative, pattern or "*")
                or not _matches_include(relative, include)
                or _matches_exclude(relative, exclude)
            ):
                continue
            stat = candidate.stat()
            depth = _relative_depth(candidate, root)
            entries.append(
                {
                    "path": relative,
                    "type": "directory" if candidate.is_dir() else "file",
                    "size_bytes": stat.st_size if candidate.is_file() else 0,
                    "modified": int(stat.st_mtime),
                    "depth": depth,
                }
            )

        entries.sort(key=lambda item: item["path"])
        total_entries = len(entries)
        returned_entries = entries[:max_results]
        response = {
            "path": self.sandbox.relative(root),
            "entries": returned_entries,
            "total_entries": total_entries,
            "returned_entries": len(returned_entries),
            "truncated": total_entries > max_results,
        }
        if total_entries > max_results:
            response["truncation_reason"] = "max_results"
        return response

    def read_file(
        self,
        path: str,
        max_bytes: int = DEFAULT_READ_MAX_BYTES,
        start_line: Optional[int] = None,
        end_line: Optional[int] = None,
        line_numbers: bool = False,
    ) -> Dict[str, object]:
        target = self.sandbox.resolve(path)
        return self._read_file_target(target, max_bytes, start_line, end_line, line_numbers)

    def read_files(
        self,
        files: Sequence[Dict[str, object]],
        max_bytes_per_file: int = DEFAULT_BATCH_MAX_BYTES_PER_FILE,
        max_total_bytes: int = DEFAULT_BATCH_MAX_TOTAL_BYTES,
        line_numbers: bool = False,
    ) -> Dict[str, object]:
        if not isinstance(files, (list, tuple)):
            raise ValueError("files must be an array")

        per_file_limit = max(1, int(max_bytes_per_file or DEFAULT_BATCH_MAX_BYTES_PER_FILE))
        total_limit = max(1, int(max_total_bytes or DEFAULT_BATCH_MAX_TOTAL_BYTES))
        specs = []
        for item in files:
            if not isinstance(item, dict) or not item.get("path"):
                raise ValueError("each files item must contain a path")
            specs.append(item)

        def read_one(item: Dict[str, object]) -> Dict[str, object]:
            requested_path = str(item["path"])
            try:
                target = self.sandbox.resolve(requested_path)
                if not target.exists():
                    return {
                        "path": self.sandbox.relative(target),
                        "exists": False,
                        "truncated": False,
                        "error": _error_info("file_not_found", "file does not exist"),
                    }
                if not target.is_file():
                    return {
                        "path": self.sandbox.relative(target),
                        "exists": True,
                        "truncated": False,
                        "error": _error_info("not_a_file", "path is not a file"),
                    }
                start_line = _optional_int(item.get("start_line"))
                end_line = _optional_int(item.get("end_line"))
                result = self._read_file_target(
                    target,
                    per_file_limit,
                    start_line,
                    end_line,
                    bool(line_numbers),
                )
                if result.get("truncation_reason") == "max_bytes":
                    result["truncation_reason"] = "max_bytes_per_file"
                result["exists"] = True
                return result
            except ValueError as exc:
                return {
                    "path": requested_path,
                    "exists": False,
                    "truncated": False,
                    "error": _error_info(
                        "path_outside_workspace" if "outside workspace" in str(exc) else "invalid_request",
                        "path is outside workspace" if "outside workspace" in str(exc) else str(exc),
                    ),
                }
            except FileNotFoundError:
                return {
                    "path": requested_path,
                    "exists": False,
                    "truncated": False,
                    "error": _error_info("file_not_found", "file does not exist"),
                }
            except OSError as exc:
                return {
                    "path": requested_path,
                    "exists": False,
                    "truncated": False,
                    "error": _error_info("file_read_error", str(exc)),
                }

        if not specs:
            return {
                "files": [],
                "total_returned_bytes": 0,
                "truncated": False,
            }

        with ThreadPoolExecutor(max_workers=min(8, len(specs))) as pool:
            results = list(pool.map(read_one, specs))

        total_returned_bytes = 0
        total_truncated = False
        total_truncation_reason = ""
        for result in results:
            content = result.get("content")
            if not isinstance(content, str):
                continue
            original_returned = _utf8_size(content)
            remaining = max(0, total_limit - total_returned_bytes)
            if original_returned > remaining:
                result["content"] = _truncate_utf8(content, remaining)[0]
                result["returned_bytes"] = _utf8_size(result["content"])
                result["truncated"] = True
                result["truncation_reason"] = "max_total_bytes"
                total_truncated = True
                total_truncation_reason = "max_total_bytes"
            total_returned_bytes += int(result.get("returned_bytes", 0))
            if result.get("truncated"):
                total_truncated = True
                if not total_truncation_reason:
                    total_truncation_reason = str(result.get("truncation_reason") or "max_bytes_per_file")

        response = {
            "files": results,
            "total_returned_bytes": total_returned_bytes,
            "truncated": total_truncated,
        }
        if total_truncated:
            response["truncation_reason"] = total_truncation_reason or "max_bytes_per_file"
        return response

    def _read_file_target(
        self,
        target: Path,
        max_bytes: int,
        start_line: Optional[int],
        end_line: Optional[int],
        line_numbers: bool,
    ) -> Dict[str, object]:
        start_line, end_line = _validate_line_range(start_line, end_line)
        data = target.read_bytes()
        decoded = data.decode("utf-8", errors="replace")
        lines = decoded.splitlines(keepends=True)
        selected = decoded
        response: Dict[str, object] = {
            "path": self.sandbox.relative(target),
            "content": "",
            "size_bytes": len(data),
            "returned_bytes": 0,
            "truncated": False,
        }

        if start_line is not None or end_line is not None:
            selected_start = start_line or 1
            selected_end = len(lines) if end_line is None else min(end_line, len(lines))
            if selected_start <= selected_end:
                selected_lines = lines[selected_start - 1 : selected_end]
                if line_numbers:
                    selected = "".join(
                        f"{number} | {line}"
                        for number, line in enumerate(selected_lines, start=selected_start)
                    )
                else:
                    selected = "".join(selected_lines)
            else:
                selected = ""
            response["start_line"] = selected_start
            response["end_line"] = selected_end
        elif line_numbers:
            selected = "".join(
                f"{number} | {line}"
                for number, line in enumerate(lines, start=1)
            )

        content, truncated = _truncate_utf8(selected, max(1, int(max_bytes or DEFAULT_READ_MAX_BYTES)))
        response["content"] = content
        response["returned_bytes"] = _utf8_size(content)
        response["truncated"] = truncated
        if truncated:
            response["truncation_reason"] = "max_bytes"
        return response

    def write_file(self, path: str, content: str) -> Dict[str, object]:
        target = self.sandbox.resolve(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        data = (content or "").encode("utf-8")
        target.write_bytes(data)
        return {
            "path": self.sandbox.relative(target),
            "bytes_written": len(data),
        }

    def search_text(
        self,
        query: str,
        path: str = ".",
        max_results: int = 100,
        regex: bool = False,
        case_sensitive: bool = True,
        include: Optional[Sequence[str]] = None,
        exclude: Optional[Sequence[str]] = None,
        context_before: int = 0,
        context_after: int = 0,
        max_output_bytes: int = DEFAULT_SEARCH_MAX_OUTPUT_BYTES,
    ) -> Dict[str, object]:
        if not query:
            raise ValueError("query is required")
        root = self.sandbox.resolve(path)
        max_results = max(1, int(max_results or 100))
        context_before = max(0, int(context_before or 0))
        context_after = max(0, int(context_after or 0))
        max_output_bytes = max(1, int(max_output_bytes or DEFAULT_SEARCH_MAX_OUTPUT_BYTES))
        flags = 0 if case_sensitive else re.IGNORECASE
        matcher = re.compile(query if regex else re.escape(query), flags=flags)
        matches: List[Dict[str, object]] = []
        total_matches = 0
        max_results_exceeded = False
        output_limit_reached = False

        for candidate in self._walk(root, recursive=True, exclude=exclude):
            if candidate.is_dir() or self._is_ignored(candidate):
                continue
            relative = self.sandbox.relative(candidate)
            if not _matches_include(relative, include) or _matches_exclude(relative, exclude):
                continue
            try:
                lines = candidate.read_text(encoding="utf-8").splitlines()
            except (UnicodeDecodeError, OSError):
                continue
            for line_number, line in enumerate(lines, start=1):
                for found in matcher.finditer(line):
                    total_matches += 1
                    if len(matches) >= max_results:
                        max_results_exceeded = True
                        continue
                    if output_limit_reached:
                        continue
                    match: Dict[str, object] = {
                        "path": relative,
                        "line": line_number,
                        "column": found.start() + 1,
                        "matched_text": found.group(0),
                        "line_text": line,
                    }
                    if context_before or context_after:
                        context_start = max(1, line_number - context_before)
                        context_end = min(len(lines), line_number + context_after)
                        match["context"] = [
                            {
                                "line": number,
                                "text": lines[number - 1],
                                "is_match": number == line_number,
                            }
                            for number in range(context_start, context_end + 1)
                        ]
                    candidate_matches = matches + [match]
                    if _search_payload_size(query, candidate_matches) > max_output_bytes:
                        output_limit_reached = True
                        continue
                    matches.append(match)

        truncated = max_results_exceeded or output_limit_reached
        response: Dict[str, object] = {
            "query": query,
            "matches": matches,
            "total_matches": total_matches,
            "returned_matches": len(matches),
            "truncated": truncated,
        }
        if truncated:
            response["truncation_reason"] = "max_output_bytes" if output_limit_reached else "max_results"
        return response

    def apply_patch(self, patch: str) -> Dict[str, object]:
        operations = _parse_patch(patch)
        changed: List[str] = []
        for operation in operations:
            op_type = operation["type"]
            target = self.sandbox.resolve(operation["path"])
            relative = self.sandbox.relative(target)
            if op_type == "add":
                if target.exists():
                    raise ValueError(f"file already exists: {relative}")
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text("\n".join(operation["lines"]) + "\n", encoding="utf-8")
            elif op_type == "delete":
                target.unlink()
            elif op_type == "update":
                original = target.read_text(encoding="utf-8").splitlines()
                updated = _apply_hunks(original, operation["hunks"], relative)
                target.write_text("\n".join(updated) + "\n", encoding="utf-8")
            else:
                raise ValueError(f"unsupported patch operation: {op_type}")
            changed.append(relative)
        return {"changed_files": changed}

    def _walk(
        self,
        root: Path,
        recursive: bool,
        max_depth: Optional[int] = None,
        exclude: Optional[Sequence[str]] = None,
    ) -> Iterable[Path]:
        if root.is_file():
            yield root
            return

        effective_max_depth = max_depth
        if not recursive:
            effective_max_depth = 1 if max_depth is None else min(1, max_depth)
        for current_root, dirs, files in os.walk(root):
            current = Path(current_root)
            current_depth = _relative_depth(current, root)
            dirs[:] = sorted(
                name
                for name in dirs
                if name not in IGNORED_NAMES
                and (effective_max_depth is None or current_depth < effective_max_depth)
                and not _matches_exclude(self.sandbox.relative(current / name), exclude)
            )
            for dirname in dirs:
                yield current / dirname
            if effective_max_depth is not None and current_depth >= effective_max_depth:
                continue
            for filename in sorted(files):
                if filename not in IGNORED_NAMES:
                    yield current / filename

    def _is_ignored(self, path: Path) -> bool:
        return any(part in IGNORED_NAMES for part in path.relative_to(self.workspace).parts)


def _optional_int(value: Any) -> Optional[int]:
    if value is None or value == "":
        return None
    return int(value)


def _error_info(code: str, message: str) -> Dict[str, str]:
    return {"code": code, "message": message}


def _validate_line_range(start_line: Optional[int], end_line: Optional[int]):
    start = None if start_line is None else int(start_line)
    end = None if end_line is None else int(end_line)
    if start is not None and start < 1:
        raise ValueError("start_line must be at least 1")
    if end is not None and end < 1:
        raise ValueError("end_line must be at least 1")
    if start is not None and end is not None and start > end:
        raise ValueError("start_line must be less than or equal to end_line")
    return start, end


def _utf8_size(value: str) -> int:
    return len(value.encode("utf-8"))


def _truncate_utf8(value: str, max_bytes: int):
    limit = max(0, int(max_bytes or 0))
    data = value.encode("utf-8")
    if len(data) <= limit:
        return value, False
    if limit == 0:
        return "", True
    return data[:limit].decode("utf-8", errors="ignore"), True


def _relative_depth(path: Path, root: Path) -> int:
    try:
        return len(path.relative_to(root).parts)
    except ValueError:
        return 0


def _normalize_glob(pattern: str) -> str:
    normalized = str(pattern or "*").replace("\\", "/")
    while normalized.startswith("./"):
        normalized = normalized[2:]
    return normalized or "*"


def _glob_matches(relative: str, pattern: str) -> bool:
    candidate = relative.replace("\\", "/")
    normalized = _normalize_glob(pattern)
    if normalized.endswith("/**") and candidate == normalized[:-3].rstrip("/"):
        return True
    if fnmatch.fnmatchcase(candidate, normalized):
        return True
    # Python's fnmatch does not treat **/ as matching an empty directory
    # prefix, so make **/*.ts also match a root-level foo.ts.
    if normalized.startswith("**/") and fnmatch.fnmatchcase(candidate, normalized[3:]):
        return True
    # A basename-only glob is useful for both listFiles and searchText and
    # preserves the old listFiles pattern behavior.
    if "/" not in normalized and fnmatch.fnmatchcase(Path(candidate).name, normalized):
        return True
    return False


def _matches_include(relative: str, patterns: Optional[Sequence[str]]) -> bool:
    normalized = [str(pattern) for pattern in (patterns or []) if str(pattern)]
    return not normalized or any(_glob_matches(relative, pattern) for pattern in normalized)


def _matches_exclude(relative: str, patterns: Optional[Sequence[str]]) -> bool:
    return any(_glob_matches(relative, pattern) for pattern in (patterns or []) if str(pattern))


def _search_payload_size(query: str, matches: Sequence[Dict[str, object]]) -> int:
    payload = {
        "query": query,
        "matches": list(matches),
        "total_matches": len(matches),
        "returned_matches": len(matches),
        "truncated": False,
    }
    return len(json.dumps(payload, ensure_ascii=False).encode("utf-8"))


def _parse_patch(patch: str) -> List[Dict[str, object]]:
    """Parse a small, deterministic subset of apply_patch syntax.

    解析一个小而确定的 apply_patch 语法子集。
    """

    lines = patch.splitlines()
    if not lines or lines[0] != "*** Begin Patch" or lines[-1] != "*** End Patch":
        raise ValueError("patch must start with *** Begin Patch and end with *** End Patch")
    operations: List[Dict[str, object]] = []
    index = 1
    while index < len(lines) - 1:
        line = lines[index]
        if line.startswith("*** Add File: "):
            path = line.removeprefix("*** Add File: ")
            index += 1
            added: List[str] = []
            while index < len(lines) - 1 and not lines[index].startswith("*** "):
                if not lines[index].startswith("+"):
                    raise ValueError("add file lines must start with +")
                added.append(lines[index][1:])
                index += 1
            operations.append({"type": "add", "path": path, "lines": added})
        elif line.startswith("*** Delete File: "):
            path = line.removeprefix("*** Delete File: ")
            operations.append({"type": "delete", "path": path})
            index += 1
        elif line.startswith("*** Update File: "):
            path = line.removeprefix("*** Update File: ")
            index += 1
            hunks: List[List[str]] = []
            while index < len(lines) - 1 and not lines[index].startswith("*** "):
                if lines[index] != "@@":
                    raise ValueError("update hunk must start with @@")
                index += 1
                hunk: List[str] = []
                while index < len(lines) - 1 and not lines[index].startswith("*** ") and lines[index] != "@@":
                    hunk.append(lines[index])
                    index += 1
                hunks.append(hunk)
            operations.append({"type": "update", "path": path, "hunks": hunks})
        else:
            raise ValueError(f"unknown patch operation: {line}")
    return operations


def _apply_hunks(original: Sequence[str], hunks: Sequence[Sequence[str]], path: str) -> List[str]:
    """Apply context hunks exactly; fuzzy patching would be too surprising.

    精确应用上下文 hunk；模糊匹配补丁容易产生意外结果。
    """

    output = list(original)
    search_start = 0
    for hunk in hunks:
        old_segment = [line[1:] for line in hunk if line.startswith((" ", "-"))]
        new_segment = [line[1:] for line in hunk if line.startswith((" ", "+"))]
        position = _find_segment(output, old_segment, search_start)
        if position < 0:
            raise ValueError(f"patch context not found in {path}")
        output[position : position + len(old_segment)] = new_segment
        search_start = position + len(new_segment)
    return output


def _find_segment(lines: Sequence[str], segment: Sequence[str], start: int) -> int:
    if not segment:
        return start
    for index in range(start, len(lines) - len(segment) + 1):
        if list(lines[index : index + len(segment)]) == list(segment):
            return index
    return -1
