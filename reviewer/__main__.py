"""Windows review entry point; offline by default, real providers require explicit permissions."""
import argparse
import hashlib
import json
import sys
from pathlib import Path

from .adapters import build_invocation
from .config import ConfigError, load_config
from .execution import Authorization, ExecutionBlocked, ExecutionFailed, authorize, run_review

FIXTURE = "def add(a, b):\n    return a - b\n"
SYNTHETIC_REPORT = """# Synthetic review

This is a fixed offline fixture, not an AI-generated review.

- Major: fixture.py:2 - add subtracts b. For add(2, 1), expected 3, actual 1.
- Suggested fix: return a + b.
- Not reviewed: real repositories, providers, authentication, isolation or networking.
"""


def plan(config):
    invocation = build_invocation(config["provider"], config.get("model"), config.get("command"),
                                  config.get("executable"), config.get("budget_usd"))
    synthetic = config["provider"] == "synthetic"
    return {
        "schema_version": 1,
        "provider": config["provider"],
        "runtime": config["runtime"],
        "host": sys.platform,
        "argv": list(invocation.argv),
        "stdin_contract": invocation.stdin,
        "execution_available": synthetic,
        "execution_implemented": True,
        "network_used": False,
        "credentials_read": False,
        "security_boundary": "offline-only; no provider process is started",
        "requirements": [] if synthetic else [
            "Execution remains blocked without explicit data-transfer, runtime and budget acknowledgments.",
            "An argv plan is not proof of filesystem or network isolation.",
            "Provider image, credentials, cost and data-transfer authorization need separate verification.",
            *( ["OpenShell requires a verified gateway/runtime; native Windows OpenShell is not claimed."]
               if config["runtime"] == "openshell" else []),
        ],
    }


def execute(config, input_path=None, permission=None):
    if config["provider"] != "synthetic":
        if not input_path:
            raise ExecutionBlocked("an explicitly approved --input text file is required")
        return run_review(config, input_path, permission or Authorization())
    return SYNTHETIC_REPORT + "\nFixture SHA-256: " + hashlib.sha256(FIXTURE.encode()).hexdigest() + "\n"


def publish_report(path, report):
    """Create exclusively: failures must never overwrite an existing report."""
    # Exclusive open also rejects symlinks and preexisting files. No directories
    # are created implicitly and no reviewed input is written or read.
    target = Path(path)
    with target.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(report)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True, help="credential-free JSON configuration")
    actions = parser.add_mutually_exclusive_group()
    actions.add_argument("--dry-run", action="store_true", help="default: validate and show an offline plan")
    actions.add_argument("--execute", action="store_true", help="explicit execution; real providers need all permissions")
    parser.add_argument("--out", help="new report path; never overwritten")
    parser.add_argument("--input", help="approved UTF-8 text file; never read by dry-run")
    parser.add_argument("--allow-data-transfer", action="store_true")
    parser.add_argument("--allow-native-execution", action="store_true")
    parser.add_argument("--confirm-external-budget", action="store_true")
    parser.add_argument("--confirm-sandbox-verified", action="store_true")
    args = parser.parse_args(argv)
    try:
        config = load_config(args.config)
        if not args.execute:
            if args.out:
                raise ConfigError("--out is supported only with --execute")
            result = plan(config)
            # Custom arguments are untrusted, potentially sensitive data. Keep
            # them out of logs even when a config contains pasted credentials.
            if config["provider"] == "custom":
                result["argv"] = ["<custom argv omitted>"]
            print(json.dumps(result, indent=2, ensure_ascii=True))
            return 0
        if config["provider"] == "synthetic" and args.input:
            raise ConfigError("synthetic execution accepts no input file")
        if config["provider"] != "synthetic":
            if not args.input:
                raise ExecutionBlocked("an explicitly approved --input text file is required")
            authorize(config, Authorization(args.allow_data_transfer, args.allow_native_execution,
                      args.confirm_external_budget, args.confirm_sandbox_verified))
            if not args.out:
                raise ExecutionBlocked("real provider execution requires a new --out report path")
            if Path(args.out).exists() or Path(args.out).is_symlink():
                raise OSError("output exists")
            if not Path(args.out).parent.is_dir():
                raise OSError("output parent missing")
        report = execute(config, args.input, Authorization(args.allow_data_transfer,
                         args.allow_native_execution, args.confirm_external_budget,
                         args.confirm_sandbox_verified))
        if args.out:
            publish_report(args.out, report)
        else:
            print(report, end="")
        return 0
    except ConfigError as exc:
        print("configuration error: " + str(exc), file=sys.stderr)
        return 2
    except ExecutionBlocked as exc:
        print("execution blocked: " + str(exc), file=sys.stderr)
        return 3
    except ExecutionFailed as exc:
        print("execution failed: " + str(exc), file=sys.stderr)
        return 5
    except OSError:
        print("report error: cannot create new output file", file=sys.stderr)
        return 4
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    sys.exit(main())
