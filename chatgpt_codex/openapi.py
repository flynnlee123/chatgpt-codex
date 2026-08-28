from typing import Dict


def make_openapi_document(public_base_url: str) -> Dict[str, object]:
    """Build the OpenAPI document imported by ChatGPT Actions.

    构建供 ChatGPT Actions 导入的 OpenAPI 文档。
    """

    base_url = public_base_url.rstrip("/")
    return {
        "openapi": "3.1.0",
        "info": {
            "title": "ChatGPT Codex Local Actions",
            "version": "0.5.0",
            "description": "Local workspace coding actions for a user-owned ChatGPT Custom GPT. / 给用户自己的 Custom GPT 使用的本地工作区编程 Actions。",
        },
        "servers": [{"url": base_url}],
        "paths": {
            "/health": {"get": {"operationId": "health", "responses": {"200": _json_response("Health", "HealthResult")}}},
            "/openapi.json": {"get": {"operationId": "openapi", "responses": {"200": {"description": "OpenAPI document"}}}},
            "/privacy": {"get": {"operationId": "privacy", "responses": {"200": {"description": "Privacy policy"}}}},
            "/workspace_status": {
                "post": {
                    "operationId": "getWorkspaceStatus",
                    "summary": "Show the active local workspace and all authorized workspaces.",
                    "x-openai-isConsequential": False,
                    "security": [{"bearerAuth": []}],
                    "requestBody": _optional_request_body("EmptyRequest"),
                    "responses": _action_responses("Workspace status", "WorkspaceStatusResult"),
                }
            },
            "/switch_workspace": {
                "post": {
                    "operationId": "switchWorkspace",
                    "summary": "Switch the active workspace by authorized workspace name.",
                    "security": [{"bearerAuth": []}],
                    "requestBody": _request_body("SwitchWorkspaceRequest"),
                    "responses": _action_responses("Workspace status", "WorkspaceStatusResult"),
                }
            },
            "/list_files": {
                "post": {
                    "operationId": "listFiles",
                    "summary": "List files and directories inside the active workspace with bounded depth and include/exclude globs. Use shallow depth first when exploring an unfamiliar project.",
                    "x-openai-isConsequential": False,
                    "security": [{"bearerAuth": []}],
                    "requestBody": _request_body("ListFilesRequest"),
                    "responses": _action_responses("File listing", "FileListingResult"),
                }
            },
            "/read_file": {
                "post": {
                    "operationId": "readFile",
                    "summary": "Read a UTF-8 file inside the active workspace. Supports optional line ranges for reading only the relevant section of large source files. Prefer line ranges after locating a symbol with searchText.",
                    "x-openai-isConsequential": False,
                    "security": [{"bearerAuth": []}],
                    "requestBody": _request_body("ReadFileRequest"),
                    "responses": _action_responses("File content", "ReadFileResult"),
                }
            },
            "/read_files": {
                "post": {
                    "operationId": "readFiles",
                    "summary": "Read multiple known UTF-8 workspace files in one call. Prefer this over repeated readFile calls when several independent files need to be inspected together.",
                    "x-openai-isConsequential": False,
                    "security": [{"bearerAuth": []}],
                    "requestBody": _request_body("ReadFilesRequest"),
                    "responses": _action_responses("Batch file content", "ReadFilesResult"),
                }
            },
            "/search_text": {
                "post": {
                    "operationId": "searchText",
                    "summary": "Recursively search text inside workspace files with regex, include/exclude globs, surrounding context, and bounded results. Prefer this over execCommand with rg for normal source-code searches.",
                    "x-openai-isConsequential": False,
                    "security": [{"bearerAuth": []}],
                    "requestBody": _request_body("SearchTextRequest"),
                    "responses": _action_responses("Search results", "SearchResult"),
                }
            },
            "/write_file": {
                "post": {
                    "operationId": "writeFile",
                    "summary": "Create or replace a UTF-8 file inside the workspace.",
                    "x-openai-isConsequential": False,
                    "security": [{"bearerAuth": []}],
                    "requestBody": _request_body("WriteFileRequest"),
                    "responses": _action_responses("Write result", "WriteFileResult"),
                }
            },
            "/apply_patch": {
                "post": {
                    "operationId": "applyPatch",
                    "summary": "Apply a limited apply_patch-style patch inside the workspace.",
                    "x-openai-isConsequential": False,
                    "security": [{"bearerAuth": []}],
                    "requestBody": _request_body("PatchRequest"),
                    "responses": _action_responses("Patch result", "PatchResult"),
                }
            },
            "/exec_command": {
                "post": {
                    "operationId": "execCommand",
                    "summary": "Run a shell command inside the active workspace after safety checks and return the final stdout, stderr, exit code, and timeout state.",
                    "x-openai-isConsequential": False,
                    "security": [{"bearerAuth": []}],
                    "requestBody": _request_body("CommandRequest"),
                    "responses": _action_responses("Command result", "CommandResult"),
                }
            },
        },
        "components": {
            "securitySchemes": {
                "bearerAuth": {"type": "http", "scheme": "bearer"},
            },
            "schemas": _schemas(),
        },
    }


def _request_body(schema_name: str) -> Dict[str, object]:
    return {
        "required": True,
        "content": {"application/json": {"schema": {"$ref": f"#/components/schemas/{schema_name}"}}},
    }


def _optional_request_body(schema_name: str) -> Dict[str, object]:
    body = _request_body(schema_name)
    body["required"] = False
    return body


def _json_response(description: str, schema_name: str) -> Dict[str, object]:
    return {
        "description": description,
        "content": {"application/json": {"schema": {"$ref": f"#/components/schemas/{schema_name}"}}},
    }


def _action_responses(description: str, schema_name: str) -> Dict[str, object]:
    return {
        "200": _json_response(description, schema_name),
        "default": _json_response("Action error", "ErrorResult"),
    }


def _schemas() -> Dict[str, object]:
    return {
        "HealthResult": _object(
            {
                "ok": {"type": "boolean"},
                "active_workspace": {"type": "string"},
                "public_base_url": {"type": "string"},
                "access": {"$ref": "#/components/schemas/AccessStatus"},
            }
        ),
        "EmptyRequest": _object({}),
        "WorkspaceEntry": _object(
            {
                "name": {"type": "string"},
                "path": {"type": "string"},
                "active": {"type": "boolean"},
            }
        ),
        "WorkspaceStatusResult": _object(
            {
                "active_workspace": {"$ref": "#/components/schemas/ActiveWorkspace"},
                "workspaces": {"type": "array", "items": {"$ref": "#/components/schemas/WorkspaceEntry"}},
                "access": {"$ref": "#/components/schemas/AccessStatus"},
            }
        ),
        "ActiveWorkspace": _object(
            {
                "name": {"type": "string"},
                "path": {"type": "string"},
            },
            ["name", "path"],
        ),
        "AccessStatus": _object(
            {
                "mode": {"type": "string"},
                "active": {"type": "boolean"},
                "expires_at": {"type": "string"},
                "seconds_remaining": {"type": ["integer", "null"]},
            }
        ),
        "SwitchWorkspaceRequest": _object({"name": {"type": "string"}}, ["name"]),
        "ListFilesRequest": _object(
            {
                "path": {"type": "string", "default": "."},
                "recursive": {"type": "boolean", "default": False},
                "max_depth": {"type": "integer", "minimum": 0},
                "include": {"type": "array", "items": {"type": "string"}},
                "exclude": {"type": "array", "items": {"type": "string"}},
                "pattern": {"type": "string", "default": "*"},
                "max_results": {"type": "integer", "minimum": 1, "default": 200},
            }
        ),
        "FileEntry": _object(
            {
                "path": {"type": "string"},
                "type": {"type": "string", "enum": ["file", "directory"]},
                "size_bytes": {"type": "integer"},
                "modified": {"type": "integer"},
                "depth": {"type": "integer"},
            }
        ),
        "FileListingResult": _object(
            {
                "path": {"type": "string"},
                "entries": {"type": "array", "items": {"$ref": "#/components/schemas/FileEntry"}},
                "total_entries": {"type": "integer"},
                "returned_entries": {"type": "integer"},
                "truncated": {"type": "boolean"},
                "truncation_reason": {"type": "string"},
            }
        ),
        "ReadFileRequest": _object(
            {
                "path": {"type": "string"},
                "start_line": {"type": "integer", "minimum": 1},
                "end_line": {"type": "integer", "minimum": 1},
                "max_bytes": {"type": "integer", "minimum": 1, "default": 200000},
                "line_numbers": {"type": "boolean", "default": False},
            },
            ["path"],
        ),
        "ReadFileResult": _object(
            {
                "path": {"type": "string"},
                "content": {"type": "string"},
                "size_bytes": {"type": "integer"},
                "returned_bytes": {"type": "integer"},
                "start_line": {"type": "integer", "minimum": 1},
                "end_line": {"type": "integer", "minimum": 1},
                "truncated": {"type": "boolean"},
                "truncation_reason": {"type": "string"},
            }
        ),
        "ReadFileSpec": _object(
            {
                "path": {"type": "string"},
                "start_line": {"type": "integer", "minimum": 1},
                "end_line": {"type": "integer", "minimum": 1},
            },
            ["path"],
        ),
        "ReadFilesRequest": _object(
            {
                "files": {"type": "array", "items": {"$ref": "#/components/schemas/ReadFileSpec"}},
                "max_bytes_per_file": {"type": "integer", "minimum": 1, "default": 30000},
                "max_total_bytes": {"type": "integer", "minimum": 1, "default": 100000},
                "line_numbers": {"type": "boolean", "default": False},
            },
            ["files"],
        ),
        "ReadFileBatchResult": _object(
            {
                "path": {"type": "string"},
                "exists": {"type": "boolean"},
                "size_bytes": {"type": "integer"},
                "returned_bytes": {"type": "integer"},
                "start_line": {"type": "integer", "minimum": 1},
                "end_line": {"type": "integer", "minimum": 1},
                "content": {"type": "string"},
                "truncated": {"type": "boolean"},
                "truncation_reason": {"type": "string"},
                "error": {"$ref": "#/components/schemas/ErrorInfo"},
            }
        ),
        "ReadFilesResult": _object(
            {
                "files": {"type": "array", "items": {"$ref": "#/components/schemas/ReadFileBatchResult"}},
                "total_returned_bytes": {"type": "integer"},
                "truncated": {"type": "boolean"},
                "truncation_reason": {"type": "string"},
            }
        ),
        "SearchTextRequest": _object(
            {
                "query": {"type": "string"},
                "path": {"type": "string", "default": "."},
                "regex": {"type": "boolean", "default": False},
                "case_sensitive": {"type": "boolean", "default": True},
                "include": {"type": "array", "items": {"type": "string"}},
                "exclude": {"type": "array", "items": {"type": "string"}},
                "context_before": {"type": "integer", "minimum": 0, "default": 0},
                "context_after": {"type": "integer", "minimum": 0, "default": 0},
                "max_results": {"type": "integer", "minimum": 1, "default": 100},
                "max_output_bytes": {"type": "integer", "minimum": 1, "default": 200000},
            },
            ["query"],
        ),
        "SearchContextLine": _object(
            {
                "line": {"type": "integer"},
                "text": {"type": "string"},
                "is_match": {"type": "boolean"},
            }
        ),
        "SearchMatch": _object(
            {
                "path": {"type": "string"},
                "line": {"type": "integer"},
                "column": {"type": "integer"},
                "matched_text": {"type": "string"},
                "line_text": {"type": "string"},
                "context": {"type": "array", "items": {"$ref": "#/components/schemas/SearchContextLine"}},
            }
        ),
        "SearchResult": _object(
            {
                "query": {"type": "string"},
                "matches": {"type": "array", "items": {"$ref": "#/components/schemas/SearchMatch"}},
                "total_matches": {"type": "integer"},
                "returned_matches": {"type": "integer"},
                "truncated": {"type": "boolean"},
                "truncation_reason": {"type": "string"},
            }
        ),
        "WriteFileRequest": _object({"path": {"type": "string"}, "content": {"type": "string"}}, ["path", "content"]),
        "WriteFileResult": _object({"path": {"type": "string"}, "bytes_written": {"type": "integer"}}),
        "PatchRequest": _object({"patch": {"type": "string"}}, ["patch"]),
        "PatchResult": _object({"changed_files": {"type": "array", "items": {"type": "string"}}}),
        "CommandRequest": _object(
            {
                "command": {"type": "string"},
                "cwd": {"type": "string", "default": "."},
                "timeout_seconds": {"type": "integer", "default": 60},
                "max_stdout_bytes": {"type": "integer", "minimum": 1, "default": 20000},
                "max_stderr_bytes": {"type": "integer", "minimum": 1, "default": 20000},
            },
            ["command"],
        ),
        "CommandResult": _object(
            {
                "command": {"type": "string"},
                "cwd": {"type": "string"},
                "exit_code": {"type": ["integer", "null"]},
                "duration_ms": {"type": "integer"},
                "stdout": {"type": "string"},
                "stderr": {"type": "string"},
                "stdout_bytes": {"type": "integer"},
                "stderr_bytes": {"type": "integer"},
                "stdout_truncated": {"type": "boolean"},
                "stderr_truncated": {"type": "boolean"},
                "timed_out": {"type": "boolean"},
            }
        ),
        "ErrorInfo": _object(
            {
                "code": {"type": "string"},
                "message": {"type": "string"},
            },
            ["code", "message"],
        ),
        "ErrorResult": _object(
            {
                "error": {"$ref": "#/components/schemas/ErrorInfo"},
                "access": {"$ref": "#/components/schemas/AccessStatus"},
            },
            ["error"],
        ),
    }


def _object(properties, required=None):
    schema = {"type": "object", "properties": properties, "additionalProperties": False}
    if required:
        schema["required"] = required
    return schema
