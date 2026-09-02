from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

import pytest

from .shared_context import ContextContractError, WorkflowContextStore


def test_uncommitted_value_is_invisible() -> None:
    store = WorkflowContextStore()
    tx = store.begin("wf", declared_writes=["result"])
    tx.stage("result", {"value": 1})
    with pytest.raises(ContextContractError):
        store.view("wf", declared_reads=["result"]).read("result")
    tx.abort()
    with pytest.raises(ContextContractError):
        store.view("wf", declared_reads=["result"]).read("result")


def test_write_once_and_idempotent_replay() -> None:
    store = WorkflowContextStore()
    first = store.begin("wf", declared_writes=["result"])
    first.stage("result", {"value": 1})
    original = first.commit()[0]
    replay = store.begin("wf", declared_writes=["result"])
    replay.stage("result", {"value": 1})
    assert replay.commit()[0] == original
    conflict = store.begin("wf", declared_writes=["result"])
    conflict.stage("result", {"value": 2})
    with pytest.raises(ContextContractError, match="write-once conflict"):
        conflict.commit()


def test_declared_reads_and_writes_fail_closed() -> None:
    store = WorkflowContextStore()
    tx = store.begin("wf", declared_writes=["allowed"])
    with pytest.raises(ContextContractError, match="undeclared write"):
        tx.stage("other", 1)
    tx.stage("allowed", 1)
    tx.commit()
    with pytest.raises(ContextContractError, match="undeclared read"):
        store.view("wf", declared_reads=[]).read("allowed")


def test_concurrent_workflows_are_isolated() -> None:
    store = WorkflowContextStore()

    def publish(workflow: str, value: int) -> int:
        tx = store.begin(workflow, declared_writes=["result"])
        tx.stage("result", {"value": value})
        tx.commit()
        payload = store.view(workflow, declared_reads=["result"]).read("result")
        return int(payload.payload.decode().split(":")[1].rstrip("}"))

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(lambda item: publish(*item), [("a", 1), ("b", 2)])) == [
            1,
            2,
        ]
    assert store.workflow_keys("a") == {"result"}
    assert store.workflow_keys("b") == {"result"}


def test_downstream_view_has_no_mutation_surface() -> None:
    store = WorkflowContextStore()
    tx = store.begin("wf", declared_writes=["result"])
    tx.stage("result", 1)
    tx.commit()
    view = store.view("wf", declared_reads=["result"])
    assert not hasattr(view, "stage")
    assert not hasattr(view, "commit")
