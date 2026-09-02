"""Harness-only workflow scratchpad with explicit authority boundaries."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import threading
import uuid
from typing import Any, Iterable


class ContextContractError(ValueError):
    """Raised when a workflow violates its declared context contract."""


def canonical_bytes(value: Any) -> bytes:
    """Return the one frozen canonical JSON representation."""
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def digest_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


@dataclass(frozen=True)
class ContextValue:
    workflow_id: str
    key: str
    payload: bytes
    sha256: str


class PublishTransaction:
    """An invisible staged write that becomes readable only on commit."""

    def __init__(
        self,
        store: "WorkflowContextStore",
        workflow_id: str,
        declared_writes: frozenset[str],
    ) -> None:
        self._store = store
        self.workflow_id = workflow_id
        self.declared_writes = declared_writes
        self.transaction_id = uuid.uuid4().hex
        self._staged: dict[str, bytes] = {}
        self._closed = False

    def stage(self, key: str, value: Any) -> None:
        if self._closed:
            raise ContextContractError("transaction is already closed")
        if key not in self.declared_writes:
            raise ContextContractError(f"undeclared write: {key}")
        self._staged[key] = canonical_bytes(value)

    def commit(self) -> list[ContextValue]:
        if self._closed:
            raise ContextContractError("transaction is already closed")
        self._closed = True
        return self._store._commit(self.workflow_id, self._staged)

    def abort(self) -> None:
        self._staged.clear()
        self._closed = True


class ReadOnlyWorkflowView:
    """Downstream view: declared reads only and no mutation surface."""

    def __init__(
        self,
        store: "WorkflowContextStore",
        workflow_id: str,
        declared_reads: Iterable[str],
    ) -> None:
        self._store = store
        self.workflow_id = workflow_id
        self.declared_reads = frozenset(declared_reads)

    def read(self, key: str) -> ContextValue:
        if key not in self.declared_reads:
            raise ContextContractError(f"undeclared read: {key}")
        return self._store._read(self.workflow_id, key)


class WorkflowContextStore:
    """Thread-safe, write-once values isolated by workflow id.

    This class deliberately has no persistence and is not production code. It
    is the treatment simulated by arm C.
    """

    def __init__(self) -> None:
        self._values: dict[tuple[str, str], ContextValue] = {}
        self._lock = threading.RLock()

    def begin(
        self, workflow_id: str, *, declared_writes: Iterable[str]
    ) -> PublishTransaction:
        workflow_id = workflow_id.strip()
        if not workflow_id:
            raise ContextContractError("workflow_id is required")
        writes = frozenset(str(key).strip() for key in declared_writes)
        if not writes or "" in writes:
            raise ContextContractError("at least one non-empty write key is required")
        return PublishTransaction(self, workflow_id, writes)

    def view(
        self, workflow_id: str, *, declared_reads: Iterable[str]
    ) -> ReadOnlyWorkflowView:
        return ReadOnlyWorkflowView(self, workflow_id, declared_reads)

    def _commit(self, workflow_id: str, staged: dict[str, bytes]) -> list[ContextValue]:
        if not staged:
            raise ContextContractError("cannot commit an empty transaction")
        with self._lock:
            for key, payload in staged.items():
                existing = self._values.get((workflow_id, key))
                if existing is not None and existing.payload != payload:
                    raise ContextContractError(
                        f"write-once conflict for {workflow_id}/{key}"
                    )
            committed: list[ContextValue] = []
            for key, payload in staged.items():
                identity = (workflow_id, key)
                value = self._values.get(identity)
                if value is None:
                    value = ContextValue(
                        workflow_id=workflow_id,
                        key=key,
                        payload=payload,
                        sha256=digest_bytes(payload),
                    )
                    self._values[identity] = value
                committed.append(value)
            return committed

    def _read(self, workflow_id: str, key: str) -> ContextValue:
        with self._lock:
            try:
                return self._values[(workflow_id, key)]
            except KeyError:
                raise ContextContractError(
                    f"no committed value for {workflow_id}/{key}"
                ) from None

    def workflow_keys(self, workflow_id: str) -> frozenset[str]:
        """Harness inspection only; not exposed by downstream views."""
        with self._lock:
            return frozenset(
                key for (candidate, key) in self._values if candidate == workflow_id
            )
