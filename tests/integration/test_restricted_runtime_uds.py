import pytest


@pytest.mark.linux_only
def test_restricted_uds_live_contract_is_exercised_by_client_suite():
    """OS lane sentinel: the live AF_UNIX/SO_PEERCRED suite must be collected."""
    from hermes_cli.restricted_runtime import platform_supports_restricted_runtime

    assert platform_supports_restricted_runtime()


@pytest.mark.windows_only
def test_native_windows_fails_before_attempting_transport(monkeypatch):
    import socket

    from hermes_cli.restricted_runtime import (
        RestrictedPlatformError,
        RestrictedUdsClient,
    )

    monkeypatch.setattr(
        socket,
        "socket",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("transport attempted")
        ),
    )
    with pytest.raises(RestrictedPlatformError):
        RestrictedUdsClient().ready("epoch", "f" * 64)
