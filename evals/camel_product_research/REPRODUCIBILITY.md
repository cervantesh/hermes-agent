# Reproducibility and evidence inventory

Nothing in this package requires publishing raw provider traces. `results/` is
git-ignored and contains local JSONL observations. The committed analysis code
recomputes descriptive comparisons from those files.

## Core validation

```text
python -m pytest evals/camel_product_research -q
python -m ruff check evals/camel_product_research
git diff --check
```

## Analysis commands

```text
python evals/camel_product_research/analysis.py \
  --baseline evals/camel_product_research/results/economic-haiku45/claude-haiku-4-5.jsonl \
  --candidate evals/camel_product_research/results/ceiling-camel-haiku45/claude-haiku-4-5.jsonl

python evals/camel_product_research/analysis.py \
  --baseline evals/camel_product_research/results/pilot-v2-claude-sonnet46/claude-sonnet-4-6.jsonl \
  --candidate evals/camel_product_research/results/robustness-camel-sonnet46/claude-sonnet-4-6.jsonl
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
temporary local paths and model text, so they should be sanitized before any
future publication. No credentials are stored in them.

## External source-suite commands

```text
# Eigent pinned checkout
uv run --project backend --frozen pytest backend/tests/app/utils/test_workforce.py -q

# Hermes pinned checkout
python -m pytest tests/tools/test_async_delegation.py tests/gateway/test_completion_delivery.py -q
```

The owner-death boundary witness is part of the local evaluation test suite and
uses a disposable `HERMES_HOME` plus a genuinely terminated child process.
