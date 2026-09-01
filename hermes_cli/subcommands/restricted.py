"""Argument definitions for the closed restricted-runtime command group."""

from __future__ import annotations

import argparse


class _ClosedParser(argparse.ArgumentParser):
    def error(self, _message):
        from hermes_cli.restricted_runtime import RestrictedUsageError

        raise RestrictedUsageError()


def build_restricted_parser(subparsers, *, cmd_restricted=None):
    parser = subparsers.add_parser(
        "restricted",
        help="Operate the text-only restricted runtime",
        description="Operate the closed text-only restricted runtime.",
    )
    commands = parser.add_subparsers(dest="restricted_command")
    enable = commands.add_parser("enable", add_help=False)
    enable.add_argument("--policy-epoch", required=True)
    enable.add_argument("--policy-digest", required=True)
    enable.add_argument("--confirm-stopped", action="store_true")
    commands.add_parser("disable", add_help=False)
    commands.add_parser("status", add_help=False)
    commands.add_parser("doctor", add_help=False)
    run = commands.add_parser("run", add_help=False)
    run.add_argument("--stdin", action="store_true")
    if cmd_restricted is not None:
        parser.set_defaults(func=cmd_restricted)
    return parser


def parse_restricted_invocation(tokens: tuple[str, ...]):
    parser = _ClosedParser(
        prog="hermes restricted", add_help=False, exit_on_error=False
    )
    commands = parser.add_subparsers(
        dest="restricted_command", required=True, parser_class=_ClosedParser
    )
    enable = commands.add_parser("enable", add_help=False, exit_on_error=False)
    enable.add_argument("--policy-epoch", required=True)
    enable.add_argument("--policy-digest", required=True)
    enable.add_argument("--confirm-stopped", action="store_true")
    commands.add_parser("disable", add_help=False, exit_on_error=False)
    commands.add_parser("status", add_help=False, exit_on_error=False)
    commands.add_parser("doctor", add_help=False, exit_on_error=False)
    run = commands.add_parser("run", add_help=False, exit_on_error=False)
    run.add_argument("--stdin", action="store_true")
    try:
        return parser.parse_args(list(tokens))
    except (argparse.ArgumentError, SystemExit) as exc:
        from hermes_cli.restricted_runtime import RestrictedUsageError

        raise RestrictedUsageError() from exc


def cmd_restricted(_args):
    """Defensive normal-parser handler; the wrapper should own this route."""

    from hermes_cli.restricted_runtime import RestrictedAuthorityError

    raise RestrictedAuthorityError()


__all__ = ["build_restricted_parser", "cmd_restricted", "parse_restricted_invocation"]
