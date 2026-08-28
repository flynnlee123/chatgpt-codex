import contextlib
import io
import json
import os
import tempfile
import threading
import unittest
from pathlib import Path

from chatgpt_codex.cli import main
from chatgpt_codex.config import AppConfig, load_config, load_permissions
from chatgpt_codex.server import create_server


def run_quietly(args):
    with contextlib.redirect_stdout(io.StringIO()):
        return main(args)


class CliTests(unittest.TestCase):
    def test_init_writes_private_config(self):
        with tempfile.TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "config.json"
            workspace = Path(tmp) / "workspace"
            workspace.mkdir()
            stdout = io.StringIO()

            with contextlib.redirect_stdout(stdout):
                exit_code = main(
                    [
                        "--config",
                        str(config_path),
                        "init",
                        "--workspace",
                        str(workspace),
                        "--public-base-url",
                        "https://actions.example.com",
                    ]
                )

            config = load_config(config_path)
            raw_config = json.loads(config_path.read_text(encoding="utf-8"))
            self.assertEqual(exit_code, 0)
            self.assertEqual(config.workspace, workspace.resolve())
            self.assertEqual(config.active_workspace, "workspace")
            self.assertEqual(config.public_base_url, "https://actions.example.com")
            self.assertGreaterEqual(len(config.token), 32)
            self.assertNotIn("workspace", raw_config)
            self.assertIn("workspaces", raw_config)
            self.assertEqual(raw_config["active_workspace"], "workspace")
            self.assertEqual(raw_config["workspaces"]["workspace"], str(workspace.resolve()))

    def test_openapi_command_prints_importable_schema(self):
        with tempfile.TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "config.json"
            workspace = Path(tmp) / "workspace"
            workspace.mkdir()
            run_quietly(["--config", str(config_path), "init", "--workspace", str(workspace)])
            stdout = io.StringIO()

            with contextlib.redirect_stdout(stdout):
                exit_code = main(["--config", str(config_path), "openapi"])

            document = json.loads(stdout.getvalue())
            self.assertEqual(exit_code, 0)
            self.assertIn("/exec_command", document["paths"])

    def test_gpt_instructions_include_action_setup_fields(self):
        with tempfile.TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "config.json"
            workspace = Path(tmp) / "workspace"
            workspace.mkdir()
            run_quietly(
                [
                    "--config",
                    str(config_path),
                    "init",
                    "--workspace",
                    str(workspace),
                    "--public-base-url",
                    "https://actions.example.com",
                ]
            )
            stdout = io.StringIO()

            with contextlib.redirect_stdout(stdout):
                exit_code = main(["--config", str(config_path), "gpt-instructions"])

            self.assertEqual(exit_code, 0)
            output = stdout.getvalue()
            self.assertIn("https://actions.example.com/openapi.json", output)
            self.assertIn("Bearer", output)
            self.assertIn("Only me", output)
            self.assertIn("getWorkspaceStatus", output)
            self.assertIn("switchWorkspace", output)
            self.assertIn("AGENTS.md", output)
            self.assertIn("Do not treat it as a mandatory preflight", output)
            self.assertIn("readFiles", output)
            self.assertIn("at least every 10 seconds", output)
            self.assertNotIn("listWorkspaces", output)
            self.assertNotIn("workspace_status", output)
            self.assertNotIn("switch_workspace", output)

    def test_workspace_cli_adds_lists_and_switches_authorized_workspaces(self):
        with tempfile.TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "config.json"
            first = Path(tmp) / "first"
            second = Path(tmp) / "second"
            first.mkdir()
            second.mkdir()
            run_quietly(
                [
                    "--config",
                    str(config_path),
                    "init",
                    "--workspace",
                    str(first),
                    "--workspace-name",
                    "first",
                ]
            )

            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                exit_code = main(
                    [
                        "--config",
                        str(config_path),
                        "workspace",
                        "add",
                        "--name",
                        "second",
                        "--path",
                        str(second),
                        "--activate",
                    ]
                )

            config = load_config(config_path)
            self.assertEqual(exit_code, 0)
            self.assertEqual(config.active_workspace, "second")
            self.assertEqual(config.workspace, second.resolve())
            self.assertIn("first", config.workspaces)

            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                exit_code = main(["--config", str(config_path), "workspace", "list"])

            listing = json.loads(stdout.getvalue())
            self.assertEqual(exit_code, 0)
            self.assertEqual(listing["active_workspace"], "second")
            self.assertEqual(len(listing["workspaces"]), 2)

    def test_app_config_requires_latest_workspace_registry_schema(self):
        with self.assertRaises(KeyError):
            AppConfig.from_dict({"workspace": "/tmp/legacy", "token": "secret-token"})

    def test_invalid_access_expiry_is_inactive_instead_of_crashing(self):
        config = AppConfig(
            token="secret-token",
            workspaces={"demo": Path.cwd()},
            active_workspace="demo",
            access_expires_at="not-a-date",
        )

        status = config.access_status()

        self.assertEqual(status["mode"], "invalid")
        self.assertFalse(status["active"])

    def test_status_prints_machine_readable_state_without_token(self):
        with tempfile.TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "config.json"
            workspace = Path(tmp) / "workspace"
            workspace.mkdir()
            run_quietly(
                [
                    "--config",
                    str(config_path),
                    "init",
                    "--workspace",
                    str(workspace),
                    "--workspace-name",
                    "demo",
                    "--public-base-url",
                    "https://actions.example.com",
                ]
            )
            token = load_config(config_path).token
            stdout = io.StringIO()

            with contextlib.redirect_stdout(stdout):
                exit_code = main(["--config", str(config_path), "status"])

            status = json.loads(stdout.getvalue())
            self.assertEqual(exit_code, 0)
            self.assertTrue(status["configured"])
            self.assertTrue(status["token_configured"])
            self.assertTrue(status["access"]["active"])
            self.assertEqual(status["active_workspace"], "demo")
            self.assertEqual(status["openapi_url"], "https://actions.example.com/openapi.json")
            self.assertIn("builder_profile_path", status)
            self.assertIn("node_found", status)
            self.assertIn("npx_found", status)
            self.assertNotIn(token, stdout.getvalue())

    def test_cli_language_can_be_selected_for_machine_readable_status(self):
        stdout = io.StringIO()

        with contextlib.redirect_stdout(stdout):
            exit_code = main(["--lang", "zh", "status"])

        status = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertEqual(status["language"], "zh")
        self.assertIn("chatgpt-codex --lang en status", status["language_examples"])
        self.assertIn("chatgpt-codex --lang zh status", status["language_examples"])

    def test_ai_commands_prints_machine_readable_command_catalog(self):
        stdout = io.StringIO()

        with contextlib.redirect_stdout(stdout):
            exit_code = main(["ai-commands"])

        catalog = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertIn("setup", catalog)
        self.assertIn("workspace", catalog)
        self.assertIn("language", catalog)
        self.assertIn("chatgpt-codex --lang zh <command>", catalog["language"])
        self.assertIn("chatgpt-codex status", catalog["inspect"])
        self.assertIn("chatgpt-codex access status", catalog["inspect"])
        self.assertIn("chatgpt-codex set-public-url <url>", catalog["routing"])
        self.assertIn("chatgpt-codex channel register --workspace <path> --public-base-url <url>", catalog["setup"])
        self.assertIn("chatgpt-codex channel status", catalog["inspect"])
        self.assertIn("chatgpt-codex channel renew", catalog["access"])
        self.assertIn("chatgpt-codex channel revoke", catalog["access"])
        self.assertIn("chatgpt-codex verify", catalog["inspect"])
        self.assertIn("chatgpt-codex api-smoke", catalog["inspect"])
        self.assertIn("chatgpt-codex access revoke", catalog["access"])
        self.assertIn("chatgpt-codex token", catalog["chatgpt_builder"])
        self.assertIn("chatgpt-codex chatgpt-preflight", catalog["chatgpt_builder"])
        self.assertIn("chatgpt-codex open-chatgpt-login", catalog["chatgpt_builder"])

    def test_chatgpt_preflight_reports_plan_and_builder_boundaries_without_token(self):
        with tempfile.TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "config.json"
            workspace = Path(tmp) / "workspace"
            workspace.mkdir()
            run_quietly(
                [
                    "--config",
                    str(config_path),
                    "init",
                    "--workspace",
                    str(workspace),
                    "--workspace-name",
                    "demo",
                    "--public-base-url",
                    "https://actions.example.com",
                ]
            )
            token = load_config(config_path).token
            stdout = io.StringIO()

            with contextlib.redirect_stdout(stdout):
                exit_code = main(["--config", str(config_path), "chatgpt-preflight"])

            preflight = json.loads(stdout.getvalue())
            self.assertEqual(exit_code, 0)
            self.assertTrue(preflight["chatgpt_login"]["required"])
            self.assertIn("ChatGPT Plus", preflight["account_requirements"]["can_create_and_edit_gpts"])
            self.assertFalse(preflight["builder_automation"]["fully_configurable_by_local_api"])
            self.assertEqual(preflight["builder_fields"]["authentication"], "API key / Bearer")
            self.assertEqual(preflight["builder_fields"]["schema_import_url"], "https://actions.example.com/openapi.json")
            self.assertNotIn(token, stdout.getvalue())

    def test_doctor_without_config_prints_next_step_instead_of_traceback(self):
        with tempfile.TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "missing.json"
            stdout = io.StringIO()

            with contextlib.redirect_stdout(stdout):
                exit_code = main(["--config", str(config_path), "doctor"])

            output = stdout.getvalue()
            self.assertEqual(exit_code, 1)
            self.assertIn("config is missing", output)
            self.assertIn("chatgpt-codex channel register", output)

    def test_channel_register_status_revoke_and_renew(self):
        with tempfile.TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "config.json"
            workspace = Path(tmp) / "workspace"
            workspace.mkdir()

            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                exit_code = main(
                    [
                        "--config",
                        str(config_path),
                        "channel",
                        "register",
                        "--workspace",
                        str(workspace),
                        "--workspace-name",
                        "demo",
                        "--public-base-url",
                        "https://actions.example.com/",
                    ]
                )
            registered = json.loads(stdout.getvalue())
            config = load_config(config_path)
            first_token = config.token
            self.assertEqual(exit_code, 0)
            self.assertTrue(registered["registered"])
            self.assertTrue(registered["active"])
            self.assertEqual(registered["token"], first_token)
            self.assertEqual(registered["public_base_url"], "https://actions.example.com")
            self.assertEqual(config.workspace, workspace.resolve())
            self.assertEqual(config.active_workspace, "demo")
            self.assertEqual(config.access_status()["mode"], "no_expiry")

            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                exit_code = main(["--config", str(config_path), "channel", "status"])
            status = json.loads(stdout.getvalue())
            self.assertEqual(exit_code, 0)
            self.assertTrue(status["registered"])
            self.assertTrue(status["token_configured"])
            self.assertNotIn(first_token, stdout.getvalue())

            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                exit_code = main(["--config", str(config_path), "channel", "revoke"])
            revoked = json.loads(stdout.getvalue())
            revoked_config = load_config(config_path)
            self.assertEqual(exit_code, 0)
            self.assertFalse(revoked["active"])
            self.assertTrue(revoked["token_rotated"])
            self.assertNotEqual(revoked_config.token, first_token)
            self.assertNotIn(revoked_config.token, stdout.getvalue())

            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                exit_code = main(["--config", str(config_path), "channel", "renew", "--public-base-url", "https://fresh.example.com"])
            renewed = json.loads(stdout.getvalue())
            renewed_config = load_config(config_path)
            self.assertEqual(exit_code, 0)
            self.assertTrue(renewed["active"])
            self.assertEqual(renewed["token"], renewed_config.token)
            self.assertEqual(renewed["public_base_url"], "https://fresh.example.com")
            self.assertEqual(renewed_config.access_status()["mode"], "no_expiry")

    def test_api_smoke_exercises_action_interfaces_without_existing_config(self):
        stdout = io.StringIO()

        with contextlib.redirect_stdout(stdout):
            exit_code = main(["api-smoke"])

        result = json.loads(stdout.getvalue())
        check_names = [check["name"] for check in result["checks"]]
        self.assertEqual(exit_code, 0)
        self.assertTrue(result["ok"])
        self.assertIn("workspace_status", check_names)
        self.assertIn("read_files", check_names)
        self.assertIn("write_file", check_names)
        self.assertIn("apply_patch", check_names)
        self.assertIn("exec_command", check_names)
        self.assertIn("switch_workspace", check_names)
        self.assertIn("path_escape_blocked", check_names)
        self.assertIn("dangerous_command_blocked", check_names)
        self.assertIn("expired_access_blocked", check_names)
        self.assertNotIn("api-smoke-token", stdout.getvalue())

    def test_access_commands_grant_revoke_and_rotate_without_leaking_status_token(self):
        with tempfile.TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "config.json"
            workspace = Path(tmp) / "workspace"
            workspace.mkdir()
            run_quietly(["--config", str(config_path), "init", "--workspace", str(workspace), "--workspace-name", "demo"])
            original = load_config(config_path).token

            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                exit_code = main(["--config", str(config_path), "access", "grant", "--ttl-minutes", "30"])
            granted = json.loads(stdout.getvalue())
            self.assertEqual(exit_code, 0)
            self.assertTrue(granted["access"]["active"])
            self.assertFalse(granted["token_rotated"])
            self.assertEqual(load_config(config_path).token, original)

            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                exit_code = main(["--config", str(config_path), "access", "status"])
            self.assertEqual(exit_code, 0)
            self.assertNotIn(original, stdout.getvalue())

            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                exit_code = main(["--config", str(config_path), "access", "revoke"])
            revoked = json.loads(stdout.getvalue())
            after_revoke = load_config(config_path)
            self.assertEqual(exit_code, 0)
            self.assertFalse(revoked["access"]["active"])
            self.assertTrue(revoked["token_rotated"])
            self.assertNotEqual(after_revoke.token, original)
            self.assertNotIn(after_revoke.token, stdout.getvalue())

            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                exit_code = main(["--config", str(config_path), "rotate-token", "--ttl-minutes", "15"])
            rotated = json.loads(stdout.getvalue())
            after_rotate = load_config(config_path)
            self.assertEqual(exit_code, 0)
            self.assertEqual(rotated["token"], after_rotate.token)
            self.assertTrue(rotated["access"]["active"])

    def test_set_public_url_preserves_token_and_workspaces(self):
        with tempfile.TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "config.json"
            workspace = Path(tmp) / "workspace"
            workspace.mkdir()
            run_quietly(["--config", str(config_path), "init", "--workspace", str(workspace), "--workspace-name", "demo"])
            before = load_config(config_path)

            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                exit_code = main(["--config", str(config_path), "set-public-url", "https://new.example.com/"])

            after = load_config(config_path)
            payload = json.loads(stdout.getvalue())
            self.assertEqual(exit_code, 0)
            self.assertEqual(payload["public_base_url"], "https://new.example.com")
            self.assertEqual(after.token, before.token)
            self.assertEqual(after.workspaces, before.workspaces)

    def test_verify_checks_health_schema_and_read_only_action(self):
        with tempfile.TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "config.json"
            workspace = Path(tmp) / "workspace"
            workspace.mkdir()
            (workspace / "hello.txt").write_text("hello", encoding="utf-8")
            run_quietly(["--config", str(config_path), "init", "--workspace", str(workspace), "--workspace-name", "demo"])
            config = load_config(config_path)
            config.port = 0
            server = create_server(config, config_path)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                base_url = f"http://127.0.0.1:{server.server_port}"
                run_quietly(["--config", str(config_path), "set-public-url", base_url])
                stdout = io.StringIO()
                with contextlib.redirect_stdout(stdout):
                    exit_code = main(["--config", str(config_path), "verify", "--base-url", base_url])

                result = json.loads(stdout.getvalue())
                self.assertEqual(exit_code, 0)
                self.assertTrue(result["ok"])
                self.assertEqual(len(result["checks"]), 3)
                self.assertTrue(all(check["ok"] for check in result["checks"]))
                self.assertEqual(result["checks"][1]["server_url"], base_url)
                self.assertNotIn("_content", stdout.getvalue())
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=5)

    def test_ai_native_alias_prints_agent_handoff(self):
        for command in ["agent-brief", "ai-native", "skills", "skill"]:
            with self.subTest(command=command):
                stdout = io.StringIO()

                with contextlib.redirect_stdout(stdout):
                    exit_code = main([command])

                output = stdout.getvalue()
                self.assertEqual(exit_code, 0)
                self.assertIn("Codex or Claude", output)
                self.assertIn("skills/chatgpt-codex/SKILL.md", output)
                self.assertIn("workspace path", output)
                self.assertIn("Playwright-profile human login to ChatGPT", output)
                self.assertIn("chatgpt-codex.<domain>", output)
                self.assertIn("public HTTPS", output)
                self.assertIn("ChatGPT Builder", output)

    def test_route_options_explain_cloudflared_and_domain_requirements(self):
        stdout = io.StringIO()

        with contextlib.redirect_stdout(stdout):
            exit_code = main(["route-options"])

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("built-in-quick-tunnel", output)
        self.assertIn("cloudflared required: yes", output)
        self.assertIn("custom-domain", output)
        self.assertIn("domain required: yes", output)

    def test_authorize_writes_permissions_without_secrets(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "repo"
            workspace = Path(tmp) / "workspace"
            root.mkdir()
            workspace.mkdir()
            stdout = io.StringIO()
            previous_cwd = Path.cwd()
            try:
                os.chdir(root)
                with contextlib.redirect_stdout(stdout):
                    exit_code = main(
                        [
                            "authorize",
                            "--workspace",
                            str(workspace),
                            "--operating-system",
                            "macos",
                            "--access-plan",
                            "built-in-quick-tunnel",
                            "--public-base-url",
                            "https://actions.example.com",
                            "--allow-browser-automation",
                            "--allow-start-services",
                            "--allow-install-helpers",
                            "--allow-workspace-write",
                            "--allow-command-execution",
                        ]
                    )
                permissions_path = root / ".chatgpt-codex" / "permissions.json"
                permissions = load_permissions(permissions_path)
            finally:
                os.chdir(previous_cwd)

            self.assertEqual(exit_code, 0)
            self.assertEqual(permissions.workspace, workspace.resolve())
            self.assertEqual(permissions.access_plan, "built-in-quick-tunnel")
            self.assertTrue(permissions.allow_browser_automation)
            self.assertTrue(permissions.allow_install_helpers)
            self.assertNotIn("password", permissions_path.read_text(encoding="utf-8").lower())

    def test_permissions_template_prints_and_writes_valid_json(self):
        stdout = io.StringIO()

        with contextlib.redirect_stdout(stdout):
            exit_code = main(["permissions-template"])

        template = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertEqual(template["access_plan"], "built-in-quick-tunnel")
        self.assertIn("workspace", template)

        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "permissions.json"
            with contextlib.redirect_stdout(io.StringIO()):
                exit_code = main(["permissions-template", "--output", str(output)])

            written = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(exit_code, 0)
            self.assertEqual(written["public_base_url"], "https://actions.example.com")


if __name__ == "__main__":
    unittest.main()
