"""Run one task through the real synchronous delegate_task lifecycle."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import tempfile
import time
from pathlib import Path

EVAL_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(EVAL_DIR))

from fixtures import build_workspace  # noqa: E402
from tasks import TASKS_BY_ID  # noqa: E402


def _load_suite(suite: str, task_id: str):
    """Resolve a task, its fixture builder, and the suite's iteration budget."""
    if suite == "long":
        from long_horizon import LONG_TASKS_BY_ID, build_long_workspace

        task = LONG_TASKS_BY_ID[task_id]
        return task, lambda root: build_long_workspace(root, task_id), 50
    task = TASKS_BY_ID[task_id]
    return task, build_workspace, 12


def _enable_disposable_codex_workspace_write(workspace: Path) -> None:
    """Scope the eval-only Codex sandbox to the disposable workspace.

    Production Hermes intentionally follows the user's Codex permission
    profile.  The evaluator needs a symmetric, non-interactive write arm, so
    it overrides the app-server client only inside this worker process.  The
    sandbox stays enabled, gains no writable root beyond ``workspace``, and
    has network access disabled.
    """
    from agent.transports.codex_app_server import CodexAppServerClient
    import agent.transports.codex_app_server_session as session_module

    original_session = session_module.CodexAppServerSession
    workspace_toml = json.dumps(str(workspace))

    def eval_session(*args, **kwargs):
        def client_factory(*, codex_bin: str, codex_home: str | None):
            return CodexAppServerClient(
                codex_bin=codex_bin,
                codex_home=codex_home,
                extra_args=[
                    "-c",
                    'sandbox_mode="workspace-write"',
                    "-c",
                    f"sandbox_workspace_write.writable_roots=[{workspace_toml}]",
                    "-c",
                    "sandbox_workspace_write.network_access=false",
                ],
            )

        kwargs["client_factory"] = client_factory
        return original_session(*args, **kwargs)

    session_module.CodexAppServerSession = eval_session


def _provider_key(provider: str) -> str:
    aliases = {
        "gemini": "GEMINI_API_KEY",
        "google": "GOOGLE_API_KEY",
        "openrouter": "OPENROUTER_API_KEY",
        "anthropic": "ANTHROPIC_API_KEY",
        "openai": "OPENAI_API_KEY",
    }
    preferred = aliases.get(provider, "")
    if preferred and os.environ.get(preferred):
        return preferred
    if provider == "gemini" and os.environ.get("GOOGLE_API_KEY"):
        return "GOOGLE_API_KEY"
    if provider == "google" and os.environ.get("GEMINI_API_KEY"):
        return "GEMINI_API_KEY"
    return preferred


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--suite", choices=("short", "long"), default="short")
    parser.add_argument("--task", required=True)
    parser.add_argument("--provider", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--codex-workspace-write", action="store_true")
    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve()
    sys.path.insert(0, str(repo_root))
    try:
        task, workspace_builder, iteration_budget = _load_suite(args.suite, args.task)
    except KeyError:
        raise SystemExit(f"unknown {args.suite} task: {args.task}") from None
    wanted_key = _provider_key(args.provider)
    if wanted_key and not os.environ.get(wanted_key):
        raise SystemExit(f"missing required credential: {wanted_key}")
    workspace = Path(tempfile.mkdtemp(prefix=f"delegate-inception-{task.task_id}-"))
    home_root = Path(tempfile.mkdtemp(prefix="delegate-inception-home-"))
    hermes_home = home_root / ".hermes"
    hermes_home.mkdir()
    workspace_builder(workspace)
    (hermes_home / "config.yaml").write_text(
        "delegation:\n"
        f"  max_iterations: {iteration_budget}\n"
        "  max_spawn_depth: 2\n"
        "  orchestrator_enabled: false\n",
        encoding="utf-8",
    )

    old_env = dict(os.environ)
    os.environ["HERMES_HOME"] = str(hermes_home)
    os.environ["TERMINAL_CWD"] = str(workspace)
    for name in list(os.environ):
        if name.endswith("_API_KEY") and name not in {
            wanted_key,
            "GEMINI_API_KEY" if args.provider == "google" else wanted_key,
            "GOOGLE_API_KEY" if args.provider == "gemini" else wanted_key,
        }:
            os.environ.pop(name, None)

    started = time.monotonic()
    try:
        if args.codex_workspace_write:
            if args.provider != "codex-app-server":
                raise SystemExit(
                    "--codex-workspace-write requires --provider codex-app-server"
                )
            os.environ["HERMES_YOLO_MODE"] = "1"
            _enable_disposable_codex_workspace_write(workspace)

        from run_agent import AIAgent
        from tools.delegate_tool import delegate_task

        api_key = os.environ.get(wanted_key) if wanted_key else None
        runtime_kwargs = {
            "provider": args.provider,
            "api_key": api_key,
        }
        if args.provider == "claude-code":
            runtime_kwargs.update(
                provider="anthropic",
                api_key=None,
                api_mode="anthropic_messages",
            )
        if args.provider == "codex-app-server":
            runtime_kwargs.update(
                provider="openai",
                api_key="codex-app-server",
                base_url="https://codex-app-server.invalid",
                api_mode="codex_app_server",
            )
        parent = AIAgent(
            model=args.model,
            quiet_mode=True,
            skip_context_files=True,
            skip_memory=True,
            enabled_toolsets=["file", "terminal", "search"],
            max_iterations=2,
            platform="cli",
            **runtime_kwargs,
        )
        payload = json.loads(
            delegate_task(
                goal=task.prompt,
                background=False,
                parent_agent=parent,
            )
        )
        entry = (payload.get("results") or [{}])[0]
        summary = str(entry.get("summary") or "")
        provider_failure = next(
            (
                marker
                for marker in (
                    "RESOURCE_EXHAUSTED",
                    "API call failed after",
                    "authentication failed",
                    "connection error",
                )
                if marker.lower() in summary.lower()
            ),
            None,
        )
        if provider_failure:
            raise SystemExit(
                f"provider failure (not an eval result): {provider_failure}"
            )
        transcript_path = entry.get("live_transcript")
        if transcript_path and Path(transcript_path).is_file():
            entry["_eval_transcript"] = Path(transcript_path).read_text(
                encoding="utf-8", errors="replace"
            )
        checks = task.grade(summary, entry, workspace)
        output = {
            "task": task.task_id,
            "suite": args.suite,
            "category": task.category,
            "note": task.note,
            "ok": bool(checks) and all(checks.values()),
            "checks": checks,
            "summary": summary,
            "status": entry.get("status"),
            "exit_reason": entry.get("exit_reason"),
            "api_calls": entry.get("api_calls", 0),
            "tool_trace": entry.get("tool_trace") or [],
            "live_transcript": entry.get("_eval_transcript") or "",
            "tokens": entry.get("tokens") or {},
            "duration_seconds": round(time.monotonic() - started, 2),
            "error": entry.get("error"),
        }
        print(json.dumps(output, ensure_ascii=False))
        return 0
    finally:
        os.environ.clear()
        os.environ.update(old_env)
        shutil.rmtree(workspace, ignore_errors=True)
        shutil.rmtree(home_root, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
