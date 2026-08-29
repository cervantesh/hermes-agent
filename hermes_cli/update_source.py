"""Git source selection, branch, stash, fork, and fetch behavior.

Extracted mechanically from :mod:`hermes_cli.update_cmd`.  Runtime
references to the historical module surface resolve through the
compatibility facade so imports and monkeypatches remain effective.
"""

from pathlib import Path
from typing import Optional


def _stash_local_changes_if_needed(git_cmd: list[str], cwd: Path) -> Optional[str]:
    status = subprocess.run(
        git_cmd + ["status", "--porcelain"],
        cwd=cwd,
        capture_output=True,
        text=True, encoding="utf-8", errors="replace",
        check=True,
    )
    if not status.stdout.strip():
        return None

    # If the index has unmerged entries (e.g. from an interrupted merge/rebase),
    # git stash will fail with "needs merge / could not write index".  Clear the
    # conflict state with `git reset` so the stash can proceed.  Working-tree
    # changes are preserved; only the index conflict markers are dropped.
    unmerged = subprocess.run(
        git_cmd + ["ls-files", "--unmerged"],
        cwd=cwd,
        capture_output=True,
        text=True, encoding="utf-8", errors="replace",
    )
    if unmerged.stdout.strip():
        print("→ Clearing unmerged index entries from a previous conflict...")
        subprocess.run(git_cmd + ["reset"], cwd=cwd, capture_output=True)

    from datetime import datetime, timezone

    stash_name = datetime.now(timezone.utc).strftime(
        "hermes-update-autostash-%Y%m%d-%H%M%S"
    )
    print("→ Local changes detected — stashing before update...")
    prev_stash = subprocess.run(
        git_cmd + ["rev-parse", "--verify", "refs/stash"],
        cwd=cwd,
        capture_output=True,
        text=True, encoding="utf-8", errors="replace",
    ).stdout.strip()
    push = subprocess.run(
        git_cmd + ["stash", "push", "--include-untracked", "-m", stash_name],
        cwd=cwd,
        capture_output=True,
        text=True, encoding="utf-8", errors="replace",
    )
    if push.stdout.strip():
        print(push.stdout.strip())
    stash_probe = subprocess.run(
        git_cmd + ["rev-parse", "--verify", "refs/stash"],
        cwd=cwd,
        capture_output=True,
        text=True, encoding="utf-8", errors="replace",
    )
    stash_ref = stash_probe.stdout.strip()
    stash_created = (
        stash_probe.returncode == 0 and bool(stash_ref) and stash_ref != prev_stash
    )

    if push.returncode != 0:
        if stash_created:
            # git stash push exits non-zero when it saved everything but could
            # not delete some swept untracked files from the working tree
            # (e.g. a root-owned directory: "warning: failed to remove ...:
            # Permission denied").  The stash entry is complete — the changes
            # are safe — so this is not a failure.  Leave the undeletable
            # files in place and continue the update.
            if push.stderr.strip():
                print(push.stderr.strip())
            print(
                "  ⚠ Some untracked files could not be removed from the "
                "working tree (permission denied)."
            )
            print(
                "    They were still saved to the stash and were left in "
                "place — the update will continue."
            )
            # A partially-failed stash push also aborts its working-tree
            # cleanup for TRACKED modifications — they are saved in the stash
            # but still dirty the tree, which would break the checkout/pull
            # that follows. Safe to reset: everything is in the stash entry.
            subprocess.run(
                git_cmd + ["reset", "--hard", "HEAD"],
                cwd=cwd,
                capture_output=True,
            )
        else:
            # No stash entry was created: the changes were NOT saved.  This
            # is a real failure — bail out before the update touches HEAD.
            print("✗ Could not stash local changes — update aborted.")
            if push.stderr.strip():
                print(f"  {push.stderr.strip().splitlines()[0]}")
            print(
                "  Commit, stash, or clean up your local changes manually, "
                "then re-run `hermes update`."
            )
            raise subprocess.CalledProcessError(
                push.returncode, push.args, output=push.stdout, stderr=push.stderr
            )

    return stash_ref


def _resolve_stash_selector(
    git_cmd: list[str], cwd: Path, stash_ref: str
) -> Optional[str]:
    stash_list = subprocess.run(
        git_cmd + ["stash", "list", "--format=%gd %H"],
        cwd=cwd,
        capture_output=True,
        text=True, encoding="utf-8", errors="replace",
        check=True,
    )
    for line in stash_list.stdout.splitlines():
        selector, _, commit = line.partition(" ")
        if commit.strip() == stash_ref:
            return selector.strip()
    return None


def _print_stash_cleanup_guidance(
    stash_ref: str, stash_selector: Optional[str] = None
) -> None:
    print(
        "  Check `git status` first so you don't accidentally reapply the same change twice."
    )
    print("  Find the saved entry with: git stash list --format='%gd %H %s'")
    if stash_selector:
        print(f"  Remove it with: git stash drop {stash_selector}")
    else:
        print(
            f"  Look for commit {stash_ref}, then drop its selector with: git stash drop stash@{{N}}"
        )


def _stash_apply_failed_only_on_existing_untracked(stderr: str) -> bool:
    """True when a ``git stash apply`` failure is ONLY about untracked files
    that already exist in the working tree.

    This is the tail end of the permission-denied autostash class: ``git stash
    push --include-untracked`` swept undeletable files (e.g. a root-owned
    ``packaging/`` directory) into the stash but could not remove them from
    disk.  On restore, git applies all tracked changes, then refuses to
    overwrite those still-present files (``already exists, no checkout`` /
    ``could not restore untracked files from stash``) and exits non-zero even
    though nothing was lost.  Any other error line (e.g. ``would be
    overwritten by merge`` / ``Aborting``) means the tracked apply itself
    failed and this returns False.
    """
    lines = [ln.strip() for ln in (stderr or "").splitlines() if ln.strip()]
    if not lines:
        return False
    saw_untracked_error = False
    for ln in lines:
        if "already exists, no checkout" in ln:
            saw_untracked_error = True
        elif "could not restore untracked files from stash" in ln:
            saw_untracked_error = True
        elif ln.startswith(("warning:", "hint:")):
            continue
        else:
            return False
    return saw_untracked_error


def _park_stashed_changes(stash_ref: str) -> None:
    """Leave a pre-update autostash parked instead of re-applying it.

    Used by ``hermes update --keep-stash`` (the desktop updater's mode): the
    stash made the update possible on a dirty tree, but local source edits
    must never be silently re-applied onto the updated code. Nothing is
    lost — the entry stays in ``git stash`` with printed recovery guidance.
    """
    print()
    print("ℹ️  Local changes were stashed before updating and were NOT re-applied (--keep-stash).")
    print(f"  Stash ref: {stash_ref}")
    print(f"  Restore manually with: git stash apply {stash_ref}")


def _restore_stashed_changes(
    git_cmd: list[str],
    cwd: Path,
    stash_ref: str,
    prompt_user: bool = False,
    input_fn=None,
) -> bool:
    if prompt_user:
        print()
        print("⚠ Local changes were stashed before updating.")
        print(
            "  Restoring them may reapply local customizations onto the updated codebase."
        )
        print("  Review the result afterward if Hermes behaves unexpectedly.")
        print("Restore local changes now? [Y/n]")
        if input_fn is not None:
            response = input_fn("Restore local changes now? [Y/n]", "y")
        else:
            try:
                response = input().strip().lower()
            except (EOFError, UnicodeDecodeError):
                # Mirror the config-migration prompt's fix: don't let a
                # terminal-encoding issue or a closed stdin crash the
                # update mid-restore. Falls through to the existing
                # skip-restore path below, which already explains how to
                # restore manually from git stash.
                response = "n"
        if response not in {"", "y", "yes"}:
            print("Skipped restoring local changes.")
            print("Your changes are still preserved in git stash.")
            print(f"Restore manually with: git stash apply {stash_ref}")
            return False

    print("→ Restoring local changes...")
    restore = subprocess.run(
        git_cmd + ["stash", "apply", stash_ref],
        cwd=cwd,
        capture_output=True,
        text=True, encoding="utf-8", errors="replace",
    )

    # Check for unmerged (conflicted) files — can happen even when returncode is 0
    unmerged = subprocess.run(
        git_cmd + ["diff", "--name-only", "--diff-filter=U"],
        cwd=cwd,
        capture_output=True,
        text=True, encoding="utf-8", errors="replace",
    )
    has_conflicts = bool(unmerged.stdout.strip())

    if restore.returncode != 0 and not has_conflicts and (
        _stash_apply_failed_only_on_existing_untracked(restore.stderr)
    ):
        # Permission-denied autostash tail end: the tracked changes applied
        # cleanly; the only "failure" is untracked files that never left the
        # working tree (git could not delete them at stash time, so it now
        # refuses to overwrite them). Their content was never touched —
        # nothing is lost. Treat as restored.
        print(
            "  ⚠ Some stashed untracked files already exist in the working "
            "tree and were kept as-is."
        )
    elif restore.returncode != 0 or has_conflicts:
        print("✗ Update pulled new code, but restoring local changes hit conflicts.")
        if restore.stdout.strip():
            print(restore.stdout.strip())
        if restore.stderr.strip():
            print(restore.stderr.strip())

        # Show which files conflicted
        conflicted_files = unmerged.stdout.strip()
        if conflicted_files:
            print("\nConflicted files:")
            for f in conflicted_files.splitlines():
                print(f"  • {f}")

        print("\nYour stashed changes are preserved — nothing is lost.")
        print(f"  Stash ref: {stash_ref}")

        # Always reset to clean state — leaving conflict markers in source
        # files makes hermes completely unrunnable (SyntaxError on import).
        # The user's changes are safe in the stash for manual recovery.
        subprocess.run(
            git_cmd + ["reset", "--hard", "HEAD"],
            cwd=cwd,
            capture_output=True,
        )
        print("Working tree reset to clean state.")
        print(f"Restore your changes later with: git stash apply {stash_ref}")
        # Don't sys.exit — the code update itself succeeded, only the stash
        # restore had conflicts.  Let cmd_update continue with pip install,
        # skill sync, and gateway restart.
        return False

    stash_selector = _resolve_stash_selector(git_cmd, cwd, stash_ref)
    if stash_selector is None:
        print(
            "⚠ Local changes were restored, but Hermes couldn't find the stash entry to drop."
        )
        print(
            "  The stash was left in place. You can remove it manually after checking the result."
        )
        _print_stash_cleanup_guidance(stash_ref)
    else:
        drop = subprocess.run(
            git_cmd + ["stash", "drop", stash_selector],
            cwd=cwd,
            capture_output=True,
            text=True, encoding="utf-8", errors="replace",
        )
        if drop.returncode != 0:
            print(
                "⚠ Local changes were restored, but Hermes couldn't drop the saved stash entry."
            )
            if drop.stdout.strip():
                print(drop.stdout.strip())
            if drop.stderr.strip():
                print(drop.stderr.strip())
            print(
                "  The stash was left in place. You can remove it manually after checking the result."
            )
            _print_stash_cleanup_guidance(stash_ref, stash_selector)

    print("⚠ Local changes were restored on top of the updated codebase.")
    print("  Review `git diff` / `git status` if Hermes behaves unexpectedly.")
    return True


def _discard_stashed_changes(
    git_cmd: list[str],
    cwd: Path,
    stash_ref: str,
) -> bool:
    """Throw away a stash created before an update, without applying it.

    Used only on a NON-interactive update when the user has set
    ``updates.non_interactive_local_changes: discard`` — i.e. they've opted out
    of keeping local source edits on this machine. Drops the stash entry
    instead of re-applying it, so the working tree stays clean at the freshly
    pulled HEAD. Unlike ``git reset --hard`` + ``git clean -fd``, this only
    affects what was stashed (tracked changes + the untracked files we
    explicitly captured) — ignored paths like node_modules/venv/build outputs
    are never touched, since they were never stashed.

    Returns True if the stash was dropped, False on a git failure (in which
    case the stash is left in place for safety).
    """
    stash_selector = _resolve_stash_selector(git_cmd, cwd, stash_ref)
    if stash_selector is None:
        print(
            "⚠ Configured to discard local changes on non-interactive update, "
            "but Hermes couldn't find the stash entry to drop."
        )
        _print_stash_cleanup_guidance(stash_ref)
        return False

    drop = subprocess.run(
        git_cmd + ["stash", "drop", stash_selector],
        cwd=cwd,
        capture_output=True,
        text=True, encoding="utf-8", errors="replace",
    )
    if drop.returncode != 0:
        print(
            "⚠ Configured to discard local changes, but Hermes couldn't drop "
            "the saved stash entry."
        )
        if drop.stderr.strip():
            print(f"  {drop.stderr.strip().splitlines()[0]}")
        _print_stash_cleanup_guidance(stash_ref, stash_selector)
        return False

    print("→ Discarded local source changes (updates.non_interactive_local_changes=discard).")
    return True


OFFICIAL_REPO_URLS = {
    "https://github.com/NousResearch/hermes-agent.git",
    "git@github.com:NousResearch/hermes-agent.git",
    "https://github.com/NousResearch/hermes-agent",
    "git@github.com:NousResearch/hermes-agent",
}


OFFICIAL_REPO_URL = "https://github.com/NousResearch/hermes-agent.git"


SKIP_UPSTREAM_PROMPT_FILE = ".skip_upstream_prompt"


def _get_origin_url(git_cmd: list[str], cwd: Path) -> Optional[str]:
    """Get the URL of the origin remote, or None if not set."""
    try:
        result = subprocess.run(
            git_cmd + ["remote", "get-url", "origin"],
            cwd=cwd,
            capture_output=True,
            text=True, encoding="utf-8", errors="replace",
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return None


def _is_fork(origin_url: Optional[str]) -> bool:
    """Check if the origin remote points to a fork (not the official repo)."""
    if not origin_url:
        return False
    # Normalize URL for comparison (strip trailing .git if present)
    normalized = origin_url.rstrip("/")
    if normalized.endswith(".git"):
        normalized = normalized[:-4]
    for official in OFFICIAL_REPO_URLS:
        official_normalized = official.rstrip("/")
        if official_normalized.endswith(".git"):
            official_normalized = official_normalized[:-4]
        if normalized == official_normalized:
            return False
    return True


def _has_upstream_remote(git_cmd: list[str], cwd: Path) -> bool:
    """Check if an 'upstream' remote already exists."""
    try:
        result = subprocess.run(
            git_cmd + ["remote", "get-url", "upstream"],
            cwd=cwd,
            capture_output=True,
            text=True, encoding="utf-8", errors="replace",
        )
        return result.returncode == 0
    except Exception:
        return False


def _add_upstream_remote(git_cmd: list[str], cwd: Path) -> bool:
    """Add the official repo as the 'upstream' remote. Returns True on success."""
    try:
        result = subprocess.run(
            git_cmd + ["remote", "add", "upstream", OFFICIAL_REPO_URL],
            cwd=cwd,
            capture_output=True,
            text=True, encoding="utf-8", errors="replace",
        )
        return result.returncode == 0
    except Exception:
        return False


def _count_commits_between(git_cmd: list[str], cwd: Path, base: str, head: str) -> int:
    """Count commits on `head` that are not on `base`. Returns -1 on error."""
    try:
        result = subprocess.run(
            git_cmd + ["rev-list", "--count", f"{base}..{head}"],
            cwd=cwd,
            capture_output=True,
            text=True, encoding="utf-8", errors="replace",
        )
        if result.returncode == 0:
            return int(result.stdout.strip())
    except Exception:
        pass
    return -1


def _should_skip_upstream_prompt() -> bool:
    """Check if user previously declined to add upstream."""
    from hermes_constants import get_hermes_home

    return (get_hermes_home() / SKIP_UPSTREAM_PROMPT_FILE).exists()


def _mark_skip_upstream_prompt():
    """Create marker file to skip future upstream prompts."""
    try:
        from hermes_constants import get_hermes_home

        (get_hermes_home() / SKIP_UPSTREAM_PROMPT_FILE).touch()
    except Exception:
        pass


def _sync_fork_with_upstream(git_cmd: list[str], cwd: Path) -> bool:
    """Attempt to push updated main to origin (sync fork).

    Returns True if push succeeded, False otherwise.
    """
    try:
        result = subprocess.run(
            git_cmd + ["push", "origin", "main", "--force-with-lease"],
            cwd=cwd,
            capture_output=True,
            text=True, encoding="utf-8", errors="replace",
        )
        return result.returncode == 0
    except Exception:
        return False


def _sync_with_upstream_if_needed(
    git_cmd: list[str],
    cwd: Path,
    *,
    assume_yes: bool = False,
    input_fn=None,
) -> bool:
    """Check if fork is behind upstream and sync if safe.

    This implements the fork upstream sync logic:
    - If upstream remote doesn't exist, ask user if they want to add it
    - Compare origin/main with upstream/main
    - If origin/main is strictly behind upstream/main, pull from upstream
    - Try to sync fork back to origin if possible

    Returns True when origin/main was actually verified against the official
    upstream/main, False when the check never happened (prompt skipped or
    declined, remote add failed, fetch or compare failed) so the caller can
    avoid reporting the checkout as up to date on the strength of an origin
    comparison alone (#97052 review).
    """
    has_upstream = _has_upstream_remote(git_cmd, cwd)

    if not has_upstream:
        # Check if user previously declined
        if _should_skip_upstream_prompt():
            return False

        print()
        print("ℹ Your fork is not tracking the official Hermes repository.")
        print("  This means you may miss updates from NousResearch/hermes-agent.")
        print()

        if assume_yes or (
            input_fn is None and not (sys.stdin.isatty() and sys.stdout.isatty())
        ):
            # --yes means "don't block", not "mutate my git remotes". Skip
            # without persisting the decline so interactive runs still get asked.
            print("  Skipping upstream setup (non-interactive run).")
            print(
                "  Add it later with: git remote add upstream https://github.com/NousResearch/hermes-agent.git"
            )
            return False

        # Ask user if they want to add upstream
        if input_fn is not None:
            response = (
                input_fn("Add official repo as 'upstream' remote? [y/N]", "n")
                .strip()
                .lower()
            )
        else:
            try:
                response = (
                    input("Add official repo as 'upstream' remote? [Y/n]: ")
                    .strip()
                    .lower()
                )
            except (EOFError, KeyboardInterrupt, UnicodeDecodeError):
                print()
                response = "n"

        if response in {"", "y", "yes"}:
            print("→ Adding upstream remote...")
            if _add_upstream_remote(git_cmd, cwd):
                print(
                    "  ✓ Added upstream: https://github.com/NousResearch/hermes-agent.git"
                )
                has_upstream = True
            else:
                print("  ✗ Failed to add upstream remote. Skipping upstream sync.")
                return False
        else:
            print(
                "  Skipped. Run 'git remote add upstream https://github.com/NousResearch/hermes-agent.git' to add later."
            )
            _mark_skip_upstream_prompt()
            return False

    # Fetch upstream main only. This sync compares upstream/main with
    # origin/main, so there's no reason to pull every upstream ref — and a bare
    # fetch drags in thousands of auto-generated branches.
    print()
    print("→ Fetching upstream...")
    try:
        subprocess.run(
            git_cmd + ["fetch", "upstream", "main", "--quiet"],
            cwd=cwd,
            capture_output=True,
            check=True,
        )
    except subprocess.CalledProcessError:
        print("  ✗ Failed to fetch upstream. Skipping upstream sync.")
        return False

    # Compare origin/main with upstream/main
    origin_ahead = _count_commits_between(git_cmd, cwd, "upstream/main", "origin/main")
    upstream_ahead = _count_commits_between(
        git_cmd, cwd, "origin/main", "upstream/main"
    )

    if origin_ahead < 0 or upstream_ahead < 0:
        print("  ✗ Could not compare branches. Skipping upstream sync.")
        return False

    # If origin/main has commits not on upstream, don't trample
    if origin_ahead > 0:
        print()
        print(f"ℹ Your fork has {origin_ahead} commit(s) not on upstream.")
        print("  Skipping upstream sync to preserve your changes.")
        print("  If you want to merge upstream changes, run:")
        print("    git pull upstream main")
        return True

    # If upstream is not ahead, fork is up to date
    if upstream_ahead == 0:
        print("  ✓ Fork is up to date with upstream")
        return True

    # origin/main is strictly behind upstream/main (can fast-forward)
    print()
    print(f"→ Fork is {upstream_ahead} commit(s) behind upstream")
    print("→ Pulling from upstream...")

    try:
        subprocess.run(
            git_cmd + ["pull", "--ff-only", "upstream", "main"],
            cwd=cwd,
            check=True,
        )
    except subprocess.CalledProcessError:
        print(
            "  ✗ Failed to pull from upstream. You may need to resolve conflicts manually."
        )
        return False

    print("  ✓ Updated from upstream")

    # Try to sync fork back to origin
    print("→ Syncing fork...")
    if _sync_fork_with_upstream(git_cmd, cwd):
        print("  ✓ Fork synced with upstream")
    else:
        print(
            "  ℹ Got updates from upstream but couldn't push to fork (no write access?)"
        )
        print("    Your local repo is updated, but your fork on GitHub may be behind.")
    return True


def _cmd_update_check(branch: str = "main", *, branch_explicit: bool = False):
    """Implement ``hermes update --check``: fetch and report without installing.

    ``branch`` selects which branch the check compares against. Default is
    "main"; callers can pass another branch to ask "are there new commits
    on origin/<branch>?" without performing the update.

    ``branch_explicit`` is True iff the caller passed --branch on the CLI.
    Installs that can't honor non-default branches (e.g. Docker) surface a
    one-line notice instead of silently dropping the flag.
    """
    # Shared admission gate (#91277 Phase 3): same marker-first decision as
    # the apply path, so --check can never report git state for an install
    # whose real update mechanism is an image pull.
    from hermes_cli.update_contract import (
        evaluate_update_admission,
        record_refusal_receipt,
    )

    refusal = evaluate_update_admission(_m().PROJECT_ROOT)
    if refusal is not None:
        print(refusal.message)
        record_refusal_receipt(refusal)
        sys.exit(2)

    git_dir = _m().PROJECT_ROOT / ".git"
    if not git_dir.exists():
        print("✗ Not a git repository — cannot check for updates.")
        sys.exit(1)

    git_cmd = ["git"]
    if sys.platform == "win32":
        git_cmd = ["git", "-c", "windows.appendAtomically=false"]

    # A crashed/interrupted fetch can leave .git/shallow.lock (or another git
    # lock file) behind; every later fetch then fails with "File exists" and
    # the check reports a hard failure (or, in the banner path, silently
    # compares stale refs). Self-heal abandoned locks before fetching.
    from hermes_cli.gitlock import clear_stale_git_locks, clear_stale_tmp_packs

    cleared = clear_stale_git_locks(_m().PROJECT_ROOT)
    for lock_path in cleared:
        print(f"  (removed stale git lock: {lock_path})")
    # Aborted fetches on flaky lines also strand tmp_pack_* debris in
    # .git/objects/pack — unchecked it reached 6 GB and corrupted the pack
    # dir outright (#93732). Same age+process safety contract as the locks.
    swept = clear_stale_tmp_packs(_m().PROJECT_ROOT)
    if swept:
        print(f"  (removed {len(swept)} aborted-fetch pack temp file(s))")

    # Fetch only the branch we compare against; prefer upstream as the canonical
    # reference. A bare `git fetch <remote>` pulls every ref, and this repo has
    # thousands of auto-generated branches, so scope the fetch to <branch>.
    # Note: upstream/<branch> may not exist for non-main branches (a fork's
    # bb/gui has no upstream counterpart), so when the caller picks a
    # non-default branch we skip the upstream probe and use origin directly.
    # Installer checkouts are shallow (`git clone --depth 1`). A plain
    # `git fetch` would unshallow the repo (dragging in the whole history —
    # the exact cost the shallow clone avoided) and the rev-list count below
    # would then report a huge bogus "behind" number. Detect shallow up front:
    # fetch with --depth 1 to preserve the boundary and report presence-only.
    is_shallow = (
        subprocess.run(
            git_cmd + ["rev-parse", "--is-shallow-repository"],
            cwd=_m().PROJECT_ROOT,
            capture_output=True,
            text=True, encoding="utf-8", errors="replace",
        ).stdout.strip()
        == "true"
    )
    depth_args = ["--depth", "1"] if is_shallow else []

    if branch == "main":
        # Probe locally (~6 ms) whether an 'upstream' remote exists at all
        # before spending a network fetch on it. Non-fork installs have no
        # 'upstream' remote, and the old flow burned a failed network attempt
        # (~0.3-1 s) on every --check before falling back to origin.
        has_upstream_remote = (
            subprocess.run(
                git_cmd + ["remote", "get-url", "upstream"],
                cwd=_m().PROJECT_ROOT,
                capture_output=True,
                text=True, encoding="utf-8", errors="replace",
            ).returncode
            == 0
        )
        fetch_result = None
        if has_upstream_remote:
            print("→ Fetching from upstream...")
            fetch_result = subprocess.run(
                git_cmd + ["fetch"] + depth_args + ["upstream", branch],
                cwd=_m().PROJECT_ROOT,
                capture_output=True,
                text=True, encoding="utf-8", errors="replace",
            )
        if fetch_result is not None and fetch_result.returncode == 0:
            upstream_exists = True
            compare_branch = f"upstream/{branch}"
        else:
            # No upstream remote, or the upstream fetch failed — use origin.
            print("→ Fetching from origin...")
            fetch_result = subprocess.run(
                git_cmd + ["fetch"] + depth_args + ["origin", branch],
                cwd=_m().PROJECT_ROOT,
                capture_output=True,
                text=True, encoding="utf-8", errors="replace",
            )
            upstream_exists = False
            compare_branch = f"origin/{branch}"
    else:
        # Non-default branch: compare against origin/<branch> directly.
        print("→ Fetching from origin...")
        fetch_result = subprocess.run(
            git_cmd + ["fetch"] + depth_args + ["origin", branch],
            cwd=_m().PROJECT_ROOT,
            capture_output=True,
            text=True, encoding="utf-8", errors="replace",
        )
        upstream_exists = False
        compare_branch = f"origin/{branch}"

    if fetch_result.returncode != 0:
        _print_fetch_failure(fetch_result.stderr)
        sys.exit(1)

    # Verify the compare ref actually exists before asking rev-list about it.
    # Without this, `git rev-list HEAD..origin/<bogus> --count` exits 128 and
    # (with check=True) raises CalledProcessError, surfacing a Python
    # traceback. Friendlier to detect-and-report.
    verify_result = subprocess.run(
        git_cmd + ["rev-parse", "--verify", "--quiet", compare_branch],
        cwd=_m().PROJECT_ROOT,
        capture_output=True,
        text=True, encoding="utf-8", errors="replace",
    )
    if verify_result.returncode != 0:
        print(f"✗ Branch '{branch}' not found on {compare_branch.split('/', 1)[0]}.")
        sys.exit(1)

    if is_shallow:
        # No history to count across the shallow boundary. Compare tip SHAs
        # (mirrors the banner's _check_via_local_git), then try to recover the
        # exact count via the GitHub compare API — the remote graph is complete
        # even when the local one is truncated.
        head_sha = subprocess.run(
            git_cmd + ["rev-parse", "HEAD"],
            cwd=_m().PROJECT_ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace",
        ).stdout.strip()
        target_sha = subprocess.run(
            git_cmd + ["rev-parse", compare_branch],
            cwd=_m().PROJECT_ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace",
        ).stdout.strip()
        if head_sha and target_sha and head_sha == target_sha:
            print("✓ Already up to date.")
        else:
            from hermes_cli.banner import _github_compare_behind
            from hermes_cli.config import recommended_update_command

            counted = _github_compare_behind(head_sha, target_sha)
            if counted == 0:
                # Local commits on top of the remote tip — not behind.
                print("✓ Already up to date.")
                return
            if counted is not None:
                commits_word = "commit" if counted == 1 else "commits"
                print(f"⚕ Update available: {counted} {commits_word} behind {compare_branch}.")
            else:
                print(f"⚕ Update available (behind {compare_branch}).")
            print(f"  Run '{recommended_update_command()}' to install.")
        return

    rev_result = subprocess.run(
        git_cmd + ["rev-list", f"HEAD..{compare_branch}", "--count"],
        cwd=_m().PROJECT_ROOT,
        capture_output=True,
        text=True, encoding="utf-8", errors="replace",
        check=True,
    )
    behind = int(rev_result.stdout.strip())

    if behind == 0:
        print("✓ Already up to date.")
    else:
        commits_word = "commit" if behind == 1 else "commits"
        print(f"⚕ Update available: {behind} {commits_word} behind {compare_branch}.")
        from hermes_cli.config import recommended_update_command

        print(f"  Run '{recommended_update_command()}' to install.")


def _discard_lockfile_churn(git_cmd, repo_root):
    """Restore tracked ``package-lock.json`` files that npm dirtied locally.

    npm rewrites lockfiles non-deterministically at install/build time. On a
    managed install those diffs are never intentional, so we discard them so
    ``hermes update`` sees a clean tree instead of autostashing every run.
    Best-effort; only ever touches files named ``package-lock.json``.
    """
    try:
        diff = subprocess.run(
            git_cmd + ["diff", "--name-only"],
            cwd=repo_root,
            capture_output=True,
            text=True, encoding="utf-8", errors="replace",
        )
        if diff.returncode != 0:
            return
        dirty_package_dirs = {
            Path(line.strip()).parent
            for line in diff.stdout.splitlines()
            if line.strip().endswith("package.json")
        }
        dirty = [
            line.strip()
            for line in diff.stdout.splitlines()
            if line.strip().endswith("package-lock.json")
            and Path(line.strip()).parent not in dirty_package_dirs
        ]
        if not dirty:
            return
        subprocess.run(
            git_cmd + ["checkout", "--", *dirty],
            cwd=repo_root,
            capture_output=True,
            text=True, encoding="utf-8", errors="replace",
            check=False,
        )
        print(f"→ Discarded npm lockfile churn ({len(dirty)} file(s))")
    except Exception:
        # Never let lockfile cleanup block an update.
        pass


def _normalize_managed_eol(git_cmd, repo_root):
    """Take a managed checkout off ``core.autocrlf=true`` without leaving it dirty.

    Git for Windows ships ``core.autocrlf=true`` in its system config, which
    renormalizes this repo's LF text files to CRLF in the working tree. That
    breaks ``git checkout`` on update with "Your local changes would be
    overwritten", so ``install.ps1`` pins ``core.autocrlf=false`` on the managed
    clone (#67730). Checkouts created before that landed never got the pin and
    cannot receive it — the bootstrap installer reuses its build-pinned
    ``install.ps1`` forever — so ``hermes update``, which ships with the checkout
    itself, is the only path left that can fix them.

    The pin and the cleanup are one operation. Under ``autocrlf=true`` git
    compares normalized content, so a CRLF working tree reads clean; pinning
    alone would expose every text file as modified and hand the update an
    autostash of the whole tree. So the pin is written only after the tree is
    verified clean under it, and a checkout we cannot fully normalize is left
    exactly as it was. Best-effort: never blocks an update.
    """
    # -c, not config: evaluate the tree as it WOULD look pinned, without
    # persisting anything we might not be able to follow through on.
    probe = git_cmd + ["-c", "core.autocrlf=false"]

    def _dirty(*extra):
        out = subprocess.run(
            probe + ["diff", "-z", "--name-only", *extra],
            cwd=repo_root,
            capture_output=True,
            text=True, encoding="utf-8", errors="replace",
        )
        if out.returncode != 0:
            return None
        return {p for p in out.stdout.split("\0") if p}

    def _real_dirty():
        # Files with a *content* change once CRLF differences are ignored.
        # NOTE: ``diff --name-only --ignore-cr-at-eol`` still LISTS CR-only
        # files (the name list is computed from blob/stat differences before
        # the CR filter is applied), so it cannot be used to isolate real
        # edits. ``--numstat`` does honor the filter: a CR-only file produces
        # no numstat record, while a genuinely-edited file does. Parse the
        # paths out of numstat instead.
        out = subprocess.run(
            probe + ["-c", "core.quotepath=false",
                     "diff", "--numstat", "--ignore-cr-at-eol"],
            cwd=repo_root,
            capture_output=True,
            text=True, encoding="utf-8", errors="replace",
        )
        if out.returncode != 0:
            return None
        paths = set()
        for line in out.stdout.splitlines():
            if not line.strip():
                continue
            # Format: "<added>\t<deleted>\t<path>". Rename detection is off in
            # plain diff, so there is exactly one path field per record.
            parts = line.split("\t", 2)
            if len(parts) == 3 and parts[2]:
                paths.add(parts[2])
        return paths

    def _eol_only():
        all_dirty, real_dirty = _dirty(), _real_dirty()
        if all_dirty is None or real_dirty is None:
            return None
        return all_dirty - real_dirty

    try:
        effective = subprocess.run(
            git_cmd + ["config", "--get", "core.autocrlf"],
            cwd=repo_root,
            capture_output=True,
            text=True, encoding="utf-8", errors="replace",
        )
        # Only "true" rewrites LF to CRLF on checkout. Unset, false, and input
        # all leave the working tree alone, so there is nothing to repair.
        if effective.stdout.strip().lower() != "true":
            return

        eol_only = _eol_only()
        if eol_only is None:
            return
        if eol_only:
            # Pathspec over stdin, not argv: a fully renormalized checkout is
            # thousands of paths, well past the Windows command-line limit.
            subprocess.run(
                probe
                + ["checkout", "--pathspec-from-file=-", "--pathspec-file-nul", "--"],
                cwd=repo_root,
                input="\0".join(sorted(eol_only)),
                capture_output=True,
                text=True, encoding="utf-8", errors="replace",
                check=False,
            )
            if _eol_only():
                # Still dirty — persisting the pin here would only surface churn
                # we failed to clear. Leave the checkout as we found it.
                return
            print(f"→ Normalized line-ending churn ({len(eol_only)} file(s))")

        subprocess.run(
            git_cmd + ["config", "core.autocrlf", "false"],
            cwd=repo_root,
            capture_output=True,
            check=False,
        )
    except Exception:
        # Never let line-ending cleanup block an update.
        pass
