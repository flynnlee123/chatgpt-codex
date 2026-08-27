import sys
import tempfile
import unittest
from pathlib import Path

from chatgpt_codex.executor import CommandExecutor


class CommandExecutorTests(unittest.TestCase):
    def test_returns_byte_counts_and_individual_output_truncation(self):
        with tempfile.TemporaryDirectory() as workspace:
            result = CommandExecutor(Path(workspace)).run(
                "printf 123456",
                max_stdout_bytes=3,
                max_stderr_bytes=4,
            )

            self.assertEqual(result["exit_code"], 0)
            self.assertEqual(result["stdout"], "123")
            self.assertEqual(result["stdout_bytes"], 6)
            self.assertTrue(result["stdout_truncated"])
            self.assertEqual(result["stderr_bytes"], 0)
            self.assertFalse(result["stderr_truncated"])
            self.assertFalse(result["timed_out"])
            self.assertGreaterEqual(result["duration_ms"], 0)
            self.assertEqual(result["cwd"], str(Path(workspace).resolve()))

    def test_non_zero_exit_is_returned_as_a_normal_result(self):
        with tempfile.TemporaryDirectory() as workspace:
            result = CommandExecutor(Path(workspace)).run("exit 7")

            self.assertEqual(result["exit_code"], 7)
            self.assertFalse(result["timed_out"])

    def test_timeout_is_returned_as_a_structured_result(self):
        with tempfile.TemporaryDirectory() as workspace:
            command = f'"{sys.executable}" -c "import time; time.sleep(2)"'
            result = CommandExecutor(Path(workspace)).run(command, timeout_seconds=1)

            self.assertIsNone(result["exit_code"])
            self.assertTrue(result["timed_out"])
            self.assertIn("timed_out", result)


if __name__ == "__main__":
    unittest.main()
