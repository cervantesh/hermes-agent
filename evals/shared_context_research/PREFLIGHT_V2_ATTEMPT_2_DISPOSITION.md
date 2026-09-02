# V2 preflight attempt 2 disposition

Status: **INVALID — not scored and private only**

After fixing the sentinel parser and stating the workspace restriction
explicitly, a second unscored preflight was run against target
`180291162ff4df0d42b5dc4fecd08005cf7cebf9`.

The sentinel and shared-storage topology passed their integrity checks. In the
detached `compact_release_map` fixture, however, arm B searched its isolated arm
root after searching its assigned workspace. That is a genuine scope-expansion
event under the frozen protocol. It was not added to the allow-list, and the
preflight command correctly exited nonzero without producing a public packet.

V1 and V2 treat scope expansion as an adverse measured outcome that prevents a
favorable product adjudication; it must not be erased or reclassified as valid.
The scored pilot therefore retains `compact_release_map` unchanged. To finish
the mechanical preflight of the detached topology, the next unscored attempt
uses the already predeclared `ordered_dependency_plan` fixture instead. No
preflight observation is pooled with the pilot, and every run uses fresh homes,
databases, sessions, workspaces, and model context.
