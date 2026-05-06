"""JARFIS Work Args — parse $ARGUMENTS for /jarfis:work overrides.

ADR-0003 §2.3 introduced two override flags so the user can bypass
``jarfis_cli.py domain detect`` when the autodetect picks the wrong
domain or when the project is greenfield:

    /jarfis:work --domain mobile
    /jarfis:work --scope-domain shell=desktop --scope-domain app=mobile

Both flags can coexist with each other and with free-text input
(work description). This module is the single source of truth for
parsing those flags. ``work.md`` Phase 0 step 7 reads the result and:

  * If ``args["domain"]`` is set → skip ``domain detect``, use the
    override across all scopes.
  * If ``args["scope_domains"]`` is non-empty → for each
    ``scope[i].name`` matching a key, force the listed domain;
    everything else falls through to detect.

The module intentionally has no I/O so it stays trivially testable from
``scripts/tests/test_dispatch.py``. CLI usage emits JSON via the standard
``json_output`` / ``json_error`` helpers and ``main()`` wires it into
``jarfis_cli.py`` if/when the orchestrator needs subprocess access.
"""

from __future__ import annotations

import shlex
import sys
from typing import Optional

from . import trace
from .utils import json_error, json_output


VALID_DOMAINS = ("web", "desktop", "mobile")


class WorkArgsError(ValueError):
    """Raised on malformed --domain / --scope-domain values."""


def _validate_domain(value: str) -> str:
    if value not in VALID_DOMAINS:
        raise WorkArgsError(
            f"Invalid domain {value!r}. Expected one of: "
            f"{', '.join(VALID_DOMAINS)}"
        )
    return value


def parse_work_args(arg_string: Optional[str]) -> dict:
    """Parse ``$ARGUMENTS`` for /jarfis:work override flags.

    Args:
        arg_string: Raw ``$ARGUMENTS`` value (may be empty / None).

    Returns:
        Dict with any of the following keys present:
          * ``domain``: str (one of ``web``/``desktop``/``mobile``) — only
            present when ``--domain`` is supplied.
          * ``scope_domains``: ``dict[str, str]`` — only present when at
            least one ``--scope-domain name=domain`` is supplied.
          * ``input``: str — leftover free-text after flag extraction
            (always present, possibly empty, only when arg_string had any
            non-flag content).

        An empty/whitespace-only / None input returns ``{}`` so callers
        can do ``if args:`` to detect "no overrides".

    Raises:
        WorkArgsError: invalid domain value or malformed scope-domain.
    """
    if not arg_string or not str(arg_string).strip():
        return {}

    try:
        tokens = shlex.split(str(arg_string))
    except ValueError as exc:
        raise WorkArgsError(f"Could not parse $ARGUMENTS: {exc}") from exc

    result: dict = {}
    leftover: list[str] = []
    scope_domains: dict[str, str] = {}

    i = 0
    while i < len(tokens):
        tok = tokens[i]
        if tok == "--domain":
            if i + 1 >= len(tokens):
                raise WorkArgsError("--domain requires a value")
            result["domain"] = _validate_domain(tokens[i + 1])
            i += 2
            continue
        if tok.startswith("--domain="):
            result["domain"] = _validate_domain(tok.split("=", 1)[1])
            i += 1
            continue
        if tok == "--scope-domain":
            if i + 1 >= len(tokens):
                raise WorkArgsError(
                    "--scope-domain requires a <name>=<domain> value"
                )
            value = tokens[i + 1]
            i += 2
            _absorb_scope_domain(scope_domains, value)
            continue
        if tok.startswith("--scope-domain="):
            _absorb_scope_domain(scope_domains, tok.split("=", 1)[1])
            i += 1
            continue
        leftover.append(tok)
        i += 1

    if scope_domains:
        result["scope_domains"] = scope_domains

    if leftover:
        result["input"] = " ".join(leftover)

    # M6.4 (T3): testbed dispatch breadcrumbs.
    # `--scope-domain` is a multi-domain monorepo signal (per ADR-0003
    # §2.2 case 5); `--domain` alone is a single-scope override.
    try:
        if trace.is_enabled():
            if scope_domains:
                trace.log_event(
                    "dispatch_branch",
                    {
                        "branch": "multi-domain",
                        "scope_domains": dict(scope_domains),
                    },
                )
            if "domain" in result:
                trace.log_event(
                    "dispatch_branch",
                    {"branch": "override", "domain": result["domain"]},
                )
    except Exception:
        pass

    return result


def _absorb_scope_domain(target: dict[str, str], value: str) -> None:
    if "=" not in value:
        raise WorkArgsError(
            f"--scope-domain expects <name>=<domain>, got {value!r}"
        )
    name, dom = value.split("=", 1)
    name = name.strip()
    if not name:
        raise WorkArgsError(
            f"--scope-domain {value!r}: empty scope name"
        )
    target[name] = _validate_domain(dom.strip())


def main(args: list[str]) -> None:
    """CLI entry — emits parsed args as JSON.

    Usage: ``jarfis work-args "<arg-string>"``
    """
    if not args:
        json_error(
            "Usage: jarfis work-args <arg_string>\n"
            "Parses $ARGUMENTS for /jarfis:work override flags."
        )
        return
    arg_string = args[0]
    try:
        parsed = parse_work_args(arg_string)
    except WorkArgsError as exc:
        json_error(str(exc))
        sys.exit(1)
        return
    json_output(parsed)
