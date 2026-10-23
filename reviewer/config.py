"""Strict, credential-free configuration for offline plans."""
import json
import re
from pathlib import Path

MAX_CONFIG_BYTES = 32 * 1024
FIELDS = {"version", "provider", "model", "command", "runtime"}
PROVIDERS = {"codex", "claude", "custom", "synthetic"}


class ConfigError(ValueError):
    pass


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ConfigError("duplicate configuration key")
        result[key] = value
    return result


def validate(data):
    if not isinstance(data, dict) or set(data) - FIELDS:
        raise ConfigError("configuration must be an object with documented keys only")
    if type(data.get("version")) is not int or data["version"] != 1:
        raise ConfigError("version must be integer 1")
    provider = data.get("provider")
    if not isinstance(provider, str) or provider not in PROVIDERS:
        raise ConfigError("provider must be codex, claude, custom, or synthetic")
    runtime = data.get("runtime", "native")
    if not isinstance(runtime, str) or runtime not in {"native", "openshell"}:
        raise ConfigError("runtime must be native or openshell")
    model = data.get("model")
    if "model" in data:
        if provider not in {"codex", "claude"}:
            raise ConfigError("model is supported only for codex and claude")
        if not isinstance(model, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}", model):
            raise ConfigError("model must be a nonempty model identifier, not options")
    command = data.get("command")
    if provider == "custom":
        if not isinstance(command, list) or not 1 <= len(command) <= 64:
            raise ConfigError("custom command must be an argv array of 1 to 64 strings")
        if any(not isinstance(arg, str) or not arg or len(arg) > 4096 or
               any(ord(c) < 32 or ord(c) == 127 for c in arg) for arg in command):
            raise ConfigError("custom command arguments must be nonempty printable strings")
        if command[0].startswith("-"):
            raise ConfigError("custom executable cannot start with a dash")
    elif "command" in data:
        raise ConfigError("command is supported only for custom")
    if provider == "synthetic" and runtime != "native":
        raise ConfigError("synthetic fixtures run natively without OpenShell")
    return {"version": 1, "provider": provider, "runtime": runtime,
            **({"model": model} if model is not None else {}),
            **({"command": command} if command is not None else {})}


def load_config(path):
    try:
        with Path(path).open("rb") as stream:
            raw = stream.read(MAX_CONFIG_BYTES + 1)
        if len(raw) > MAX_CONFIG_BYTES:
            raise ConfigError("configuration exceeds 32 KiB")
        data = json.loads(raw.decode("utf-8-sig"), object_pairs_hook=_pairs)
    except (OSError, UnicodeError, ValueError, RecursionError) as exc:
        # Never echo malformed input or paths: they may contain credentials.
        raise ConfigError("cannot read valid UTF-8 JSON configuration") from exc
    return validate(data)
