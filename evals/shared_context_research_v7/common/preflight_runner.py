"""Run provider-free V7 preflights against isolated real Hermes boards."""

from __future__ import annotations

import argparse
from contextlib import contextmanager
from dataclasses import asdict
import json
import os
from pathlib import Path
import tempfile
from typing import Iterator
import uuid

from hermes_cli import kanban_db as kb

from ..context_cost.preflight import run_context_cost_preflight
from ..isolation.preflight import classify_current_read
from ..selective_access.preflight import run_selective_access_preflight
from .evidence import EvidenceLedger
from .harness import OpaqueCorpus
from .hermes_fixture import install_corpus_graph, read_task_through_kanban_show


@contextmanager
def _isolated_hermes_home() -> Iterator[str]:
    previous = os.environ.get("HERMES_HOME")
    with tempfile.TemporaryDirectory(prefix="hermes-scr-v7-") as temporary:
        isolation_id = uuid.uuid4().hex
        home = Path(temporary) / isolation_id / ".hermes"
        home.mkdir(parents=True)
        os.environ["HERMES_HOME"] = str(home)
        kb.init_db()
        try:
            yield isolation_id
        finally:
            if previous is None:
                os.environ.pop("HERMES_HOME", None)
            else:
                os.environ["HERMES_HOME"] = previous


def _context_case(*, seed: int, all_records: bool) -> dict:
    with _isolated_hermes_home() as isolation_id:
        corpus = OpaqueCorpus.generate(
            seed=seed,
            record_count=12 if all_records else 80,
            value_bytes=32 if all_records else 96,
        )
        requested = corpus.keys if all_records else (corpus.keys[7], corpus.keys[73])
        graph = install_corpus_graph(corpus)
        row = asdict(run_context_cost_preflight(graph, corpus, requested))
        row.update(
            case="context_all_records" if all_records else "context_subset",
            track="context_cost",
            isolation_id=isolation_id,
        )
        return row


def _selective_case(*, seed: int, above_cap: bool) -> dict:
    with _isolated_hermes_home() as isolation_id:
        corpus = OpaqueCorpus.generate(
            seed=seed,
            record_count=100 if above_cap else 5,
            value_bytes=128 if above_cap else 64,
        )
        requested = (corpus.keys[-1],)
        graph = install_corpus_graph(corpus)
        row = asdict(run_selective_access_preflight(graph, corpus, requested))
        row.update(
            case="selective_above_cap" if above_cap else "selective_below_cap",
            track="selective_access",
            isolation_id=isolation_id,
        )
        return row


def _isolation_case(*, declared_parent: bool) -> dict:
    with _isolated_hermes_home() as isolation_id:
        canary = f"canary-{uuid.uuid4().hex}"
        with kb.connect_closing() as conn:
            owner = kb.create_task(conn, title="owner", body=canary)
            requester = kb.create_task(conn, title="requester")
            if declared_parent:
                kb.link_tasks(conn, owner, requester)
                kb.complete_task(conn, owner, result=canary)
        visible = canary in read_task_through_kanban_show(owner).raw
        relationship = (
            "declared_completed_parent" if declared_parent else "unrelated_same_board"
        )
        row = asdict(
            classify_current_read(
                requester_task=requester,
                owner_task=owner,
                relationship=relationship,
                visible=visible,
            )
        )
        row.update(
            case=(
                "isolation_declared_parent"
                if declared_parent
                else "isolation_unrelated"
            ),
            track="isolation",
            isolation_id=isolation_id,
        )
        return row


def run_preflights(evidence_root: Path, label: str) -> dict:
    ledger = EvidenceLedger.create(evidence_root, label)
    rows = [
        _context_case(seed=71, all_records=False),
        _context_case(seed=72, all_records=True),
        _selective_case(seed=81, above_cap=True),
        _selective_case(seed=82, above_cap=False),
        _isolation_case(declared_parent=False),
        _isolation_case(declared_parent=True),
    ]
    for row in rows:
        ledger.append(row)
    receipt = {
        "freeze_id": "SCR-V7-INITIAL-2026-09-02",
        "hermes_revision": "593aa74c6182ce2e5e23bc102daaaae71710c05d",
        "kind": "provider_free_preflight",
        "observation_count": len(rows),
        "rows": rows,
    }
    (ledger.directory / "receipt.json").write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--evidence-root", required=True)
    parser.add_argument("--label", required=True)
    args = parser.parse_args()
    receipt = run_preflights(Path(args.evidence_root).resolve(), args.label)
    print(json.dumps({"observation_count": receipt["observation_count"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
