# V3 target refresh

Refresh date: 2026-09-02 UTC  
Source: authenticated GitHub connector, `compare_commits`  
Repository: `NousResearch/hermes-agent`

The connector reported 22 commits between V2's publication-time target
`57d305d57f04ffb58fb8adef3657b166fa6e34a6` and `main`. A second comparison
used `c5c9aa8d44e03f4e8b5fe7f230cfd97ab2dde0bf` as the base and `main` as the
head and returned:

```text
status=identical
ahead_by=0
behind_by=0
total_commits=0
```

Therefore V3 pins `c5c9aa8d44e03f4e8b5fe7f230cfd97ab2dde0bf` as the exact current-main
target for the pre-observation frame. The local target worktree is detached,
clean, and at that SHA.

The target is immutable after sealing. Later movement of `main` will be
reported separately and will not be pooled into this experiment.
