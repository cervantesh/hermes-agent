import json
from dataclasses import dataclass

from evals.issue_375_fidelity_research.protocol import Generation
from evals.issue_375_fidelity_research.runner import (
    PairStore,
    parse_judge_scores,
    run_lane_r_pair,
)
from evals.issue_375_fidelity_research.sources import PromptSources


@dataclass
class QueueBackend:
    outputs: list[str]

    def __post_init__(self):
        self.receipts = []

    def complete(self, *, agent, system_prompt, messages, parameters):
        text = self.outputs.pop(0)
        self.receipts.append({
            "agent": agent,
            "system_prompt_sha256": "hash",
            "messages_sha256": "hash",
            "response_sha256": "hash",
            "usage": {"input_tokens": 1, "output_tokens": 1},
            "attempts": 1,
        })
        return Generation(text=text, finish_reason="stop", usage={})


def _sources():
    return PromptSources(
        original_assistant="OA <ASSISTANT_ROLE> <USER_ROLE> <TASK>",
        original_user="OU <USER_ROLE> <ASSISTANT_ROLE> <TASK>",
        task_specifier="unused",
        ablated_assistant="AA <ASSISTANT_ROLE> <USER_ROLE> <TASK>",
        ablated_user="AU <USER_ROLE> <ASSISTANT_ROLE> <TASK>",
        solution_extraction="extract exactly",
        evaluation_system="judge exactly",
        evaluation_template="Q={question}\nA1={answer_1}\nA2={answer_2}\nP={prompt}",
        evaluation_instruction="score",
    )


def test_judge_parser_requires_exact_two_score_first_line():
    assert parse_judge_scores("8 6\nexplanation") == (8.0, 6.0)
    for invalid in ("scores: 8 6", "8", "11 2", "8 6 4", "eight six"):
        try:
            parse_judge_scores(invalid)
        except ValueError:
            pass
        else:
            raise AssertionError(f"accepted malformed judge output: {invalid}")


def test_lane_r_pair_runs_two_arms_extracts_and_blind_judges():
    generator = QueueBackend([
        "hidden original",
        "<CAMEL_TASK_DONE>",
        "discarded original assistant",
        "hidden ablated",
        "<CAMEL_TASK_DONE>",
        "discarded ablated assistant",
    ])
    extractor = QueueBackend(["original solution", "ablated solution"])
    judge = QueueBackend([
        "8 6\nOriginal-looking answer was stronger.",
        "6 8\nThe mapped preference remains the same after reversal.",
    ])
    task = {
        "id": "task-1",
        "original_task": "original task",
        "specified_task": "specified task",
        "assistant_role": "Programmer",
        "user_role": "Filmmaker",
    }
    schedule = {
        "task_id": "task-1",
        "generation_order": ["original", "ablated"],
        "judge_order": ["original", "ablated"],
        "blind_labels": ["Assistant 1", "Assistant 2"],
        "order_reversal": True,
    }

    private, public = run_lane_r_pair(
        task=task,
        schedule=schedule,
        sources=_sources(),
        generator=generator,
        extractor=extractor,
        judge=judge,
    )

    assert private["outcome"] == "original"
    assert private["scores"] == {"original": 8.0, "ablated": 6.0}
    assert private["solutions"] == {
        "original": "original solution",
        "ablated": "ablated solution",
    }
    assert public["outcome"] == "original"
    assert public["reversal"]["outcome"] == "original"
    assert public["reversal"]["disagrees"] is False
    serialized_public = json.dumps(public)
    assert "original solution" not in serialized_public
    assert "specified task" not in serialized_public
    assert "Original-looking" not in serialized_public
    assert public["arms"]["original"]["solution_length"] == len("original solution")


def test_pair_store_resumes_completed_and_quarantines_interrupted_pair(tmp_path):
    store = PairStore(tmp_path)
    assert store.begin("done") is True
    store.complete("done", {"secret": "raw"}, {"safe": "receipt"})
    assert store.begin("done") is False
    assert store.load_public("done") == {"safe": "receipt"}

    assert store.begin("interrupted") is True
    recovered = store.recover_interrupted()

    assert recovered == ["interrupted"]
    assert store.load_public("interrupted")["status"] == "QUARANTINED_INTERRUPTED_PAIR"
    assert store.begin("interrupted") is False
