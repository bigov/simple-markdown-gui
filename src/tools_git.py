"""Helpers for checking and updating Git repository state on startup."""

import os
import re
import subprocess
from dataclasses import dataclass

from git import InvalidGitRepositoryError, NoSuchPathError, Repo
from git.exc import GitCommandError
from PySide6.QtWidgets import QMessageBox


@dataclass
class GitCommandResult:
    """Lightweight command result compatible with previous subprocess usage."""

    returncode: int
    stdout: str
    stderr: str


def is_git_repository_root(base_dir):
    """Return True when base_dir points to a Git repository root directory."""
    git_dir = os.path.join(base_dir, ".git")
    return os.path.isdir(git_dir)


def parse_git_behind_count(status_branch_line):
    """Extract behind count from 'git status --porcelain --branch' first line."""
    if not status_branch_line:
        return 0

    status_match = re.search(r"\[(.*?)\]", status_branch_line)
    if status_match is None:
        return 0

    behind_match = re.search(r"behind\s+(\d+)", status_match.group(1))
    if behind_match is None:
        return 0

    try:
        return int(behind_match.group(1))
    except ValueError:
        return 0


def run_git_command(base_dir, args, timeout_seconds=10):
    """Run a git command in base_dir and return GitCommandResult or None."""
    try:
        repo = Repo(base_dir)
        command = [repo.git.GIT_PYTHON_GIT_EXECUTABLE, *args]
        creationflags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
        returncode, stdout, stderr = repo.git.execute(
            command,
            with_extended_output=True,
            with_exceptions=False,
            stdout_as_string=True,
            universal_newlines=True,
            kill_after_timeout=timeout_seconds,
            creationflags=creationflags,
        )
        return GitCommandResult(returncode=returncode, stdout=stdout, stderr=stderr)
    except (
        NoSuchPathError,
        InvalidGitRepositoryError,
        GitCommandError,
        OSError,
        ValueError,
    ):
        return None


def get_git_branch_status_line(base_dir):
    """Return branch status line from git status output."""
    status_result = run_git_command(
        base_dir,
        ["status", "--porcelain", "--branch"],
        timeout_seconds=8,
    )
    if status_result is None or status_result.returncode != 0:
        return ""

    lines = status_result.stdout.splitlines()
    if not lines:
        return ""
    return lines[0].strip()


def prompt_git_pull_if_needed(parent_widget, base_dir, git_enable=None):
    """Offer git pull when base_dir is a repo root behind upstream."""
    if git_enable is None:
        git_enable = is_git_repository_root(base_dir)

    if not git_enable:
        return

    # Refresh remote tracking info before checking ahead/behind status.
    run_git_command(base_dir, ["fetch", "--quiet"], timeout_seconds=8)

    status_line = get_git_branch_status_line(base_dir)
    behind_count = parse_git_behind_count(status_line)
    if behind_count <= 0:
        return

    pull_question = QMessageBox.question(
        parent_widget,
        "Git update available",
        (
            "Configured base directory is a Git repository root.\n"
            f"Current branch is behind upstream by {behind_count} commit(s).\n\n"
            "Run git pull --ff-only now?"
        ),
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        QMessageBox.StandardButton.Yes,
    )
    if pull_question != QMessageBox.StandardButton.Yes:
        return

    pull_result = run_git_command(base_dir, ["pull", "--ff-only"], timeout_seconds=30)
    if pull_result is not None and pull_result.returncode == 0:
        details = pull_result.stdout.strip() or "Git pull completed successfully."
        QMessageBox.information(parent_widget, "Git pull completed", details)
        return

    error_details = "Unknown git error."
    if pull_result is not None:
        error_details = (
            pull_result.stderr.strip() or pull_result.stdout.strip() or error_details
        )

    QMessageBox.warning(
        parent_widget,
        "Git pull failed",
        f"Could not complete git pull --ff-only.\n\n{error_details}",
    )


def prompt_git_push_after_save(parent_widget, base_dir, git_enable):
    """Offer git push right after a successful file save when git is enabled."""
    if not git_enable:
        return

    push_question = QMessageBox.question(
        parent_widget,
        "Git push",
        "File saved successfully. Push current branch to remote now?",
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        QMessageBox.StandardButton.No,
    )
    if push_question != QMessageBox.StandardButton.Yes:
        return

    push_result = run_git_command(base_dir, ["push"], timeout_seconds=30)
    if push_result is not None and push_result.returncode == 0:
        details = push_result.stdout.strip() or "Git push completed successfully."
        QMessageBox.information(parent_widget, "Git push completed", details)
        return

    error_details = "Unknown git error."
    if push_result is not None:
        error_details = (
            push_result.stderr.strip() or push_result.stdout.strip() or error_details
        )

    QMessageBox.warning(
        parent_widget,
        "Git push failed",
        f"Could not complete git push.\n\n{error_details}",
    )


def initialize_git_integration(parent_widget, base_dir):
    """Initialize git_enable and run startup pull prompt when applicable."""
    git_enable = is_git_repository_root(base_dir)
    parent_widget.git_enable = git_enable
    prompt_git_pull_if_needed(parent_widget, base_dir, git_enable)


def handle_post_save_git_actions(parent_widget, base_dir):
    """Run post-save Git actions based on precomputed git_enable flag."""
    git_enable = getattr(parent_widget, "git_enable", False)
    prompt_git_push_after_save(parent_widget, base_dir, git_enable)
