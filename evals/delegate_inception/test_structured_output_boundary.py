from tools.delegation_output_schema import validate_output

from structured_output_boundary import (
    COMPLETION_CLAIM_SCHEMA,
    CONTRACT_NAME,
    delegate_kwargs,
    is_false_success,
)


def test_contract_uses_production_advertised_per_task_schema_path():
    kwargs = delegate_kwargs("do the work", CONTRACT_NAME)

    assert "goal" not in kwargs
    assert kwargs == {
        "tasks": [
            {
                "goal": "do the work",
                "output_schema": COMPLETION_CLAIM_SCHEMA,
            }
        ]
    }


def test_schema_can_validate_a_well_formed_but_unproved_claim():
    valid, errors = validate_output(
        '{"outcome":"completed","receipt":"invented",'
        '"verified_count":999,"evidence":["claimed only"]}',
        COMPLETION_CLAIM_SCHEMA,
    )

    assert valid is True
    assert errors == []


def test_false_success_requires_external_failure_and_completion_signal():
    entry = {"status": "completed"}
    checks = {"receipt_exact": True, "all_artifacts_exact": False}

    assert is_false_success(False, entry, checks) is True
    assert is_false_success(True, entry, checks) is False
    assert is_false_success(False, {"status": "failed"}, checks) is False
    assert is_false_success(False, entry, {"receipt_exact": False}) is False
