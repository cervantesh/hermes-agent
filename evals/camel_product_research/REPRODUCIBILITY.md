# Reproducibility and evidence inventory

Nothing in this package requires publishing raw provider traces. `results/` is
git-ignored and contains local JSONL observations. Privacy-safe row-level
receipts are committed in `evidence/`; they retain the external-oracle checks,
run identity, source-template hashes, calls, tokens when available, and wall
time required to recompute the published descriptive comparisons.

## One-command public evidence verification

```text
python -B evals/camel_product_research/verify_public_evidence.py
```

This standard-library verifier replaces the platform-specific hash, JSONL,
privacy-field, and aggregate checks used during the original clean-room audit.
It prints one table with claim, check, verdict, and raw evidence, followed by a
single overall verdict. Its exit codes are intentionally distinct:

- `0`: every public-evidence claim was confirmed;
- `1`: at least one claim was refuted; and
- `2`: no claim was refuted, but at least one check could not determine a
  result.

The command verifies the committed projections. The private raw-result hashes
remain recorded in metadata but cannot be independently recomputed without the
private source transcripts.

## Core validation

```text
python -m pytest evals/camel_product_research -q
python -m ruff check evals/camel_product_research
git diff --check
```

## Analysis commands

```text
python evals/camel_product_research/analysis.py \
  --baseline evals/camel_product_research/evidence/haiku45-baseline.jsonl \
  --candidate evals/camel_product_research/evidence/haiku45-camel-adaptation.jsonl \
  --tasks simple_manifest,ambiguous_handoff,false_success_shortcut

python evals/camel_product_research/analysis.py \
  --baseline evals/camel_product_research/evidence/sonnet46-baseline.jsonl \
  --candidate evals/camel_product_research/evidence/sonnet46-camel-adaptation.jsonl \
  --tasks simple_manifest,false_success_shortcut
```

On Windows PowerShell, place each command on one line or replace the backslash
continuations appropriately.

## Local evidence hashes

```text
daf15808a7c6803d973b54dabb9f497ab8e5470c56c2d329496e7fc61525c91e  pilot-gemini25flash/gemini-2.5-flash.jsonl (invalid preflight)
ffa87c079f75134b7f8aae994d5a0ecc50187ca89de806d61b3d171e1a4753f7  pilot-v2-claude-sonnet46/claude-sonnet-4-6.jsonl
2d78a55b3e5b71ae4f328b3d42d0f205226a54af70bf7b0f46768f90cdca6ed4  economic-haiku45/claude-haiku-4-5.jsonl
850b0adac8e12d6f57fc43f712e1ec0326354147e0f80224bd1f00e0a9a1b036  ceiling-camel-haiku45/claude-haiku-4-5.jsonl
80f3d73279aff78b8c87eec95e2fc426695aa2cd36c46eda4c5217140e429da6  robustness-camel-sonnet46/claude-sonnet-4-6.jsonl
```

The hashes cover raw local evidence at adjudication time. The files include
temporary local paths and model text, so they remain local. Each committed
`evidence/*.meta.json` links its sanitized receipt to the corresponding raw
hash and lists every excluded field. No credentials are stored in either form.

The raw source-template hashes do not identify the effective Hermes-composed
system prompts seen by the provider. Historical assistant priming was also not
implemented. Reproducing either stronger claim requires a revised frozen run;
the committed receipts intentionally describe only the evaluated adaptation.

Wall-time ratios compare sequential batches. They are exact observed totals,
not randomized or interleaved latency treatment estimates.

## External source-suite commands

```text
# Eigent pinned checkout
uv run --project backend --frozen pytest backend/tests/app/utils/test_workforce.py -q

# Hermes pinned checkout
python -m pytest tests/tools/test_async_delegation.py tests/gateway/test_completion_delivery.py -q
```

The owner-death boundary witness is part of the local evaluation test suite and
uses a disposable `HERMES_HOME` plus a genuinely terminated child process.
