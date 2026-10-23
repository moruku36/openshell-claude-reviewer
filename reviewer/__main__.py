"""Windows-compatible offline entry point. Live AI execution fails closed."""
import argparse
import hashlib
import json
import sys
from pathlib import Path

from .adapters import build_invocation
from .config import ConfigError, load_config

FIXTURE = "def add(a, b):\n    return a - b\n"
SYNTHETIC_REPORT = """# Synthetic review

This is a fixed offline fixture, not an AI-generated review.

- Major: fixture.py:2 - add subtracts b. For add(2, 1), expected 3, actual 1.
- Suggested fix: return a + b.
- Not reviewed: real repositories, providers, authentication, isolation or networking.
"""


class ExecutionBlocked(ValueError):
    pass


def plan(config):
    invocation = build_invocation(config["provider"], config.get("model"), config.get("command"))
    synthetic = config["provider"] == "synthetic"
    return {
        "schema_version": 1,
        "provider": config["provider"],
        "runtime": config["runtime"],
        "host": sys.platform,
        "argv": list(invocation.argv),
        "stdin_contract": invocation.stdin,
        "execution_available": synthetic,
        "network_used": False,
        "credentials_read": False,
        "security_boundary": "offline-only; no provider process is started",
        "requirements": [] if synthetic else [
            "Live execution is unavailable in this implementation.",
            "An argv plan is not proof of filesystem or network isolation.",
            "Provider image, credentials, cost and data-transfer authorization need separate verification.",
            *( ["OpenShell requires a verified gateway/runtime; native Windows OpenShell is not claimed."]
               if config["runtime"] == "openshell" else []),
        ],
    }


def execute(config):
    # This check happens before any output file is opened. No flag enables a
    # host fallback or real CLI invocation, including for custom commands.
    if config["provider"] != "synthetic":
        raise ExecutionBlocked("live provider execution is unavailable; use --dry-run")
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
    actions.add_argument("--execute", action="store_true", help="run the built-in synthetic fixture only")
    parser.add_argument("--out", help="new synthetic report path; never overwritten")
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
        report = execute(config)
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
    except OSError:
        print("report error: cannot create new output file", file=sys.stderr)
        return 4
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    sys.exit(main())
