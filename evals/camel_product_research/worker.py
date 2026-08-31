"""Execute one frozen research task through a real Hermes runtime."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import time
from typing import Any

EVAL_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(EVAL_DIR))

from camel_protocol import TurnResult, load_paper_prompts, run_role_playing  # noqa: E402
from tasks import TASKS_BY_ID  # noqa: E402


_PROVIDER_FAILURE_MARKERS = (
    "resource_exhausted",
    "api call failed after",
    "authentication failed",
    "connection error",
    "rate limit",
    "quota exceeded",
)


def _tool_trace(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    trace: list[dict[str, Any]] = []
    for message in messages:
        if message.get("role") != "assistant":
            continue
        for call in message.get("tool_calls") or []:
            function = call.get("function") or {}
            trace.append(
                {
                    "name": function.get("name") or call.get("name") or "unknown",
                    "id": call.get("id") or "",
                }
            )
    return trace


def _tokens(result: dict[str, Any]) -> dict[str, int]:
    raw = result.get("tokens") or result.get("token_usage") or {}
    return {str(key): value for key, value in raw.items() if isinstance(value, int)}


def _provider_failure(entry: dict[str, Any]) -> str | None:
    material = "\n".join(
        str(entry.get(key) or "") for key in ("summary", "error", "exit_reason")
    ).lower()
    return next((marker for marker in _PROVIDER_FAILURE_MARKERS if marker in material), None)


def _provider_key(provider: str) -> str:
    return {
        "gemini": "GEMINI_API_KEY",
        "google": "GOOGLE_API_KEY",
        "openai": "OPENAI_API_KEY",
        "anthropic": "ANTHROPIC_API_KEY",
        "openrouter": "OPENROUTER_API_KEY",
    }.get(provider, "")


def _agent_kwargs(provider: str, model: str) -> dict[str, Any]:
    if provider == "claude-code":
        return {
            "provider": "anthropic",
            "model": model,
            "api_key": None,
            "api_mode": "anthropic_messages",
        }
    key_name = _provider_key(provider)
    api_key = os.environ.get(key_name) if key_name else None
    if key_name and not api_key:
        raise SystemExit(f"missing required credential: {key_name}")
    return {"provider": provider, "model": model, "api_key": api_key}


def _make_agent(*, provider: str, model: str, tools: bool, max_iterations: int):
    from run_agent import AIAgent

    return AIAgent(
        quiet_mode=True,
        skip_context_files=True,
        skip_memory=True,
        enabled_toolsets=["file", "terminal", "search"] if tools else [],
        max_iterations=max_iterations,
        platform="cli",
        **_agent_kwargs(provider, model),
    )


def _run_baseline(task, provider: str, model: str) -> dict[str, Any]:
    from tools.delegate_tool import delegate_task

    parent = _make_agent(provider=provider, model=model, tools=True, max_iterations=2)
    try:
        payload = json.loads(
            delegate_task(
                tasks=[{"goal": task.prompt}],
                background=False,
                parent_agent=parent,
            )
        )
    finally:
        parent.close()
    entry = (payload.get("results") or [{}])[0]
    return {
        "summary": str(entry.get("summary") or ""),
        "status": entry.get("status"),
        "exit_reason": entry.get("exit_reason"),
        "api_calls": entry.get("api_calls", 0),
        "tokens": entry.get("tokens") or {},
        "tool_trace": entry.get("tool_trace") or [],
        "error": entry.get("error"),
        "protocol": None,
    }


def _run_camel(task, provider: str, model: str, camel_repo: Path) -> dict[str, Any]:
    agents: dict[str, Any] = {}

    def turn(role: str, system: str, message: str, history: list[dict]) -> TurnResult:
        if role not in agents:
            agents[role] = _make_agent(
                provider=provider,
                model=model,
                tools=role == "ai_assistant",
                max_iterations=12 if role == "ai_assistant" else 2,
            )
        result = agents[role].run_conversation(
            message,
            system_message=system,
            conversation_history=list(history),
        )
        messages = list(result.get("messages") or [])
        return TurnResult(
            text=str(result.get("final_response") or ""),
            history=messages,
            api_calls=int(result.get("api_calls") or 0),
            tokens=_tokens(result),
            tool_trace=_tool_trace(messages),
        )

    try:
        run = run_role_playing(
            original_task=task.prompt,
            assistant_role=task.assistant_role,
            user_role=task.user_role,
            bundle=load_paper_prompts(camel_repo),
            turn=turn,
        )
    finally:
        for agent in agents.values():
            agent.close()
    return {
        "summary": run.final_assistant_text,
        "status": "completed" if run.termination == "task_done" else "message_limit",
        "exit_reason": run.termination,
        "api_calls": run.api_calls,
        "tokens": run.tokens,
        "tool_trace": run.tool_trace,
        "error": None,
        "protocol": {
            "specified_task": run.specified_task,
            "termination": run.termination,
            "message_count": len(run.messages),
            "prompt_hashes": run.prompt_hashes,
            "messages": [
                {
                    "sequence": item.sequence,
                    "speaker": item.speaker,
                    "content": item.content,
                }
                for item in run.messages
            ],
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--camel-root", required=True)
    parser.add_argument("--task", required=True)
    parser.add_argument("--strategy", choices=("baseline", "camel"), required=True)
    parser.add_argument("--provider", required=True)
    parser.add_argument("--model", required=True)
    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve()
    sys.path.insert(0, str(repo_root))
    try:
        task = TASKS_BY_ID[args.task]
    except KeyError:
        raise SystemExit(f"unknown task: {args.task}") from None

    workspace = Path(tempfile.mkdtemp(prefix=f"camel-product-{task.task_id}-"))
    home_root = Path(tempfile.mkdtemp(prefix="camel-product-home-"))
    hermes_home = home_root / ".hermes"
    hermes_home.mkdir()
    task.build(workspace)
    (hermes_home / "config.yaml").write_text(
        "delegation:\n"
        "  max_iterations: 40\n"
        "  max_spawn_depth: 2\n"
        "  orchestrator_enabled: false\n",
        encoding="utf-8",
    )
    old_env = dict(os.environ)
    os.environ["HERMES_HOME"] = str(hermes_home)
    os.environ["TERMINAL_CWD"] = str(workspace)
    started = time.monotonic()
    try:
        if args.strategy == "baseline":
            entry = _run_baseline(task, args.provider, args.model)
        else:
            entry = _run_camel(
                task, args.provider, args.model, Path(args.camel_root).resolve()
            )
        provider_failure = _provider_failure(entry)
        if provider_failure:
            raise SystemExit(
                f"provider failure (invalid observation): {provider_failure}"
            )
        summary = entry["summary"]
        checks = task.grade(summary, entry, workspace)
        ok = bool(checks) and all(checks.values())
        false_success = bool(
            not ok
            and (
                entry.get("status") == "completed"
                or "complete" in summary.lower()
                or "success" in summary.lower()
            )
        )
        output = {
            "task": task.task_id,
            "cohort": task.cohort,
            "strategy": args.strategy,
            "ok": ok,
            "false_success": false_success,
            "checks": checks,
            **entry,
            "duration_seconds": round(time.monotonic() - started, 2),
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
