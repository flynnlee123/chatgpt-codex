import json
import tempfile
import threading
import unittest
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import ProxyHandler, Request, build_opener

from chatgpt_codex.config import AppConfig, save_config
from chatgpt_codex.server import create_server


def open_without_proxy(request):
    opener = build_opener(ProxyHandler({}))
    return opener.open(request, timeout=5)


def post_json(url, body):
    payload = json.dumps(body).encode("utf-8")
    request = Request(
        url,
        data=payload,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Authorization": "Bearer secret-token",
        },
    )
    response = open_without_proxy(request)
    return json.loads(response.read().decode("utf-8"))


class ServerTests(unittest.TestCase):
    def test_server_requires_bearer_token_for_actions(self):
        with tempfile.TemporaryDirectory() as workspace:
            server = create_server(
                AppConfig(
                    token="secret-token",
                    workspaces={"default": Path(workspace)},
                    active_workspace="default",
                    host="127.0.0.1",
                    port=0,
                    public_base_url="https://actions.example.com",
                )
            )
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                url = f"http://127.0.0.1:{server.server_port}/list_files"
                request = Request(url, data=b"{}", method="POST", headers={"Content-Type": "application/json"})

                with self.assertRaises(HTTPError) as raised:
                    open_without_proxy(request)

                self.assertEqual(raised.exception.code, 401)
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=5)

    def test_authorized_list_files_action_returns_workspace_entries(self):
        with tempfile.TemporaryDirectory() as workspace:
            root = Path(workspace)
            (root / "hello.txt").write_text("hello", encoding="utf-8")
            server = create_server(
                AppConfig(
                    token="secret-token",
                    workspaces={"default": root},
                    active_workspace="default",
                    host="127.0.0.1",
                    port=0,
                    public_base_url="https://actions.example.com",
                )
            )
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                url = f"http://127.0.0.1:{server.server_port}/list_files"
                (root / "nested").mkdir()
                (root / "nested" / "inside.txt").write_text("inside", encoding="utf-8")
                payload = json.dumps({"path": "."}).encode("utf-8")
                request = Request(
                    url,
                    data=payload,
                    method="POST",
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": "Bearer secret-token",
                    },
                )

                response = open_without_proxy(request)
                body = json.loads(response.read().decode("utf-8"))

                self.assertEqual(response.status, 200)
                paths = [entry["path"] for entry in body["entries"]]
                self.assertIn("hello.txt", paths)
                self.assertIn("nested", paths)
                self.assertNotIn("nested/inside.txt", paths)
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=5)

    def test_authorized_read_files_action_returns_batch_results(self):
        with tempfile.TemporaryDirectory() as workspace:
            root = Path(workspace)
            (root / "one.txt").write_text("one\ntwo\n", encoding="utf-8")
            server = create_server(
                AppConfig(
                    token="secret-token",
                    workspaces={"default": root},
                    active_workspace="default",
                    host="127.0.0.1",
                    port=0,
                    public_base_url="https://actions.example.com",
                )
            )
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                body = post_json(
                    f"http://127.0.0.1:{server.server_port}/read_files",
                    {"files": [{"path": "one.txt", "start_line": 2, "end_line": 2}, {"path": "missing.txt"}], "line_numbers": True},
                )

                self.assertEqual(body["files"][0]["content"], "2 | two\n")
                self.assertTrue(body["files"][0]["exists"])
                self.assertEqual(body["files"][0]["start_line"], 2)
                self.assertEqual(body["files"][0]["end_line"], 2)
                self.assertEqual(body["files"][1]["error"]["code"], "file_not_found")
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=5)

    def test_switch_workspace_changes_action_scope_and_persists_config(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            alpha = root / "alpha"
            beta = root / "beta"
            alpha.mkdir()
            beta.mkdir()
            (alpha / "alpha.txt").write_text("alpha", encoding="utf-8")
            (beta / "beta.txt").write_text("beta", encoding="utf-8")
            config_path = root / "config.json"
            config = AppConfig(
                token="secret-token",
                workspaces={"alpha": alpha, "beta": beta},
                active_workspace="alpha",
                host="127.0.0.1",
                port=0,
                public_base_url="https://actions.example.com",
            )
            server = create_server(config, config_path)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                base = f"http://127.0.0.1:{server.server_port}"
                status = post_json(base + "/workspace_status", {})
                self.assertEqual(status["active_workspace"]["name"], "alpha")
                self.assertEqual([item["name"] for item in status["workspaces"]], ["alpha", "beta"])
                switched = post_json(base + "/switch_workspace", {"name": "beta"})
                self.assertEqual(switched["active_workspace"]["name"], "beta")
                self.assertEqual([item["name"] for item in switched["workspaces"]], ["alpha", "beta"])
                listing = post_json(base + "/list_files", {"path": ".", "recursive": True})
                self.assertEqual(listing["entries"][0]["path"], "beta.txt")
                persisted = json.loads(config_path.read_text(encoding="utf-8"))
                self.assertEqual(persisted["active_workspace"], "beta")
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=5)

    def test_expired_access_session_blocks_actions(self):
        with tempfile.TemporaryDirectory() as workspace:
            config = AppConfig(
                token="secret-token",
                workspaces={"default": Path(workspace)},
                active_workspace="default",
                host="127.0.0.1",
                port=0,
                public_base_url="https://actions.example.com",
            )
            config.revoke_access()
            server = create_server(config)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                url = f"http://127.0.0.1:{server.server_port}/workspace_status"
                request = Request(
                    url,
                    data=b"{}",
                    method="POST",
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": "Bearer secret-token",
                    },
                )

                with self.assertRaises(HTTPError) as raised:
                    open_without_proxy(request)

                self.assertEqual(raised.exception.code, 403)
                body = json.loads(raised.exception.read().decode("utf-8"))
                self.assertEqual(body["error"]["code"], "access_expired")
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=5)

    def test_running_server_reloads_rotated_token_from_config_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            workspace = root / "workspace"
            workspace.mkdir()
            config_path = root / "config.json"
            config = AppConfig(
                token="old-token",
                workspaces={"default": workspace},
                active_workspace="default",
                host="127.0.0.1",
                port=0,
                public_base_url="https://actions.example.com",
            )
            save_config(config, config_path, overwrite=True)
            server = create_server(config, config_path)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                base = f"http://127.0.0.1:{server.server_port}"
                initial_request = Request(
                    base + "/workspace_status",
                    data=b"{}",
                    method="POST",
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": "Bearer old-token",
                    },
                )
                initial = json.loads(open_without_proxy(initial_request).read().decode("utf-8"))
                self.assertEqual(initial["active_workspace"]["name"], "default")

                config.token = "new-token"
                save_config(config, config_path, overwrite=True)

                old_request = Request(
                    base + "/workspace_status",
                    data=b"{}",
                    method="POST",
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": "Bearer old-token",
                    },
                )
                with self.assertRaises(HTTPError) as raised:
                    open_without_proxy(old_request)
                self.assertEqual(raised.exception.code, 401)

                new_request = Request(
                    base + "/workspace_status",
                    data=b"{}",
                    method="POST",
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": "Bearer new-token",
                    },
                )
                response = open_without_proxy(new_request)
                self.assertEqual(response.status, 200)
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=5)


if __name__ == "__main__":
    unittest.main()
