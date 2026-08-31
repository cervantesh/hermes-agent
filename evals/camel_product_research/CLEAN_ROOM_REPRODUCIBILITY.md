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
changing line-ending behavior for every JSONL file in Hermes. The post-fix
tree must be checked again from the clean clone before this receipt is treated
as complete.

## Overall verdict at the audited commit

The executable tests, static checks, public-row privacy boundary, record
counts, and published aggregate comparisons are reproducible. Byte-level
receipt verification was not reproducible in a default Windows checkout at
`00ecca1`; the committed blobs were correct, and the narrowly scoped
`.gitattributes` correction addresses the checkout defect. Final confirmation
requires a fresh checkout of the correction commit with all four worktree
hashes matching their metadata.
