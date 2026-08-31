# Clean-room reproducibility receipt

## Audit frame

- Audited source commit: `00ecca192d2ef52a4e18666dc2bdcb2d74d84544`
- Source remote: `https://github.com/cervantesh/hermes-agent.git`
- Checkout: fresh detached clone, clean before and after validation
- Operating system: Windows 11 Home `10.0.26200` (build `26200`)
- Git: `2.54.0.windows.1`
- Git checkout policy: `core.autocrlf=true`
- Python: `3.11.7`
- pytest: `9.1.1`
- Ruff: `0.15.10`

The Python environment came from a separate Hermes worktree. It was used only
as the test and analysis runner; no dependency directory was copied into the
audited checkout. `PYTHONDONTWRITEBYTECODE=1` and pytest's no-cache plugin
option kept the checkout clean.

## Claim verification

| Claim | Check | Verdict | Raw evidence |
|---|---|---|---|
| The published commit is the tree under test | Detached checkout plus `git rev-parse HEAD` | Confirmed | `00ecca192d2ef52a4e18666dc2bdcb2d74d84544` |
| The evaluation test suite passes | `python -m pytest evals/camel_product_research -q -p no:cacheprovider` | Confirmed | `26 passed in 7.79s` |
| Static checks pass | `python -m ruff check evals/camel_product_research` | Confirmed | `All checks passed!` |
| Formatting is stable | `python -m ruff format --check evals/camel_product_research` | Confirmed | `26 files already formatted` |
| The audited worktree remains clean | `git diff --check` plus `git status --porcelain=v1` | Confirmed | no output from either check |
| The Haiku comparison reconstructs from committed receipts | `analysis.py` with the documented three-task subset | Confirmed | baseline `3/3`; candidate `1/3`; false success `2/3`; calls `3.74x`; observed wall time `8.41x`; discordance `2/0` |
| The Sonnet comparison reconstructs from committed receipts | `analysis.py` with the documented two-task subset | Confirmed | baseline `2/2`; candidate `2/2`; false success `0/2`; calls `2.92x`; observed wall time `2.02x`; discordance `0/0` |
| Sanitized receipts exclude the declared private fields | Parsed every JSONL row and checked `repo`, `camel_repo`, `summary`, `error`, `tool_trace`, and `protocol.messages` | Confirmed | no forbidden field found in 19 rows |
| Receipt record counts match their metadata | Counted non-empty JSONL rows and compared each `*.meta.json` | Confirmed | `7`, `3`, `7`, and `2` records, all matched |
| Receipt SHA-256 values match a default Windows working tree at the audited commit | SHA-256 over checked-out JSONL bytes | Refuted | all four worktree hashes differed because all 19 line endings were converted to CRLF |
| Receipt SHA-256 values match the committed Git blobs at the audited commit | SHA-256 over `git cat-file blob HEAD:<path>` | Confirmed | all four blob hashes matched `evidence_sha256` |

## Defect found and correction

The mismatch was checkout normalization, not evidence corruption. The Git
blobs were LF-delimited and matched the published hashes exactly. The existing
`.gitattributes` covered `*.json` but not `*.jsonl`; with
`core.autocrlf=true`, a fresh Windows clone checked each receipt out as CRLF.
That made a documented byte-level hash check fail even though the parsed rows
and reconstructed aggregates remained correct.

The package now declares:

```gitattributes
evals/camel_product_research/evidence/*.jsonl text eol=lf
```

This is deliberately scoped to the published research receipts rather than
changing line-ending behavior for every JSONL file in Hermes.

## Post-fix clean-room confirmation

The correction commit
`5765782175752b17a2a6f7dca84a8ab8ffee64cf` was then cloned into a second,
new checkout using the same Windows environment and `core.autocrlf=true`.
The first audit checkout was not reused.

| Claim | Verdict | Raw evidence |
|---|---|---|
| Exact correction tree checked out | Confirmed | `5765782175752b17a2a6f7dca84a8ab8ffee64cf` |
| Evaluation suite | Confirmed | `26 passed in 7.08s` |
| Ruff lint and format | Confirmed | `All checks passed!`; `27 files already formatted` |
| Clean checkout before and after validation | Confirmed | empty `git status --porcelain=v1` |
| All four worktree receipt hashes match `evidence_sha256` | Confirmed | `7`, `3`, `7`, and `2` records; four hash matches |
| Receipt line endings remain LF | Confirmed | zero CRLF sequences across all 19 JSONL rows |
| Declared private fields remain absent | Confirmed | zero forbidden fields across all 19 rows |
| Haiku aggregates reconstruct | Confirmed | `3/3` versus `1/3`; two false successes; `3.74x` calls; `8.41x` observed wall time; discordance `2/0` |
| Sonnet aggregates reconstruct | Confirmed | `2/2` versus `2/2`; zero false successes; `2.92x` calls; `2.02x` observed wall time; discordance `0/0` |

## Reusable Python verifier

The receipt hash, line-ending, record-count, privacy-field, and aggregate
checks from this audit are now implemented as a cross-platform command:

```text
python -B evals/camel_product_research/verify_public_evidence.py
```

The implementation was developed test-first. Five focused tests cover the
confirmed package, a modified receipt hash, a missing receipt, an unreadable
input, and an aggregate that drifts after its receipt metadata is rehashed.
The verifier reports `CONFIRMED`, `REFUTED`, or `UNDETERMINED` per claim and
returns exit code `0`, `1`, or `2`, respectively. Its first run over the
published receipts returned six confirmed claims and `OVERALL: CONFIRMED`.

## Linux clean-room confirmation

The automated verifier and full evaluation suite were then run from a new
Ubuntu 24.04 WSL2 checkout, not from the Windows worktree:

- Hermes research commit:
  `92f952d68069a070d03c514756db6ec00f8ea7dd`
- CAMEL source commit:
  `c402032a7f7cd27e196356fbcf413c521a8cb4ca`
- Linux kernel: `6.6.87.2-microsoft-standard-WSL2`, `x86_64`
- Git: `2.43.0`
- Python: `3.12.3`
- pytest: `9.1.1`
- Ruff: `0.15.10`

The isolated Linux virtual environment installed the Hermes project from the
exact audited checkout, rather than borrowing dependencies from the Windows
environment. `CAMEL_RESEARCH_REPO` pointed at a separate, detached clone of
the pinned paper-era CAMEL source.

An initial minimal environment correctly exposed two undeclared audit
assumptions: four tests used the Windows-only `C:/dev/camel-audit` default,
and the owner-death witness imported Hermes runtime dependencies that were not
present when only pytest and Ruff were installed. The source path is now
explicitly configurable, and the final audit installed Hermes's declared
runtime dependencies before executing its integration witness. Neither issue
changed evidence rows, aggregates, or production code.

| Claim | Check | Verdict | Raw evidence |
|---|---|---|---|
| The published Linux audit commit is the tree under test | Detached clean checkout plus `git rev-parse HEAD` | Confirmed | `92f952d68069a070d03c514756db6ec00f8ea7dd` |
| The Python verifier is platform-independent | Run the one-command verifier under Python 3.12 | Confirmed | six claims confirmed; `OVERALL: CONFIRMED` |
| The full evaluation suite passes on Linux | Run pytest with the pinned CAMEL source and declared Hermes runtime | Confirmed | `31 passed in 8.53s` |
| Static checks pass on Linux | Ruff check | Confirmed | `All checks passed!` |
| Formatting is stable on Linux | Ruff format check | Confirmed | `29 files already formatted` |
| The Linux checkout remains unchanged | `git diff --check` and `git status --porcelain=v1` | Confirmed | no output from either command |

## Overall verdict at the audited commit

The executable tests, static checks, public-row privacy boundary, record
counts, and published aggregate comparisons are reproducible. Byte-level
receipt verification was not reproducible in a default Windows checkout at
`00ecca1`; the committed blobs were correct, and the narrowly scoped
`.gitattributes` correction fixed the checkout defect. A second clean clone of
the correction commit confirmed that all four checked-out receipts now match
their published metadata hashes. The later Linux clean-room run independently
confirmed the same public evidence, aggregate reconstruction, evaluation
tests, and clean-tree guarantees.
