# V5 research frame: discriminate bounded relay from declared reads

Status: **pre-observation**.

V4 did not demonstrate an incremental product outcome because its dependent
payloads remained available through Hermes's existing transports. V5 does not
repeat that matrix. It targets one independently reachable difference on
current main: `build_worker_context()` truncates each completed parent summary
at 4,096 characters, while the simulated C declared-read transport returns the
committed value without that projection cap.

The product question is narrow: when an opaque, decision-required record lies
beyond the real Kanban projection cap, does current B fail an executable result
oracle while the same model and fixture succeed through C? This is not a claim
that arbitrary unbounded shared state should ship, nor a faithful replication
of the CAMEL paper.
