#!/usr/bin/env python3
"""Offline sanity check of the rendered sandbox policy against the documented schema
(top-level fields, endpoint fields, rule shape). It is NOT a substitute for OpenShell's
own validation, which happens when a sandbox is created."""
import re
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
TOP = {"version", "filesystem_policy", "landlock", "process", "network_policies", "network_middlewares"}
ENDPOINT = {"host", "port", "ports", "path", "allowed_ips", "protocol", "tls", "enforcement", "access",
            "rules", "deny_rules", "allow_encoded_slash", "credential_binding"}
METHODS = {"GET", "HEAD", "OPTIONS", "POST", "PUT", "PATCH", "DELETE", "*"}


def check(policy, label):
    errs = []
    if not isinstance(policy, dict) or policy.get("version") != 1:
        errs.append("version must be 1")
    errs += [f"unknown top-level field: {k}" for k in policy if k not in TOP]
    fs = policy.get("filesystem_policy", {})
    if "/" in fs.get("read_write", []):
        errs.append("read_write must not contain /")
    for p in fs.get("read_only", []) + fs.get("read_write", []):
        if not p.startswith("/") or ".." in p:
            errs.append(f"bad filesystem path: {p}")
    if policy.get("landlock", {}).get("compatibility") != "hard_requirement":
        errs.append("landlock.compatibility must be hard_requirement (fail closed)")
    if str(policy.get("process", {}).get("run_as_user", "0")) in ("0", "root"):
        errs.append("must not run as root")
    for name, rule in policy.get("network_policies", {}).items():
        if not rule.get("binaries"):
            errs.append(f"{name}: no binaries (rule would match nothing)")
        for ep in rule.get("endpoints", []):
            errs += [f"{name}: unknown endpoint field {k}" for k in ep if k not in ENDPOINT]
            host = ep.get("host", "")
            if "*" in host or not host:
                errs.append(f"{name}: wildcard/empty host not allowed: {host!r}")
            if ep.get("enforcement") != "enforce":
                errs.append(f"{name}: enforcement must be 'enforce'")
            if "access" in ep and "rules" in ep:
                errs.append(f"{name}: access and rules cannot be combined")
            for r in ep.get("rules", []):
                m = r["allow"]["method"]
                if m not in METHODS:
                    errs.append(f"{name}: bad method {m}")
                if m not in ("GET", "HEAD") and not r["allow"]["path"].endswith(("git-upload-pack",)):
                    errs.append(f"{name}: write-capable allow rule: {m} {r['allow']['path']}")
    text = str(policy)
    if "@OWNER@" in text or "@REPO@" in text or "@GH_BINDING@" in text:
        errs.append("unrendered placeholder left in policy")
    return [f"[{label}] {e}" for e in errs]


def main():
    errs = []
    for token in ("0", "1"):
        out = ROOT / ".rendered" / f"lint-{token}.yaml"
        subprocess.run(["bash", "-c",
                        f'source "{ROOT}/scripts/lib.sh"; render_policy octo demo-repo.x {token} "{out}"'], check=True)
        policy = yaml.safe_load(out.read_text())
        errs += check(policy, f"token={token}")
        has_binding = any("credential_binding" in ep for r in policy["network_policies"].values() for ep in r["endpoints"])
        if has_binding != (token == "1"):
            errs.append(f"[token={token}] credential_binding presence is wrong")
    # hostile owner/repo must be rejected
    for bad in ("a/b c", "a/b;rm", "../x", "a/b/c", "a/..", "https://evil.com/a/b"):
        r = subprocess.run(["bash", "-c", f'source "{ROOT}/scripts/lib.sh"; parse_repo "$1"', "_", bad],
                           capture_output=True)
        if r.returncode == 0:
            errs.append(f"parse_repo accepted hostile input: {bad}")
    for e in errs:
        print(e, file=sys.stderr)
    print("policy lint:", "FAIL" if errs else "OK")
    return 1 if errs else 0


if __name__ == "__main__":
    sys.exit(main())
