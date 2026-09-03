from __future__ import annotations

import pytest

from .harness import (
    AccessDenied,
    AccessPolicy,
    Observation,
    OpaqueCorpus,
    ResourceResult,
    exact_subset_digest,
    project_declared,
    project_full,
    resource_gate,
)


def test_opaque_corpus_is_repeatable_and_seed_separated() -> None:
    first = OpaqueCorpus.generate(seed=17, record_count=8, value_bytes=48)
    repeated = OpaqueCorpus.generate(seed=17, record_count=8, value_bytes=48)
    other = OpaqueCorpus.generate(seed=18, record_count=8, value_bytes=48)

    assert first == repeated
    assert first != other
    assert len(first.records) == 8
    assert all(len(value.encode("ascii")) == 48 for value in first.records.values())


def test_declared_projection_preserves_exact_oracle_with_less_context() -> None:
    corpus = OpaqueCorpus.generate(seed=4, record_count=64, value_bytes=128)
    requested = (corpus.keys[7], corpus.keys[41])

    full = project_full(corpus)
    declared = project_declared(corpus, requested)

    assert exact_subset_digest(full.payload, requested) == exact_subset_digest(
        declared.payload, requested
    )
    assert declared.utf8_bytes < full.utf8_bytes
    assert tuple(declared.payload) == requested


def test_declared_projection_rejects_unknown_or_duplicate_keys() -> None:
    corpus = OpaqueCorpus.generate(seed=2, record_count=3, value_bytes=16)

    with pytest.raises(KeyError):
        project_declared(corpus, ("missing",))
    with pytest.raises(ValueError, match="duplicate"):
        project_declared(corpus, (corpus.keys[0], corpus.keys[0]))


@pytest.mark.parametrize(
    ("owner_task", "requester_task", "declared_parents", "completed", "allowed"),
    [
        ("task-a", "task-a", (), (), True),
        ("parent", "child", ("parent",), ("parent",), True),
        ("parent", "child", (), ("parent",), False),
        ("parent", "child", ("parent",), (), False),
        ("sibling", "child", ("parent",), ("parent", "sibling"), False),
    ],
)
def test_access_policy_task_relationships(
    owner_task: str,
    requester_task: str,
    declared_parents: tuple[str, ...],
    completed: tuple[str, ...],
    allowed: bool,
) -> None:
    policy = AccessPolicy(
        workflow_id="wf-1",
        tenant_id="tenant-1",
        board_id="board-1",
        requester_task=requester_task,
        declared_parent_tasks=frozenset(declared_parents),
        completed_tasks=frozenset(completed),
        declared_keys=frozenset({"key-1"}),
    )

    if allowed:
        policy.authorize(
            owner_task=owner_task,
            workflow_id="wf-1",
            tenant_id="tenant-1",
            board_id="board-1",
            key="key-1",
        )
    else:
        with pytest.raises(AccessDenied):
            policy.authorize(
                owner_task=owner_task,
                workflow_id="wf-1",
                tenant_id="tenant-1",
                board_id="board-1",
                key="key-1",
            )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("workflow_id", "wf-2"),
        ("tenant_id", "tenant-2"),
        ("board_id", "board-2"),
        ("key", "undeclared"),
    ],
)
def test_access_policy_denies_every_frozen_boundary(field: str, value: str) -> None:
    policy = AccessPolicy(
        workflow_id="wf-1",
        tenant_id="tenant-1",
        board_id="board-1",
        requester_task="child",
        declared_parent_tasks=frozenset({"parent"}),
        completed_tasks=frozenset({"parent"}),
        declared_keys=frozenset({"key-1"}),
    )
    request = {
        "owner_task": "parent",
        "workflow_id": "wf-1",
        "tenant_id": "tenant-1",
        "board_id": "board-1",
        "key": "key-1",
    }
    request[field] = value

    with pytest.raises(AccessDenied, match=field):
        policy.authorize(**request)


def test_resource_gate_requires_two_cohorts_and_no_other_metric_regression() -> None:
    passing = [
        ResourceResult(
            "model-a",
            True,
            baseline_tokens=1000,
            candidate_tokens=800,
            baseline_latency_ms=100,
            candidate_latency_ms=95,
        ),
        ResourceResult(
            "model-b",
            True,
            baseline_tokens=900,
            candidate_tokens=720,
            baseline_latency_ms=120,
            candidate_latency_ms=115,
        ),
    ]
    assert resource_gate(passing).passed

    one_cohort = passing[:1]
    assert not resource_gate(one_cohort).passed

    latency_regression = [
        ResourceResult(
            "model-a",
            True,
            baseline_tokens=1000,
            candidate_tokens=700,
            baseline_latency_ms=100,
            candidate_latency_ms=140,
        ),
        ResourceResult(
            "model-b",
            True,
            baseline_tokens=1000,
            candidate_tokens=700,
            baseline_latency_ms=100,
            candidate_latency_ms=140,
        ),
    ]
    assert not resource_gate(latency_regression).passed


def test_observation_requires_external_oracle_and_measured_tokens() -> None:
    with pytest.raises(ValueError, match="external oracle"):
        Observation(
            track="context_cost",
            arm="B",
            cohort="model-a",
            seed=1,
            external_oracle=None,
            prompt_bytes=42,
        )

    observation = Observation(
        track="context_cost",
        arm="B",
        cohort="model-a",
        seed=1,
        external_oracle=True,
        prompt_bytes=42,
    )
    assert observation.input_tokens is None
    assert observation.token_source is None
