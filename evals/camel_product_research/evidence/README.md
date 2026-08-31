# Sanitized research evidence

These JSONL receipts are a strict projection of local raw observations. They
retain run identity, external-oracle checks, task specification, termination,
API-call counts, available token totals, and wall time. They exclude local
paths, free-form model summaries, errors, tool traces, and full role
transcripts.

Each `.meta.json` records the SHA-256 of both the private raw source and the
committed projection. Regenerate a receipt with:

```text
python evals/camel_product_research/sanitize_evidence.py --source <raw.jsonl> --output <evidence.jsonl>
```

The receipts support the descriptive tables in `RESULTS.md`. They do not make
the sequential wall-time ratios causal, reconstruct deleted workspaces, or pin
the effective Hermes-composed system prompt.
