import unittest

from chatgpt_codex.openapi import make_openapi_document


class OpenApiTests(unittest.TestCase):
    def test_openapi_has_explicit_object_schemas_for_action_responses(self):
        document = make_openapi_document("https://actions.example.com")

        self.assertEqual(document["servers"][0]["url"], "https://actions.example.com")
        self.assertEqual(document["info"]["version"], "0.5.0")
        for path in ["/workspace_status", "/switch_workspace", "/list_files", "/read_file", "/read_files", "/search_text", "/write_file", "/apply_patch", "/exec_command"]:
            with self.subTest(path=path):
                response = document["paths"][path]["post"]["responses"]["200"]
                schema = response["content"]["application/json"]["schema"]
                self.assertIn("$ref", schema)

        components = document["components"]["schemas"]
        for schema_name in ["WorkspaceStatusResult", "FileListingResult", "ReadFileResult", "ReadFilesResult", "SearchResult", "WriteFileResult", "PatchResult", "CommandResult"]:
            with self.subTest(schema_name=schema_name):
                self.assertEqual(components[schema_name]["type"], "object")
                self.assertIn("properties", components[schema_name])
                self.assertTrue(components[schema_name]["properties"])

        self.assertIn("readFiles", document["paths"]["/read_files"]["post"]["operationId"])
        self.assertNotIn("/list_workspaces", document["paths"])
        self.assertIn("max_depth", components["ListFilesRequest"]["properties"])
        self.assertFalse(components["ListFilesRequest"]["properties"]["recursive"]["default"])
        self.assertIn("start_line", components["ReadFileRequest"]["properties"])
        self.assertIn("end_line", components["ReadFileRequest"]["properties"])
        self.assertNotIn("range", components["ReadFileRequest"]["properties"])
        self.assertNotIn("bytes", components["ReadFileResult"]["properties"])
        self.assertNotIn("size", components["FileEntry"]["properties"])
        self.assertNotIn("selected_range", components["ReadFileResult"]["properties"])
        self.assertIn("start_line", components["ReadFileResult"]["properties"])
        self.assertIn("end_line", components["ReadFileResult"]["properties"])
        self.assertNotIn("range", components["ReadFileResult"]["properties"])
        self.assertNotIn("workspace", components["WorkspaceStatusResult"]["properties"])
        self.assertIn("workspaces", components["WorkspaceStatusResult"]["properties"])
        self.assertNotIn("WorkspaceListResult", components)
        self.assertIn("size_bytes", components["ReadFileResult"]["properties"])
        self.assertIn("returned_bytes", components["ReadFileResult"]["properties"])
        self.assertIn("start_line", components["ReadFileBatchResult"]["properties"])
        self.assertIn("end_line", components["ReadFileBatchResult"]["properties"])
        self.assertNotIn("range", components["ReadFileBatchResult"]["properties"])
        self.assertIn("start_line", components["ReadFileSpec"]["properties"])
        self.assertIn("end_line", components["ReadFileSpec"]["properties"])
        self.assertNotIn("range", components["ReadFileSpec"]["properties"])
        self.assertIn("matched_text", components["SearchMatch"]["properties"])
        self.assertIn("line_text", components["SearchMatch"]["properties"])
        self.assertNotIn("match", components["SearchMatch"]["properties"])
        self.assertNotIn("text", components["SearchMatch"]["properties"])
        self.assertIn("context_before", components["SearchTextRequest"]["properties"])
        self.assertIn("timed_out", components["CommandResult"]["properties"])
        self.assertNotIn("status", components["CommandResult"]["properties"])
        self.assertNotIn("command_id", components["CommandResult"]["properties"])
        self.assertNotIn("next_stdout_cursor", components["CommandResult"]["properties"])
        self.assertNotIn("next_stderr_cursor", components["CommandResult"]["properties"])
        self.assertNotIn("yield_seconds", components["CommandRequest"]["properties"])
        self.assertNotIn("PollCommandRequest", components)
        self.assertEqual(components["ErrorInfo"]["required"], ["code", "message"])
        self.assertNotIn("/poll_command", document["paths"])

        for path in document["paths"]:
            if path in ["/health", "/openapi.json", "/privacy"]:
                continue
            self.assertEqual(
                document["paths"][path]["post"]["responses"]["default"]["content"]["application/json"]["schema"],
                {"$ref": "#/components/schemas/ErrorResult"},
            )

    def test_openapi_declares_bearer_auth_for_mutating_and_read_actions(self):
        document = make_openapi_document("https://actions.example.com")

        self.assertIn("bearerAuth", document["components"]["securitySchemes"])
        for path, methods in document["paths"].items():
            if path in ["/health", "/openapi.json", "/privacy"]:
                continue
            self.assertEqual(methods["post"]["security"], [{"bearerAuth": []}])


if __name__ == "__main__":
    unittest.main()
