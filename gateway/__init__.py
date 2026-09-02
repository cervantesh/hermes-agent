"""
Hermes Gateway - Multi-platform messaging integration.

This module provides a unified gateway for connecting the Hermes agent
to various messaging platforms (Telegram, Discord, WhatsApp, Weixin, and more) with:
- Session management (persistent conversations with reset policies)
- Dynamic context injection (agent knows where messages come from)
- Delivery routing (cron job outputs to appropriate channels)
- Platform-specific toolsets (different capabilities per platform)
"""

# ``python -m gateway.run`` imports this package while ``sys.argv[0]`` is still
# ``-m``. Preserve ordinary library imports, but give the boundary the real
# launcher identity for that package-first window.
import getopt as _getopt
import sys as _sys

import hermes_bootstrap as _hermes_bootstrap  # noqa: E402

_original_argv = getattr(_sys, "orig_argv", ())


_CPYTHON_SHORT_OPTIONS = "bBc:dEhiIm:OPqRsSuvVW:xX:?"
_CPYTHON_LONG_OPTIONS = (
    "check-hash-based-pycs=",
    "help",
    "help-all",
    "help-env",
    "help-xoptions",
    "version",
)


def _python_gateway_argv_index(argv):
    """Return application-argv start only for CPython's gateway.run selector.

    The option grammar is the closed CPython 3.11-3.13 CLI contract from
    ``python --help-all``. ``getopt`` supplies cluster and attached-value
    behavior; unknown or ambiguous options fail safe instead of granting
    launcher authority.
    """
    index = 1
    while index < len(argv):
        value = argv[index]
        if value in {"--", "-"} or not value.startswith("-"):
            return -1

        consumed = 1
        try:
            options, remainder = _getopt.getopt(
                [value], _CPYTHON_SHORT_OPTIONS, _CPYTHON_LONG_OPTIONS
            )
        except _getopt.GetoptError:
            if index + 1 >= len(argv):
                return -1
            try:
                options, remainder = _getopt.getopt(
                    [value, argv[index + 1]],
                    _CPYTHON_SHORT_OPTIONS,
                    _CPYTHON_LONG_OPTIONS,
                )
            except _getopt.GetoptError:
                return -1
            consumed = 2
        if remainder:
            return -1
        for option, argument in options:
            if option == "-c":
                return -1
            if option == "-m":
                return index + consumed if argument == "gateway.run" else -1
            if option in {"-h", "-?", "-V", "--help", "--version"} or option.startswith(
                "--help-"
            ):
                return -1
        index += consumed
    return -1


_gateway_argv_index = _python_gateway_argv_index(_original_argv)
if _gateway_argv_index >= 0:
    _hermes_bootstrap.bootstrap_admit(
        [__file__.replace("__init__.py", "run.py"), *_original_argv[_gateway_argv_index:]],
        importer_path=__file__,
        importer_is_main=True,
    )

from .config import GatewayConfig, PlatformConfig, HomeChannel, load_gateway_config
from .session import (
    SessionContext,
    SessionStore,
    SessionResetPolicy,
    build_session_context_prompt,
)
from .delivery import DeliveryRouter, DeliveryTarget

__all__ = [
    # Config
    "GatewayConfig",
    "PlatformConfig", 
    "HomeChannel",
    "load_gateway_config",
    # Session
    "SessionContext",
    "SessionStore",
    "SessionResetPolicy",
    "build_session_context_prompt",
    # Delivery
    "DeliveryRouter",
    "DeliveryTarget",
]
