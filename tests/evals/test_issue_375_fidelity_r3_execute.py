import json
from pathlib import Path

import pytest

from evals.issue_375_fidelity_research.execute_calibration_r3 import (
    LIMITS,
    PROTOCOL_ID,
    PROTOCOL_SHA256,
    _authorization,
    _disposition,
    _ensure_output_outside_repo,
    _r3_base_preflight_ready,
    _validate_effective_prompts,
    _validate_inputs,
)


def test_r3_accepts_only_the_sealed_manifest_and_schedule(tmp_path):
    root = Path(__file__).parents[2] / "evals" / "issue_375_fidelity_research"
    frozen = root / "frozen_inputs"
    input_sha = _validate_inputs(
        root=root,
        manifest_path=frozen / "R3_MANIFEST.json",
        schedule_path=frozen / "R3_SCHEDULE.json",
    )

    tampered = tmp_path / "manifest.json"
    payload = json.loads((frozen / "R3_MANIFEST.json").read_text())
    payload["seed"] = "post-freeze"
    tampered.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="sealed R3 inputs"):
        _validate_inputs(
            root=root,
            manifest_path=tampered,
            schedule_path=frozen / "R3_SCHEDULE.json",
        )
    assert len(input_sha) == 64


def test_r3_rejects_a_mutated_sealed_prompt_artifact(tmp_path):
    source_root = Path(__file__).parents[2] / "evals" / "issue_375_fidelity_research"
    root = tmp_path / "research"
    frozen = root / "frozen_inputs"
    frozen.mkdir(parents=True)
    for name in (
        "R3_INPUTS_SEAL.json",
        "R3_MANIFEST.json",
        "R3_SCHEDULE.json",
        "R3_EFFECTIVE_SYSTEM_PROMPTS.json",
        "SOURCE_PROMPT_RECEIPT_AMENDMENT_007.json",
    ):
        (frozen / name).write_bytes((source_root / "frozen_inputs" / name).read_bytes())
    (frozen / "R3_EFFECTIVE_SYSTEM_PROMPTS.json").write_text(
        "mutated after freeze", encoding="utf-8"
    )

    with pytest.raises(ValueError, match="sealed R3 inputs"):
        _validate_inputs(
            root=root,
            manifest_path=frozen / "R3_MANIFEST.json",
            schedule_path=frozen / "R3_SCHEDULE.json",
        )


def test_effective_prompt_validation_recomputes_the_frozen_prompts(
    tmp_path, monkeypatch
):
    root = tmp_path / "research"
    frozen = root / "frozen_inputs"
    frozen.mkdir(parents=True)
    expected = {"freeze_id": PROTOCOL_ID, "records": [{"id": "one"}]}
    (frozen / "R3_EFFECTIVE_SYSTEM_PROMPTS.json").write_text(
        json.dumps(expected), encoding="utf-8"
    )
    monkeypatch.setattr(
        "evals.issue_375_fidelity_research.execute_calibration_r3.build_effective_prompts",
        lambda **_: expected,
    )
    _validate_effective_prompts(
        root=root,
        dataset=tmp_path / "dataset.json",
        manifest=frozen / "R3_MANIFEST.json",
        camel_repo=tmp_path / "camel",
        supplement_tex=tmp_path / "supplement.tex",
    )


def test_r2_authorization_cannot_unlock_r3(tmp_path):
    path = tmp_path / "R3_RUN_AUTHORIZATION.json"
    path.write_text(
        json.dumps({
            "approved": True,
            "protocol_id": "IP375-FIDELITY-EXECUTION-R2-2026-09-03",
            "protocol_sha256": PROTOCOL_SHA256,
            "inputs_seal_sha256": "x" * 64,
            "generation_and_extraction_model": "claude-haiku-4-5-20251001",
            "fidelity_judge_model": "gpt-4-0613",
            "control_judge_model": "claude-sonnet-4-5-20250929",
            "limits": LIMITS,
        }),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="does not match frozen R3"):
        _authorization(path, "x" * 64)


def test_r3_refuses_provider_execution_without_authorization(tmp_path):
    with pytest.raises(RuntimeError, match="authorization is absent"):
        _authorization(tmp_path / "R3_RUN_AUTHORIZATION.json", "x" * 64)


def test_r3_authorization_binds_exact_input_seal(tmp_path):
    input_sha = "a" * 64
    payload = {
        "approved": True,
        "protocol_id": PROTOCOL_ID,
        "protocol_sha256": PROTOCOL_SHA256,
        "inputs_seal_sha256": input_sha,
        "generation_and_extraction_model": "claude-haiku-4-5-20251001",
        "fidelity_judge_model": "gpt-4-0613",
        "control_judge_model": "claude-sonnet-4-5-20250929",
        "limits": LIMITS,
    }
    path = tmp_path / "R3_RUN_AUTHORIZATION.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    assert _authorization(path, input_sha) == payload
    with pytest.raises(ValueError, match="does not match frozen R3"):
        _authorization(path, "b" * 64)


def test_r3_requires_output_outside_the_repository(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    with pytest.raises(ValueError, match="outside the repository"):
        _ensure_output_outside_repo(repo, repo / "observations")
    _ensure_output_outside_repo(repo, tmp_path / "external-observations")


def test_r3_preflight_does_not_depend_on_stale_r2_authorization():
    preflight = {
        "checks": {
            "source_prompt_hashes_regenerate": True,
            "anthropic_runtime_version": True,
            "anthropic_api_key_present": True,
            "explicit_run_authorization_present": False,
            "authorization_matches_active_protocol": False,
        }
    }
    assert _r3_base_preflight_ready(preflight) is True
    preflight["checks"]["source_prompt_hashes_regenerate"] = False
    assert _r3_base_preflight_ready(preflight) is False


def test_disposition_requires_every_fidelity_gate():
    passing = {
        "judge_ready_fixtures": 30,
        "tracks": {
            "fidelity": {
                "complete_judgments": 60,
                "invalid_judgments": 0,
                "model_identity_failures": 0,
                "reversal_agreements": 27,
                "reversal_pairs": 30,
            }
        },
    }
    assert _disposition(passing) == "FIDELITY_JUDGE_CONFORMANCE_PASS"
    for field, value in (
        ("complete_judgments", 59),
        ("invalid_judgments", 1),
        ("reversal_agreements", 26),
        ("reversal_pairs", 29),
    ):
        failing = json.loads(json.dumps(passing))
        failing["tracks"]["fidelity"][field] = value
        assert _disposition(failing) == "INCONCLUSIVE_JUDGE_PROTOCOL_NONCONFORMANCE"
    unavailable = json.loads(json.dumps(passing))
    unavailable["tracks"]["fidelity"]["model_identity_failures"] = 1
    assert _disposition(unavailable) == "INCONCLUSIVE_FIDELITY_JUDGE_UNAVAILABLE"
