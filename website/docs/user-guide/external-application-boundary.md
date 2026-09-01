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
streams. On Windows, configure an executable directly (or an interpreter plus
script); `.cmd` and `.bat` handlers are rejected.

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
passed admission. Marker tamper resistance against the same OS account and
application-specific policy or sandboxing are outside this experiment.
