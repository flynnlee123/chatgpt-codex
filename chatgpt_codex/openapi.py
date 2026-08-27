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
            "version": "0.1.0",
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
                    "summary": "Show the active local workspace and all authorized workspaces. / 显示当前本地工作区和所有已授权工作区。",
                    "x-openai-isConsequential": False,
                    "security": [{"bearerAuth": []}],
                    "requestBody": _optional_request_body("EmptyRequest"),
                    "responses": {"200": _json_response("Workspace status", "WorkspaceStatusResult")},
                }
            },
            "/list_workspaces": {
                "post": {
                    "operationId": "listWorkspaces",
                    "summary": "List authorized workspaces that can be selected in this GPT chat. / 列出此 GPT 对话中可切换的已授权工作区。",
                    "x-openai-isConsequential": False,
                    "security": [{"bearerAuth": []}],
                    "requestBody": _optional_request_body("EmptyRequest"),
                    "responses": {"200": _json_response("Workspace list", "WorkspaceListResult")},
                }
            },
            "/switch_workspace": {
                "post": {
                    "operationId": "switchWorkspace",
                    "summary": "Switch the active workspace by authorized workspace name. / 按已授权工作区名称切换当前工作区。",
                    "security": [{"bearerAuth": []}],
                    "requestBody": _request_body("SwitchWorkspaceRequest"),
                    "responses": {"200": _json_response("Workspace status", "WorkspaceStatusResult")},
                }
            },
            "/list_files": {
                "post": {
                    "operationId": "listFiles",
                    "summary": "List files and directories inside the configured workspace. / 列出配置工作区内的文件和目录。",
                    "x-openai-isConsequential": False,
                    "security": [{"bearerAuth": []}],
                    "requestBody": _request_body("ListFilesRequest"),
                    "responses": {"200": _json_response("File listing", "FileListingResult")},
                }
            },
            "/read_file": {
                "post": {
                    "operationId": "readFile",
                    "summary": "Read a UTF-8 file inside the configured workspace. / 读取配置工作区内的 UTF-8 文件。",
                    "x-openai-isConsequential": False,
                    "security": [{"bearerAuth": []}],
                    "requestBody": _request_body("ReadFileRequest"),
                    "responses": {"200": _json_response("File content", "ReadFileResult")},
                }
            },
            "/search_text": {
                "post": {
                    "operationId": "searchText",
                    "summary": "Search text inside workspace files. / 搜索工作区文件文本。",
                    "x-openai-isConsequential": False,
                    "security": [{"bearerAuth": []}],
                    "requestBody": _request_body("SearchTextRequest"),
                    "responses": {"200": _json_response("Search results", "SearchResult")},
                }
            },
            "/write_file": {
                "post": {
                    "operationId": "writeFile",
                    "summary": "Create or replace a UTF-8 file inside the workspace. / 在工作区内创建或替换 UTF-8 文件。",
                    "x-openai-isConsequential": False,
                    "security": [{"bearerAuth": []}],
                    "requestBody": _request_body("WriteFileRequest"),
                    "responses": {"200": _json_response("Write result", "WriteFileResult")},
                }
            },
            "/apply_patch": {
                "post": {
                    "operationId": "applyPatch",
                    "summary": "Apply a limited apply_patch-style patch inside the workspace. / 在工作区内应用受限的 apply_patch 风格补丁。",
                    "x-openai-isConsequential": False,
                    "security": [{"bearerAuth": []}],
                    "requestBody": _request_body("PatchRequest"),
                    "responses": {"200": _json_response("Patch result", "PatchResult")},
                }
            },
            "/exec_command": {
                "post": {
                    "operationId": "execCommand",
                    "summary": "Run a shell command inside the workspace after safety checks. / 通过安全检查后在工作区内运行 shell 命令。",
                    "x-openai-isConsequential": False,
                    "security": [{"bearerAuth": []}],
                    "requestBody": _request_body("CommandRequest"),
                    "responses": {"200": _json_response("Command result", "CommandResult")},
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


def _schemas() -> Dict[str, object]:
    return {
        "HealthResult": _object(
            {
                "ok": {"type": "boolean"},
                "active_workspace": {"type": "string"},
                "public_base_url": {"type": "string"},
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
                "active_workspace": {"type": "string"},
                "workspace": {"type": "string"},
                "workspaces": {"type": "array", "items": {"$ref": "#/components/schemas/WorkspaceEntry"}},
            }
        ),
        "WorkspaceListResult": _object(
            {
                "active_workspace": {"type": "string"},
                "workspaces": {"type": "array", "items": {"$ref": "#/components/schemas/WorkspaceEntry"}},
            }
        ),
        "SwitchWorkspaceRequest": _object({"name": {"type": "string"}}, ["name"]),
        "ListFilesRequest": _object(
            {
                "path": {"type": "string", "default": "."},
                "recursive": {"type": "boolean", "default": True},
                "pattern": {"type": "string", "default": "*"},
                "max_results": {"type": "integer", "default": 200},
            }
        ),
        "FileEntry": _object(
            {
                "path": {"type": "string"},
                "type": {"type": "string", "enum": ["file", "directory"]},
                "size": {"type": "integer"},
                "modified": {"type": "integer"},
            }
        ),
        "FileListingResult": _object(
            {
                "path": {"type": "string"},
                "entries": {"type": "array", "items": {"$ref": "#/components/schemas/FileEntry"}},
                "truncated": {"type": "boolean"},
            }
        ),
        "ReadFileRequest": _object({"path": {"type": "string"}, "max_bytes": {"type": "integer", "default": 200000}}, ["path"]),
        "ReadFileResult": _object(
            {
                "path": {"type": "string"},
                "content": {"type": "string"},
                "bytes": {"type": "integer"},
                "truncated": {"type": "boolean"},
            }
        ),
        "SearchTextRequest": _object(
            {
                "query": {"type": "string"},
                "path": {"type": "string", "default": "."},
                "max_results": {"type": "integer", "default": 100},
                "regex": {"type": "boolean", "default": False},
            },
            ["query"],
        ),
        "SearchMatch": _object(
            {
                "path": {"type": "string"},
                "line": {"type": "integer"},
                "column": {"type": "integer"},
                "text": {"type": "string"},
            }
        ),
        "SearchResult": _object(
            {
                "query": {"type": "string"},
                "matches": {"type": "array", "items": {"$ref": "#/components/schemas/SearchMatch"}},
                "truncated": {"type": "boolean"},
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
            },
            ["command"],
        ),
        "CommandResult": _object(
            {
                "command": {"type": "string"},
                "cwd": {"type": "string"},
                "exit_code": {"type": "integer"},
                "stdout": {"type": "string"},
                "stderr": {"type": "string"},
                "stdout_truncated": {"type": "boolean"},
                "stderr_truncated": {"type": "boolean"},
            }
        ),
        "ErrorResult": _object({"error": {"type": "string"}}),
    }


def _object(properties, required=None):
    schema = {"type": "object", "properties": properties, "additionalProperties": False}
    if required:
        schema["required"] = required
    return schema
