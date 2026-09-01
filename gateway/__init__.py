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
import sys as _sys

import hermes_bootstrap as _hermes_bootstrap  # noqa: E402

_original_argv = getattr(_sys, "orig_argv", ())
try:
    _module_index = _original_argv.index("-m")
except ValueError:
    _module_index = -1
if _module_index >= 0 and tuple(_original_argv[_module_index + 1 : _module_index + 2]) == ("gateway.run",):
    _hermes_bootstrap.bootstrap_admit(
        [__file__.replace("__init__.py", "run.py"), *_original_argv[_module_index + 2 :]]
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
