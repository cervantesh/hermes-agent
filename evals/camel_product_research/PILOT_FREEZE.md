# Pilot freeze receipt

Frozen before the first scored model observation.

## Source identities

- Hermes: `64cc87e6681a3db4e158ed8b999ff77ba0b9d28a`
- CAMEL checkout: `e88b5eebe9f8bb5597196384c818fb4e3c63b25c`
- CAMEL paper-era content source: `c402032a7f7cd27e196356fbcf413c521a8cb4ca`
- Eigent: `92f17b596ce2ae27977d6db2f0ed11a81560115f`
- Paper: arXiv `2303.17760`

## Frozen file hashes

```text
23d53e166cd322e33ca096a3caeab911903902a24cb7f7fc1f48e1b7b406496b  .lider/camel-product-research-ledger.json
a253ee312c105811168395b47d8fc5404ad91759dd5a0d34f169e4027eff5737  evals/camel_product_research/RESEARCH_FRAME.md
162c8e39ba435cb288388629e9add24187aab114c1740611e5dff51cabc099c5  evals/camel_product_research/SOURCE_AUDIT.md
512eb871ce9bfe932af78b725e31401cd631f4787a31d7b9ed86d0596e77e667  evals/camel_product_research/camel_protocol.py
2c26bda7b90db3e71febfa3e60a946ed427b19d053a67c78d33e15e03f0dbc38  evals/camel_product_research/tasks.py
8bf635f9ae77b837efcc56795d529e3bf504737d5dbd2ea07f585006942d589e  evals/camel_product_research/worker.py
30a62ce71359a3a610898b5be82554666f68f697c7d625f536b2378d50e08d5b  evals/camel_product_research/runner.py
```

Test files are not scored artifacts. Any change to a frozen file after an
observation requires a new receipt and a new result label; old observations
must not be silently pooled with the revised protocol.

## Pilot execution order

1. One current-Hermes baseline repetition for all seven executable tasks on
   `gemini-2.5-flash`.
2. Stop each ceiling cohort before a CAMEL call.
3. Run full CAMEL only for tasks whose baseline external oracle failed.
4. Open attribution ablations only if the full CAMEL arm changes a failed
   baseline into externally verified success without a false-success increase.
5. Use Claude Sonnet 4.6 only for a new-task cross-family confirmation after a
   favorable pilot signal.

Provider/transport failures are invalid observations and are recorded
separately. Results are written to the ignored `results/` directory.
