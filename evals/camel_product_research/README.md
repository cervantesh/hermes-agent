# CAMEL and Eigent product research

This directory contains a local-first, preregistered research program for
deciding whether CAMEL RolePlaying or Eigent-style Workforce controls improve
Hermes as a product. It is not a production implementation and does not claim
to fix NousResearch/hermes-agent#375.

The research deliberately separates:

1. protocol-faithful CAMEL RolePlaying;
2. mechanism attribution through ablation;
3. Eigent-style operational resilience; and
4. a later Hermes product-integration decision.

No model observation is scored until the corresponding protocol, cohorts,
graders, models, stopping rules, and file hashes are frozen in a receipt.

## Read the package

- `SOURCE_AUDIT.md`: source fidelity and existing ownership
- `RESEARCH_FRAME.md`: hypotheses, cohorts, gates, and decision thresholds
- `PILOT_FREEZE*.md` and `*_FREEZE.md`: immutable execution decisions
- `RESULTS.md`: observations, failure mechanisms, statistics, and limitations
- `WORKFORCE_EVIDENCE.md`: actual Hermes/Eigent source-suite comparison
- `PRODUCT_DECISION.md`: product adjudication and reopening criteria
- `REPRODUCIBILITY.md`: commands and local evidence hashes

The raw `results/` directory is intentionally ignored. Nothing in this branch
is production code, and no result should be presented as a CAMEL-paper
replication or as a fix for issue #375.
