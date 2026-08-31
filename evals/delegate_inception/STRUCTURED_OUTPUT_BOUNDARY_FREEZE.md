# Structured-output boundary freeze receipt

- Freeze input commit: `4858f657d28833c4afbfafd3e0a94e3496f84f2f`
- Hermes tree under test: `main@ed3562bbbcd8a5323be96b81812291faae99e010`
- Scoring status at freeze: no model observations collected
- Harness gate: `30 passed in 66.94s`
- Ruff gate: all changed Python files passed
- Relevant Hermes paths compared with the earlier smoke base: unchanged

## SHA-256 content pins

```text
128a721532463e6a35bec0bc9d2adf277f21f237fd95e960f01ec14359ee8a87  STRUCTURED_OUTPUT_BOUNDARY_PROTOCOL.md
7bf51f45321b6acdb962c9ea387ad98d7c066f62410590eb628f77770a406b33  structured_output_boundary.py
7606b16982e993ffb8b8cc0c96cab1029dfb2e01f1889a9fe98eb1614d3d4ffd  test_structured_output_boundary.py
26eed20f345b1bcdfac6fe6dabea01b92f1289ab9f360e85136e6e1e104bc99e  worker.py
cb298909aabecce940c62f2c9150ed593d491342ed0aa24aa8e497702092f628  runner.py
9d642353bdd96835ccf25209c1e2f557bdebb3e9980a81ea2a4813da017cc5f2  anti_bypass_holdout.py
```

Any edit to a pinned file after this receipt invalidates the freeze and
requires a new receipt before scoring.
