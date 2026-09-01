"""Stdlib-first console wrapper that closes normal Hermes before imports."""

from __future__ import annotations

import json
import sys

from hermes_cli.restricted_bootstrap import (
    AUTHORITY_INVALID,
    RestrictedBootstrapScanner,
    arm_process_authority,
    authority_artifact_exists,
    authority_path,
    emit_fixed_failure,
    resolve_global_hermes_root,
    root_config_path,
    validate_private_authority_file,
)


class FullHermesArgparseParser:
    """Lazy owner of the existing full Hermes argparse/startup path."""

    @staticmethod
    def run():
        from hermes_cli.main import main as full_main

        return full_main()


def _normal_main():
    return FullHermesArgparseParser.run()


def _prepare_closed_runtime(root):
    from hermes_cli.restricted_runtime import (
        RestrictedAuthorityError,
        RestrictedStateStore,
        load_root_config,
    )

    config = load_root_config(root)
    has_authority = authority_artifact_exists(root)
    store = RestrictedStateStore(root)
    if config.enabled and not has_authority:
        # A directly edited root config still arms before any normal import.
        store.initialize(config.expected_policy_epoch, config.expected_policy_digest)
        store.write_authority(
            config.expected_policy_epoch, config.expected_policy_digest
        )
        has_authority = True
    if has_authority:
        authority = store.read_authority()
        if config.enabled and (
            authority["policy_epoch"] != config.expected_policy_epoch
            or authority["policy_digest"] != config.expected_policy_digest
        ):
            raise RestrictedAuthorityError()
        arm_process_authority(root)
    return config, has_authority


def _dispatch(root, invocation, *, stdin, stdout):
    from hermes_cli.restricted_runtime import (
        RestrictedAuthorityError,
        restricted_disable,
        restricted_doctor,
        restricted_enable,
        restricted_status,
        run_one_shot,
        run_repl,
        validate_stdin_invocation,
    )
    from hermes_cli.subcommands.restricted import parse_restricted_invocation

    args = parse_restricted_invocation(invocation)
    if args.restricted_command == "enable":
        restricted_enable(
            args.policy_epoch,
            args.policy_digest,
            confirm_stopped=args.confirm_stopped,
            root=root,
        )
        stdout.write(
            "Restricted authority armed. --confirm-stopped is an operator declaration, "
            "not a verification; previously running Hermes processes remain outside this guarantee.\n"
        )
        return
    if args.restricted_command == "disable":
        restricted_disable(root)
        return
    if args.restricted_command == "status":
        stdout.write(
            json.dumps(restricted_status(root), sort_keys=True, separators=(",", ":"))
            + "\n"
        )
        return
    if args.restricted_command == "doctor":
        stdout.write(
            json.dumps(restricted_doctor(root), sort_keys=True, separators=(",", ":"))
            + "\n"
        )
        return
    if args.restricted_command == "run":
        validate_stdin_invocation(
            ["--stdin"] if args.stdin else [], stdin_isatty=stdin.isatty()
        )
        response = run_one_shot(stdin.buffer, root=root)
        stdout.write(response)
        if response and not response.endswith("\n"):
            stdout.write("\n")
        return
    raise RestrictedAuthorityError()


def main() -> None:
    root = resolve_global_hermes_root()
    scanner = RestrictedBootstrapScanner(sys.argv[1:], root_config_path(root))
    if not scanner.route_is_closed:
        return _normal_main()
    if scanner.authority_signal:
        try:
            validate_private_authority_file(authority_path(root))
        except RuntimeError:
            emit_fixed_failure(AUTHORITY_INVALID, 78)

    try:
        from hermes_cli.restricted_runtime import (
            RestrictedAuthorityError,
            RestrictedError,
            emit_restricted_error,
            run_repl,
        )

        config, has_authority = _prepare_closed_runtime(root)
        invocation = scanner.restricted_invocation
        if invocation is not None:
            # The interrupted-disable state deliberately admits only these
            # administrative routes; run/enable cannot ignore the conflict.
            command = invocation[0] if invocation else ""
            if (
                has_authority
                and not config.enabled
                and command not in {"status", "doctor", "disable"}
            ):
                raise RestrictedAuthorityError()
            _dispatch(root, invocation, stdin=sys.stdin, stdout=sys.stdout)
            return
        if not config.enabled and not has_authority:
            return _normal_main()
        if has_authority and not config.enabled:
            raise RestrictedAuthorityError()
        if not scanner.bare_candidate:
            from hermes_cli.restricted_runtime import RestrictedEntrypointBlocked

            raise RestrictedEntrypointBlocked()
        if not sys.stdin.isatty():
            from hermes_cli.restricted_runtime import RestrictedUsageError

            raise RestrictedUsageError()
        run_repl(root=root)
    except RestrictedError as exc:
        emit_restricted_error(exc)
        raise SystemExit(exc.exit_code)
    except SystemExit:
        raise
    except Exception:
        from hermes_cli.restricted_runtime import (
            RestrictedAuthorityError,
            emit_restricted_error,
        )

        exc = RestrictedAuthorityError()
        emit_restricted_error(exc)
        raise SystemExit(exc.exit_code)


__all__ = ["FullHermesArgparseParser", "main"]
