"""Ephemeral credential bridge for the sealed V7 scored runner."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .common.evidence import verify_seal
from .common.model_runtime import Cohort, ModelResult, run_model
from .context_cost.runner import run_case
from .isolation.runner import run_relationship_probe
from .scored_runner import run_study
from .selective_access.runner import run_b_boundary_gate
from .windows_execution_adapter import install as install_windows_adapter


ROOT = Path(__file__).resolve().parent
CODEX_MIN_REMAINING_SECONDS = 30 * 60
NON_REFRESHABLE_SENTINEL = "scr-v7-nonrefreshable"


def _load_codex_cli_tokens() -> dict[str, str] | None:
    from hermes_cli.auth import _import_codex_cli_tokens

    return _import_codex_cli_tokens()


def _codex_token_is_expiring(access_token: str, skew_seconds: int) -> bool:
    from hermes_cli.auth import _codex_access_token_is_expiring

    return _codex_access_token_is_expiring(access_token, skew_seconds)


def _save_temp_codex_tokens(tokens: dict[str, str]) -> None:
    from hermes_cli.auth import _save_codex_tokens

    _save_codex_tokens(tokens)


def run_authorized_model(
    *,
    cohort: Cohort,
    user_message: str,
    system_message: str,
    enabled_toolsets: tuple[str, ...],
) -> ModelResult:
    """Seed a non-refreshable Codex access token only in the active temp home."""

    if cohort.provider == "openai-codex":
        external = _load_codex_cli_tokens()
        access_token = str((external or {}).get("access_token") or "").strip()
        if not access_token:
            raise RuntimeError("Codex CLI access token is unavailable or expired")
        if _codex_token_is_expiring(access_token, CODEX_MIN_REMAINING_SECONDS):
            raise RuntimeError(
                "Codex CLI access token has less than 30 minutes remaining; "
                "refresh it before starting the sealed run"
            )
        _save_temp_codex_tokens({
            "access_token": access_token,
            "refresh_token": NON_REFRESHABLE_SENTINEL,
        })
    return run_model(
        cohort=cohort,
        user_message=user_message,
        system_message=system_message,
        enabled_toolsets=enabled_toolsets,
    )


def context_runner(**kwargs: Any) -> list[dict[str, Any]]:
    return run_case(**kwargs, model_call=run_authorized_model)


def boundary_runner(**kwargs: Any) -> dict[str, Any]:
    return run_b_boundary_gate(**kwargs, model_call=run_authorized_model)


def isolation_runner(**kwargs: Any) -> dict[str, Any]:
    return run_relationship_probe(**kwargs, model_call=run_authorized_model)


def verify_execution_chain() -> None:
    for seal_name in (
        "PROTOCOL_SEAL.json",
        "AMENDMENT_001_SEAL.json",
        "AMENDMENT_002_SEAL.json",
    ):
        verify_seal(ROOT, ROOT / seal_name)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--evidence-root", required=True)
    parser.add_argument("--label", required=True)
    args = parser.parse_args()
    verify_execution_chain()
    install_windows_adapter()
    receipt = run_study(
        evidence_root=Path(args.evidence_root).resolve(),
        label=args.label,
        context_runner=context_runner,
        boundary_runner=boundary_runner,
        isolation_runner=isolation_runner,
    )
    print(json.dumps({"observation_count": receipt["observation_count"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
