import subprocess

from evals.issue_375_fidelity_research.sources import (
    PromptSources,
    load_prompt_sources,
    render_evaluation_prompt,
    render_role_prompts,
)


def test_prompt_sources_are_extracted_from_pinned_git_and_tex(monkeypatch, tmp_path):
    git_files = {
        "prompts/ai_society/assistant_prompt_with_task.txt": (
            "Assistant <ASSISTANT_ROLE> / <USER_ROLE> / <TASK>"
        ),
        "prompts/ai_society/user_prompt_with_task.txt": (
            "User <USER_ROLE> / <ASSISTANT_ROLE> / <TASK>"
        ),
        "prompts/ai_society/task_specify_prompt.txt": (
            "Specify <ASSISTANT_ROLE> / <USER_ROLE> / <TASK> / <WORD_LIMIT>"
        ),
    }

    def fake_run(args, **kwargs):
        path = args[-1].split(":", 1)[1]
        return subprocess.CompletedProcess(args, 0, stdout=git_files[path], stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)
    tex = tmp_path / "supplement.tex"
    tex.write_text(
        r"""
\begin{AIBox}{Solution Extraction Prompt}
    Extract the full solution.
    Do not summarize it.
\end{AIBox}
\begin{AIBox}{Evaluation Prompt}
    \textbf{\underline{System Prompt:}}
    Judge precisely.
    \textbf{\underline{Prompt Template:}}
    [Question]\\
    {question}\\
    [The Start of Assistant 1's Answer]\\
    {answer\_1}\\
    [The End of Assistant 1's Answer]\\
    [The Start of Assistant 2's Answer]\\
    {answer\_2}\\
    [The End of Assistant 2's Answer]\\
    [System]\\
    {prompt}\\
    \textbf{\underline{Prompt:}}
    Return two scores first.
\end{AIBox}
\begin{AIBox}{AI Society Ablation Inception Prompt}
\parbox{A}{{\bf Assistant System Prompt} \scriptsize \begin{alltt}
    Ablated assistant <ASSISTANT\_ROLE> <USER\_ROLE> <TASK>.
\end{alltt}}
\parbox{B}{{\bf User System Prompt:} \scriptsize \begin{alltt}
    Ablated user <USER\_ROLE> <ASSISTANT\_ROLE> <TASK> <CAMEL\_TASK\_DONE>.
\end{alltt}}
\end{AIBox}
""",
        encoding="utf-8",
    )

    sources = load_prompt_sources(tmp_path, "pinned-revision", tex)

    assert sources.original_assistant.startswith("Assistant")
    assert sources.original_user.startswith("User")
    assert sources.task_specifier.startswith("Specify")
    assert sources.ablated_assistant == (
        "Ablated assistant <ASSISTANT_ROLE> <USER_ROLE> <TASK>."
    )
    assert sources.ablated_user.endswith("<CAMEL_TASK_DONE>.")
    assert (
        sources.solution_extraction
        == "Extract the full solution.\nDo not summarize it."
    )
    assert sources.evaluation_system == "Judge precisely."
    assert "{answer_1}" in sources.evaluation_template
    assert sources.evaluation_template.endswith("{prompt}")
    assert sources.evaluation_instruction == "Return two scores first."
    assert set(sources.sha256) == {
        "original_assistant",
        "original_user",
        "task_specifier",
        "ablated_assistant",
        "ablated_user",
        "solution_extraction",
        "evaluation_system",
        "evaluation_template",
        "evaluation_instruction",
    }


def test_source_loader_fails_when_required_tex_box_is_missing(monkeypatch, tmp_path):
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *args, **kwargs: subprocess.CompletedProcess(
            args, 0, stdout="prompt", stderr=""
        ),
    )
    tex = tmp_path / "supplement.tex"
    tex.write_text("no prompt boxes", encoding="utf-8")

    try:
        load_prompt_sources(tmp_path, "pinned-revision", tex)
    except ValueError as exc:
        assert "missing TeX box" in str(exc)
    else:
        raise AssertionError("missing source box was accepted")


def test_rendering_changes_only_declared_placeholders():
    sources = PromptSources(
        original_assistant="OA <ASSISTANT_ROLE> <USER_ROLE> <TASK>",
        original_user="OU <USER_ROLE> <ASSISTANT_ROLE> <TASK>",
        task_specifier="TS <TASK>",
        ablated_assistant="AA <ASSISTANT_ROLE> <USER_ROLE> <TASK>",
        ablated_user="AU <USER_ROLE> <ASSISTANT_ROLE> <TASK>",
        solution_extraction="extract",
        evaluation_system="judge",
        evaluation_template="Q={question}\nA1={answer_1}\nA2={answer_2}\nP={prompt}",
        evaluation_instruction="compare",
    )

    original = render_role_prompts(
        sources, "original", "Programmer", "Filmmaker", "Task"
    )
    ablated = render_role_prompts(sources, "ablated", "Programmer", "Filmmaker", "Task")
    evaluation = render_evaluation_prompt(sources, "Task", "first", "second")

    assert original.assistant == "OA Programmer Filmmaker Task"
    assert original.user == "OU Filmmaker Programmer Task"
    assert ablated.assistant == "AA Programmer Filmmaker Task"
    assert ablated.user == "AU Filmmaker Programmer Task"
    assert evaluation == "Q=Task\nA1=first\nA2=second\nP=compare"
