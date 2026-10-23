import contextlib
import io
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from reviewer.__main__ import ExecutionBlocked, execute, main, plan, publish_report
from reviewer.adapters import build_invocation
from reviewer.config import ConfigError, load_config, validate


class ConfigTests(unittest.TestCase):
    def test_examples(self):
        for path in Path("configs").glob("*.json"):
            with self.subTest(path=path):
                load_config(path)

    def test_invalid_shapes(self):
        for bad in [None, [], {}, {"version": True, "provider": "codex"},
                    {"version": 1, "provider": []}, {"version": 1, "provider": "typo"},
                    {"version": 1, "provider": "codex", "api_key": "hidden"},
                    {"version": 1, "provider": "codex", "runtime": []},
                    {"version": 1, "provider": "codex", "runtime": "wsl-auto"},
                    {"version": 1, "provider": "synthetic", "runtime": "openshell"}]:
            with self.subTest(bad=bad), self.assertRaises(ConfigError):
                validate(bad)

    def test_model_validation(self):
        for model in ["", None, 1, "--danger", "model\n--yolo", "model name"]:
            with self.subTest(model=model), self.assertRaises(ConfigError):
                validate({"version": 1, "provider": "codex", "model": model})

    def test_custom_validation(self):
        for command in ["echo test", [], [1], [""], ["-cmd"], ["tool", "a\nb"], ["x"] * 65]:
            with self.subTest(command=command), self.assertRaises(ConfigError):
                validate({"version": 1, "provider": "custom", "command": command})

    def test_no_ignored_provider_fields(self):
        for provider, field, value in [("codex", "command", ["x"]),
                                        ("custom", "model", "x"),
                                        ("synthetic", "model", "x")]:
            with self.assertRaises(ConfigError):
                validate({"version": 1, "provider": provider, field: value})

    def test_bom_and_space_unicode_path(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "設定 space.json"
            path.write_text('{"version":1,"provider":"codex"}', encoding="utf-8-sig")
            self.assertEqual(load_config(path)["provider"], "codex")

    def test_bad_files_do_not_echo_contents(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "config.json"
            for contents in [b"sensitive invalid data", b"\xff", b"[" * 2000,
                             b"x" * 32769, b'{"version":1,"version":2}',
                             b'{"version":' + b'1' * 5000 + b'}']:
                path.write_bytes(contents)
                with self.assertRaises(ConfigError) as caught:
                    load_config(path)
                self.assertNotIn("sensitive", str(caught.exception))


class AdapterTests(unittest.TestCase):
    def test_codex_argv_and_stdin(self):
        cmd = build_invocation("codex", "explicit-model")
        self.assertEqual(cmd.argv, ("codex", "exec", "--sandbox", "read-only", "--ephemeral",
                                   "--skip-git-repo-check", "--model", "explicit-model", "-"))

    def test_no_invented_model_default(self):
        self.assertNotIn("--model", build_invocation("codex").argv)
        self.assertNotIn("--model", build_invocation("claude").argv)

    def test_claude_tools_are_disabled(self):
        cmd = build_invocation("claude").argv
        self.assertEqual(cmd[cmd.index("--tools") + 1], "")
        self.assertIn("--strict-mcp-config", cmd)
        self.assertEqual(cmd[cmd.index("--disallowedTools") + 1], "mcp__*")

    def test_custom_is_literal_argv(self):
        argv = ["C:/Program Files/Local Model/cli.exe", "$(do-not-run)", "a;b", "{prompt}"]
        config = validate({"version": 1, "provider": "custom", "command": argv})
        self.assertEqual(build_invocation("custom", command=config["command"]).argv, tuple(argv))

    def test_unknown_adapter_rejected(self):
        with self.assertRaises(ValueError):
            build_invocation("typo")

    def test_planning_never_starts_process(self):
        with patch("subprocess.Popen", side_effect=AssertionError("process started")):
            for provider in ["codex", "claude", "synthetic"]:
                result = plan(validate({"version": 1, "provider": provider}))
                self.assertFalse(result["network_used"])
                self.assertFalse(result["credentials_read"])

    def test_live_execution_blocked_all_runtimes(self):
        for provider in ["codex", "claude", "custom"]:
            for runtime in ["native", "openshell"]:
                config = {"version": 1, "provider": provider, "runtime": runtime}
                if provider == "custom":
                    config["command"] = ["never-launch"]
                with self.subTest(config=config), self.assertRaises(ExecutionBlocked):
                    execute(validate(config))


class CLITests(unittest.TestCase):
    def invoke(self, *args):
        stdout, stderr = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            code = main(list(args))
        return code, stdout.getvalue(), stderr.getvalue()

    def test_default_is_dry_run_no_files(self):
        code, out, err = self.invoke("--config", "configs/codex.json")
        self.assertEqual(code, 0, err)
        self.assertFalse(json.loads(out)["execution_available"])

    def test_error_codes(self):
        self.assertEqual(self.invoke("--config", "not-found.json")[0], 2)
        self.assertEqual(self.invoke("--config", "configs/codex.json", "--execute")[0], 3)
        self.assertEqual(self.invoke("--config", "configs/codex.json", "--out", "unused")[0], 2)

    def test_custom_command_not_echoed(self):
        with tempfile.TemporaryDirectory() as temp:
            config = Path(temp) / "config.json"
            config.write_text(json.dumps({"version": 1, "provider": "custom",
                                         "command": ["tool", "sensitive-value"]}))
            code, out, err = self.invoke("--config", str(config))
            self.assertEqual(code, 0, err)
            self.assertNotIn("sensitive-value", out + err)

    def test_synthetic_report_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "合成 review.md"
            args = ["--config", "configs/synthetic.json", "--execute", "--out", str(output)]
            self.assertEqual(self.invoke(*args)[0], 0)
            report = output.read_bytes()
            self.assertIn(b"fixed offline fixture", report)
            self.assertEqual(self.invoke(*args)[0], 4)
            self.assertEqual(output.read_bytes(), report)

    def test_blocked_does_not_touch_report(self):
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "report.md"
            output.write_text("keep")
            self.assertEqual(self.invoke("--config", "configs/claude.json", "--execute",
                                         "--out", str(output))[0], 3)
            self.assertEqual(output.read_text(), "keep")

    def test_missing_parent_is_safe_error(self):
        with tempfile.TemporaryDirectory() as temp:
            code, _, _ = self.invoke("--config", "configs/synthetic.json", "--execute", "--out",
                                     str(Path(temp) / "absent" / "out.md"))
            self.assertEqual(code, 4)

    def test_module_subprocess_synthetic_only(self):
        # The sole real child process is this repository's Python module.
        result = subprocess.run([sys.executable, "-m", "reviewer", "--config",
                                 "configs/synthetic.json", "--execute"],
                                capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("not an AI-generated review", result.stdout)


if __name__ == "__main__":
    unittest.main()
