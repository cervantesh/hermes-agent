"""Extract frozen prompts from the pinned CAMEL repository and paper TeX."""

from __future__ import annotations

import hashlib
import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from .protocol import RolePrompts


@dataclass(frozen=True)
class PromptSources:
    original_assistant: str
    original_user: str
    task_specifier: str
    ablated_assistant: str
    ablated_user: str
    solution_extraction: str
    evaluation_system: str
    evaluation_template: str
    evaluation_instruction: str
    sha256: dict[str, str] = field(init=False)

    def __post_init__(self) -> None:
        digests = {
            name: hashlib.sha256(getattr(self, name).encode("utf-8")).hexdigest()
            for name in (
                "original_assistant",
                "original_user",
                "task_specifier",
                "ablated_assistant",
                "ablated_user",
                "solution_extraction",
                "evaluation_system",
                "evaluation_template",
                "evaluation_instruction",
            )
        }
        object.__setattr__(self, "sha256", digests)


def _git_show(repo: Path, revision: str, path: str) -> str:
    result = subprocess.run(
        ["git", "show", f"{revision}:{path}"],
        cwd=repo,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    if result.returncode:
        raise ValueError(f"unable to read {revision}:{path}: {result.stderr.strip()}")
    return result.stdout


def _box(tex: str, title: str) -> str:
    pattern = re.compile(
        rf"\\begin\{{AIBox\}}\{{{re.escape(title)}\}}(.*?)\\end\{{AIBox\}}",
        re.DOTALL,
    )
    match = pattern.search(tex)
    if not match:
        raise ValueError(f"missing TeX box: {title}")
    return match.group(1)


def _plain_lines(fragment: str, *, skip_headings: bool = False) -> str:
    output: list[str] = []
    for raw_line in fragment.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if skip_headings and line.startswith(r"\textbf"):
            continue
        line = line.replace(r"\_", "_")
        line = line.replace(r"\\", "\n")
        output.extend(part.strip() for part in line.splitlines() if part.strip())
    return "\n".join(output)


def _evaluation_parts(fragment: str) -> tuple[str, str, str]:
    lines = [line.strip() for line in fragment.splitlines() if line.strip()]
    system_index = next(
        index for index, line in enumerate(lines) if "System Prompt:" in line
    )
    template_index = next(
        index for index, line in enumerate(lines) if "Prompt Template:" in line
    )
    instruction_index = next(
        index
        for index, line in enumerate(lines[template_index + 1 :], template_index + 1)
        if "Prompt:" in line and "Prompt Template:" not in line
    )
    system_candidates = [
        line
        for line in lines[system_index + 1 : template_index]
        if not line.startswith("\\")
    ]
    if len(system_candidates) != 1:
        raise ValueError("evaluation system prompt could not be isolated")
    template = _plain_lines(
        "\n".join(lines[template_index + 1 : instruction_index]),
        skip_headings=True,
    )
    instruction = _plain_lines("\n".join(lines[instruction_index + 1 :]))
    return system_candidates[0], template, instruction


def load_prompt_sources(
    camel_repo: str | Path,
    camel_revision: str,
    supplement_tex: str | Path,
) -> PromptSources:
    repo = Path(camel_repo)
    tex = Path(supplement_tex).read_text(encoding="utf-8")

    ablation = _box(tex, "AI Society Ablation Inception Prompt")
    alltt = re.findall(r"\\begin\{alltt\}(.*?)\\end\{alltt\}", ablation, re.DOTALL)
    if len(alltt) != 2:
        raise ValueError("ablation box must contain exactly two alltt prompts")

    evaluation_system, evaluation_template, evaluation_instruction = _evaluation_parts(
        _box(tex, "Evaluation Prompt")
    )
    return PromptSources(
        original_assistant=_git_show(
            repo, camel_revision, "prompts/ai_society/assistant_prompt_with_task.txt"
        ),
        original_user=_git_show(
            repo, camel_revision, "prompts/ai_society/user_prompt_with_task.txt"
        ),
        task_specifier=_git_show(
            repo, camel_revision, "prompts/ai_society/task_specify_prompt.txt"
        ),
        ablated_assistant=_plain_lines(alltt[0]),
        ablated_user=_plain_lines(alltt[1]),
        solution_extraction=_plain_lines(_box(tex, "Solution Extraction Prompt")),
        evaluation_system=evaluation_system,
        evaluation_template=evaluation_template,
        evaluation_instruction=evaluation_instruction,
    )


def _render(template: str, replacements: dict[str, str]) -> str:
    pattern = re.compile("|".join(re.escape(key) for key in replacements))
    rendered = pattern.sub(lambda match: replacements[match.group(0)], template)
    unresolved = re.findall(r"<(?:ASSISTANT_ROLE|USER_ROLE|TASK)>", rendered)
    if unresolved:
        raise ValueError(f"unresolved role prompt placeholders: {unresolved}")
    return rendered


def render_role_prompts(
    sources: PromptSources,
    arm: str,
    assistant_role: str,
    user_role: str,
    specified_task: str,
) -> RolePrompts:
    if arm not in {"original", "ablated"}:
        raise ValueError("arm must be original or ablated")
    replacements = {
        "<ASSISTANT_ROLE>": assistant_role,
        "<USER_ROLE>": user_role,
        "<TASK>": specified_task,
    }
    return RolePrompts(
        assistant=_render(getattr(sources, f"{arm}_assistant"), replacements),
        user=_render(getattr(sources, f"{arm}_user"), replacements),
    )


def render_evaluation_prompt(
    sources: PromptSources,
    question: str,
    answer_1: str,
    answer_2: str,
) -> str:
    replacements = {
        "{question}": question,
        "{answer_1}": answer_1,
        "{answer_2}": answer_2,
        "{prompt}": sources.evaluation_instruction,
    }
    pattern = re.compile("|".join(re.escape(key) for key in replacements))
    rendered = pattern.sub(
        lambda match: replacements[match.group(0)], sources.evaluation_template
    )
    unresolved = [key for key in replacements if key in rendered]
    if unresolved:
        raise ValueError(f"unresolved evaluation placeholders: {unresolved}")
    return rendered
