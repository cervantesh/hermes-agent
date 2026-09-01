---
sidebar_position: 12
title: Restricted runtime
---

# Restricted runtime

Hermes can enter a deliberately reduced, text-only application mode that
talks directly to a separately deployed restricted conversation runtime over
a Unix-domain socket. This mode does not construct the normal agent and does
not load providers, tools, plugins, MCP, memory, skills, attachments, vision,
OCR, compression, fallbacks, auxiliaries, or subagents.

This is an application boundary, not a compliance claim. Hermes always reports:

```text
deployment_conformant=false
model_attested=false
phi_authorized=false
```

The operator remains responsible for the host, container composition, egress,
secrets, model, policy bundle, terminal capture, output redirection, and every
other deployment control.

## Supported environment

The first version supports Linux, WSL2, and Linux containers. The fixed socket
is `/run/restricted-inference/conversation.sock`. Native Windows is rejected;
Hermes does not add a TCP bridge as a fallback.

The runtime socket must be mounted with the deployment's existing group
contract. Hermes authenticates the pathname and the peer on every connection:
socket UID `10006`, GID `20001`, mode `0660`, plus matching `SO_PEERCRED`.

## Enable

First stop all existing Hermes processes yourself. `enable` cannot inspect or
stop them and does not retroactively restrict a process that is already alive.

```bash
hermes restricted enable \
  --policy-epoch '<policy epoch>' \
  --policy-digest '<lowercase sha256>' \
  --confirm-stopped
```

`--confirm-stopped` is an operator declaration, not a software verification.
Enable runs a read-only doctor check, creates the installation-wide authority,
then atomically updates the root `config.yaml`. All profiles under the same
Hermes installation share that authority.

## Run

Start the reduced REPL from a terminal:

```bash
hermes
```

Only `/new`, `/status`, and `/exit` are available. `/new` creates a completely
new runtime conversation. If an earlier turn has an ambiguous outcome, use
`/new --confirm-abandon-pending` only after making the operational decision to
abandon that pending request.

One-shot input is accepted only from non-interactive standard input:

```bash
printf '%s' 'synthetic text' | hermes restricted run --stdin
```

The response is the only stdout payload. Shell redirection, terminal
scrollback, and capture are operator-controlled boundaries. A prompt in argv,
a file path, URL source, attachment, or implicit piped input to bare `hermes`
is rejected. URLs inside the text are opaque text and are never fetched.

## Inspect and disable

```bash
hermes restricted status
hermes restricted doctor
hermes restricted disable
```

`status` separates configured/armed state from an active restricted process.
`doctor` is read-only: it does not download, start, kill, or modify the runtime.
Disable refuses while a request has an ambiguous pending outcome. It removes
the complete reserved block from the root config first and then removes the
authority. A runner that was already alive remains restricted until it exits.

If a disable was interrupted after the config write, the authority and absent
reserved block intentionally form an administrative fail-stop. Only `status`,
`doctor`, and another idempotent `disable` are admitted; no conversation is
served.

## Persisted state

Installation-wide state lives under `<Hermes root>/restricted-runtime/` with
private owner-only permissions. Hermes stores identifiers, the exact policy
binding, and an HMAC of a pending message. It never stores the message,
response, title, transcript, destination, or model metadata in this state and
does not use `SessionDB`.

Timeouts, partial or invalid responses, process death, and intermediate runtime
states preserve the pending request. Submitting the exact same UTF-8 text
reuses its request ID after constant-time HMAC comparison; different text is
blocked until the pending request is resolved or explicitly abandoned with a
new conversation.

## What remains unavailable

While the global authority is armed, alternate Hermes entrypoints fail closed:
gateway and messaging platforms, TUI/desktop/dashboard/serve, cron, ACP, the
normal agent runner, batch and API/MCP servers. `--safe-mode`, provider/model
arguments, toolset options, and direct Python entrypoints cannot bypass the
authority.
