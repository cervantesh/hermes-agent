"""Console-script shims that prove launch intent before importing heavy targets."""

from __future__ import annotations

import sys

import hermes_bootstrap  # noqa: F401


def _admit(launcher: str) -> None:
    from hermes_application_boundary import bootstrap_admit

    bootstrap_admit(
        sys.argv,
        importer_path=__file__,
        importer_is_main=True,
        declared_launcher=launcher,
    )


def hermes_main():
    _admit("hermes")
    from hermes_cli.main import main

    return main()


def agent_main():
    _admit("hermes-agent")
    from run_agent import main

    return main()


def acp_main():
    _admit("hermes-acp")
    from acp_adapter.entry import main

    return main()
