---
title: External application boundary (experimental)
sidebar_label: External application boundary
---

This fork experiment lets an installation delegate every supported Hermes
launcher to one operator-configured external application before Hermes loads
providers, tools, plugins, memory, or gateway state. It is opt-in: without the
durable marker, launch behavior is unchanged and this configuration is not
read.

Configure an argv list in the installation root's `config.yaml`:

```yaml
application:
  external:
    command:
      - /absolute/path/to/interpreter
      - /absolute/path/to/application.py
```

Then run `hermes application enable`. The command validates the executable and
atomically writes `state/application-boundary.json`. Once armed, covered
launchers delegate with their original arguments and inherited standard
streams. On Windows, configure a directly executable image (or an executable
interpreter plus a script argument). Scripts and documents such as `.py`,
`.ps1`, `.cmd`, `.bat`, and `.txt` are rejected as direct handlers.

The marker is installation-wide. Profiles under the same installation cannot
bypass it. A distinct custom `HERMES_HOME` is a distinct installation.

While armed, these lightweight recovery commands remain local:

- `hermes application status`
- `hermes application enable`
- `hermes application disable`
- `hermes --version`

An unreadable marker, configuration drift, executable drift, or recursive
delegation fails closed. Quiesce launchers before enabling, disabling, or
changing the command: the boundary does not stop processes that have already
passed admission. If marker publication or removal succeeds but syncing its
directory fails with a real I/O error, the management command returns failure
and reports whether the authoritative state is armed or unarmed; durability of
that transition is not claimed. Marker tamper resistance against the same OS
account and application-specific policy or sandboxing are outside this
experiment.
