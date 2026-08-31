# CAMEL and Eigent product research

This directory contains a local-first, preregistered research program for
deciding whether CAMEL RolePlaying or Eigent-style Workforce controls improve
Hermes as a product. It is not a production implementation and does not claim
to fix NousResearch/hermes-agent#375.

The research deliberately separates:

1. a CAMEL-template-derived Hermes RolePlaying adaptation;
2. mechanism attribution through ablation;
3. Eigent-style operational resilience; and
4. a later Hermes product-integration decision.

Each scored observation followed a committed freeze for its protocol, cohort,
graders, model, stopping rule, and source-template hashes. A later adversarial
review found that the adapter omitted one hidden historical assistant-priming
call and did not hash Hermes's effective composed system prompts. The results
therefore characterize the evaluated adaptation, not historically exact or
component-isolated CAMEL.

## Read the package

- `SOURCE_AUDIT.md`: source fidelity and existing ownership
- `RESEARCH_FRAME.md`: hypotheses, cohorts, gates, and decision thresholds
- `PILOT_FREEZE*.md` and `*_FREEZE.md`: immutable execution decisions
- `RESULTS.md`: observations, failure mechanisms, statistics, and limitations
- `WORKFORCE_EVIDENCE.md`: actual Hermes/Eigent source-suite comparison
- `PRODUCT_DECISION.md`: product adjudication and reopening criteria
- `REPRODUCIBILITY.md`: commands and local evidence hashes

The raw `results/` directory remains intentionally ignored because it contains
local paths and full model transcripts. Privacy-safe row-level receipts are
committed under `evidence/`; they retain external-oracle checks and run
identity so the published aggregates can be recomputed. Nothing in this branch
is production code, and no result should be presented as a CAMEL-paper
replication or as a fix for issue #375.
