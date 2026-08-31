import pytest

from runner import _completed


IDENTITY = {"head": "abc", "dirty": False, "tree_digest": "abc"}


def _row(**overrides) -> dict:
    item = {
        "strategy": "baseline",
        "task": "simple_manifest",
        "rep": 1,
        "label": "pilot",
        "provider": "claude-code",
        "model": "test-model",
        "schedule_seed": 375,
        **IDENTITY,
    }
    item.update(overrides)
    return item


def _resume(records: list[dict]):
    return _completed(
        records,
        label="pilot",
        provider="claude-code",
        model="test-model",
        seed=375,
        identity=IDENTITY,
    )


def test_resume_accepts_one_exact_identity() -> None:
    assert _resume([_row()]) == {("baseline", "simple_manifest", 1)}


def test_resume_rejects_duplicate_or_mixed_identity() -> None:
    with pytest.raises(ValueError, match="duplicate existing result"):
        _resume([_row(), _row()])
    with pytest.raises(ValueError, match="mixes model"):
        _resume([_row(model="other-model")])
    with pytest.raises(ValueError, match="mixes tree_digest"):
        _resume([_row(tree_digest="dirty-tree")])
