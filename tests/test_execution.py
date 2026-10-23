"""All provider behavior is simulated. No installed provider or AI account is used."""
import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from reviewer.__main__ import main
from reviewer.config import ConfigError, validate
from reviewer.execution import (Authorization, ExecutionBlocked, ExecutionFailed, authorize,
                                command_for, load_input, resolve_executable, run_process, run_review)


PERMISSION = Authorization(data_transfer=True, native_execution=True, external_budget=True)


class FakeWriter(io.BytesIO):
    def close(self):
        self.recorded = self.getvalue()
        super().close()


def fake_process(stdout=b"A simulated review\n", stderr=b"", returncode=0):
    process = Mock()
    process.stdin = FakeWriter()
    process.stdout = io.BytesIO(stdout)
    process.stderr = io.BytesIO(stderr)
    process.wait.return_value = returncode
    return process


class ExecutionTests(unittest.TestCase):
    def config(self, **extra):
        return validate({"version": 1, "provider": "codex", "budget_usd": 0.25, **extra})

    def test_all_opt_ins_required_before_read_or_spawn(self):
        for permission in [Authorization(), Authorization(data_transfer=True),
                           Authorization(data_transfer=True, external_budget=True)]:
            with (self.subTest(permission=permission), patch("reviewer.execution.load_input") as reader,
                  patch("subprocess.Popen") as spawn):
                with self.assertRaises(ExecutionBlocked):
                    run_review(self.config(), "never-read", permission)
                reader.assert_not_called()
                spawn.assert_not_called()

    def test_budget_required_even_with_permission(self):
        with self.assertRaises(ExecutionBlocked):
            authorize(validate({"version": 1, "provider": "codex"}), PERMISSION)

    def test_budget_validation(self):
        for value in [None, True, 0, -1, float("nan"), float("inf"), 101, "1", 10**1000]:
            with self.subTest(value=str(value)[:20]), self.assertRaises(ConfigError):
                self.config(budget_usd=value)

    def test_timeout_validation(self):
        for value in [0, True, 601, 1.2]:
            with self.assertRaises(ConfigError):
                self.config(timeout_seconds=value)

    def test_provider_executable_overrides(self):
        from reviewer.adapters import build_invocation
        config = self.config(executable="C:/Program Files/Codex/codex.exe")
        argv = build_invocation("codex", executable=config["executable"], budget_usd=0.25).argv
        self.assertEqual(argv[0], config["executable"])
        self.assertNotIn("--max-budget-usd", argv)
        argv = build_invocation("claude", budget_usd=0.25).argv
        self.assertIn("--max-budget-usd", argv)
        self.assertIn("--no-session-persistence", argv)

    def test_windows_batch_wrapper_refused(self):
        with (patch("reviewer.execution.sys.platform", "win32"),
              patch("shutil.which", return_value="C:/tool/cli.cmd"),
              patch("reviewer.execution.Path.is_absolute", return_value=True)):
            with self.assertRaises(ExecutionBlocked):
                resolve_executable("cli")

    def test_missing_executable(self):
        with patch("shutil.which", return_value=None), self.assertRaises(ExecutionFailed):
            resolve_executable("missing")

    def test_openshell_windows_refused(self):
        config = self.config(runtime="openshell", sandbox="existing-box")
        with patch("reviewer.execution.sys.platform", "win32"), self.assertRaises(ExecutionBlocked):
            authorize(config, Authorization(True, False, True, True))

    def test_openshell_requires_verified_existing_sandbox(self):
        with patch("reviewer.execution.sys.platform", "linux"):
            for config in [self.config(runtime="openshell"),
                           self.config(runtime="openshell", sandbox="existing-box")]:
                with self.assertRaises(ExecutionBlocked):
                    authorize(config, Authorization(True, False, True, False))

    def test_openshell_command_contract_no_provisioning(self):
        config = self.config(runtime="openshell", sandbox="existing-box", timeout_seconds=40)
        with patch("reviewer.execution.resolve_executable", return_value="/usr/bin/openshell"):
            argv = command_for(config)
        self.assertEqual(argv[:12], ["/usr/bin/openshell", "sandbox", "exec", "-n", "existing-box",
                                     "--no-tty", "--no-login-shell", "--timeout", "40", "--", "codex", "exec"])
        self.assertNotIn("create", argv)
        self.assertNotIn("--provider", argv)

    def test_input_limits_and_invalid_text(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "approved.txt"
            for raw in [b"", b" \n", b"\xff", b"x\0y", b"x" * (256 * 1024 + 1)]:
                path.write_bytes(raw)
                with self.assertRaises(ExecutionFailed):
                    load_input(path)
            path.write_text("provided text", encoding="utf-8-sig")
            self.assertIn(b"provided text", load_input(path))

    def test_success_stdin_no_shell_and_discard_stderr(self):
        process = fake_process(stderr=b"sensitive diagnostic")
        with patch("subprocess.Popen", return_value=process) as spawn:
            result = run_process(["fake"], b"approved text", 10, "empty-cwd")
        self.assertEqual(result, "A simulated review\n")
        self.assertEqual(process.stdin.recorded, b"approved text")
        self.assertFalse(spawn.call_args.kwargs["shell"])
        self.assertEqual(spawn.call_args.kwargs["cwd"], "empty-cwd")
        self.assertNotIn("sensitive", result)

    def test_provider_failure_does_not_echo_stderr(self):
        with patch("subprocess.Popen", return_value=fake_process(stderr=b"sensitive", returncode=1)) as spawn:
            with self.assertRaises(ExecutionFailed) as caught:
                run_process(["fake"], b"input", 10, ".")
            self.assertNotIn("sensitive", str(caught.exception))
            self.assertEqual(spawn.call_count, 1)

    def test_empty_invalid_or_oversize_output(self):
        for output in [b"", b" \n", b"\xff", b"x" * (1024 * 1024 + 1)]:
            with self.subTest(size=len(output)), patch("subprocess.Popen", return_value=fake_process(stdout=output)):
                with self.assertRaises(ExecutionFailed):
                    run_process(["fake"], b"input", 10, ".")

    def test_stderr_also_counts_toward_limit(self):
        with patch("subprocess.Popen", return_value=fake_process(stderr=b"x" * (1024 * 1024 + 1))):
            with self.assertRaises(ExecutionFailed):
                run_process(["fake"], b"input", 10, ".")

    def test_timeout_kills_direct_child_no_retry(self):
        process = fake_process()
        with (patch("subprocess.Popen", return_value=process) as spawn,
              patch("time.monotonic", side_effect=[0, 2])):
            with self.assertRaisesRegex(ExecutionFailed, "uncertain"):
                run_process(["fake"], b"input", 1, ".")
        process.kill.assert_called_once()
        self.assertEqual(spawn.call_count, 1)

    def test_launch_failure(self):
        with patch("subprocess.Popen", side_effect=FileNotFoundError("private path")):
            with self.assertRaises(ExecutionFailed) as caught:
                run_process(["fake"], b"input", 1, ".")
            self.assertNotIn("private path", str(caught.exception))

    def test_interruption_cleans_direct_child_and_does_not_retry(self):
        process = fake_process()
        process.wait.side_effect = [KeyboardInterrupt, 0]
        with patch("subprocess.Popen", return_value=process) as spawn:
            with self.assertRaises(KeyboardInterrupt):
                run_process(["fake"], b"input", 10, ".")
        process.kill.assert_called_once()
        self.assertEqual(spawn.call_count, 1)

    def test_dry_run_does_not_read_input_even_with_permissions(self):
        with (contextlib.redirect_stdout(io.StringIO()),
              patch("reviewer.execution.load_input") as reader,
              patch("subprocess.Popen") as spawn):
            self.assertEqual(main(["--config", "configs/live-codex.example.json", "--dry-run",
                                  "--input", "never-read", "--allow-data-transfer",
                                  "--allow-native-execution", "--confirm-external-budget"]), 0)
        reader.assert_not_called()
        spawn.assert_not_called()

    def test_run_review_has_empty_cwd_and_stdin_not_argv(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "approved.txt"
            path.write_text("provided text")
            def simulate(argv, payload, timeout, cwd):
                self.assertEqual(argv, ["fake"])
                self.assertIn(b"provided text", payload)
                self.assertEqual(list(Path(cwd).iterdir()), [])
                return "review"
            with (patch("reviewer.execution.command_for", return_value=["fake"]),
                  patch("reviewer.execution.run_process", side_effect=simulate) as runner):
                self.assertEqual(run_review(self.config(), path, PERMISSION), "review")
                cwd = runner.call_args.args[-1]
            self.assertFalse(Path(cwd).exists())

    def test_cli_mock_end_to_end_and_existing_output_preflight(self):
        with tempfile.TemporaryDirectory() as temp:
            config, input_file, output = [Path(temp) / name for name in ["config.json", "input.txt", "out.md"]]
            config.write_text(json.dumps(self.config()))
            input_file.write_text("provided text")
            args = ["--config", str(config), "--execute", "--input", str(input_file), "--out", str(output),
                    "--allow-data-transfer", "--allow-native-execution", "--confirm-external-budget"]
            with (contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()),
                  patch("reviewer.execution.command_for", return_value=["fake"]),
                  patch("reviewer.execution.run_process", return_value="mock report") as runner):
                self.assertEqual(main(args), 0)
                self.assertEqual(output.read_text(), "mock report")
                self.assertEqual(main(args), 4)
                self.assertEqual(runner.call_count, 1)

    def test_failed_execution_publishes_no_report(self):
        with tempfile.TemporaryDirectory() as temp:
            config, output = Path(temp) / "config.json", Path(temp) / "out.md"
            config.write_text(json.dumps(self.config()))
            with (contextlib.redirect_stderr(io.StringIO()),
                  patch("reviewer.__main__.execute", side_effect=ExecutionFailed("failed"))):
                code = main(["--config", str(config), "--execute", "--input", "not-read",
                             "--out", str(output), "--allow-data-transfer", "--allow-native-execution",
                             "--confirm-external-budget"])
            self.assertEqual(code, 5)
            self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
