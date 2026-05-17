"""Tests for the force_git_author PreToolUse hook command rewriter."""

import importlib.util
from pathlib import Path

_spec = importlib.util.spec_from_file_location(
    "force_git_author",
    Path(__file__).parent.parent.parent / "scripts" / "force_git_author.py",
)
fga = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(fga)

NAME, EMAIL = "Vincent", "vincent.lamy.33@gmail.com"
AUTH = f"--author='{NAME} <{EMAIL}>'"


def test_single_commit_gets_author_after_commit_keyword():
    out = fga.rewrite_command('git commit -q -m "feat: x"', NAME, EMAIL)
    assert out == f"git commit {AUTH} -q -m \"feat: x\""


def test_compound_command_author_lands_on_commit_not_last_segment():
    cmd = 'git add . && git commit -q -m "feat: x" && git status -s'
    out = fga.rewrite_command(cmd, NAME, EMAIL)
    # --author must be attached to the commit, NOT appended after `git status -s`
    assert out == f'git add . && git commit {AUTH} -q -m "feat: x" && git status -s'
    # regression guard: the old bug appended --author onto the last segment
    assert "status -s --author" not in out
    assert out.endswith("git status -s")  # last segment left intact


def test_existing_author_flag_is_stripped_then_reinjected_once():
    cmd = "git commit -m x --author='Old Name <old@x.com>'"
    out = fga.rewrite_command(cmd, NAME, EMAIL)
    assert out.count("--author=") == 1
    assert "Old Name" not in out
    assert AUTH in out


def test_non_commit_command_returns_none():
    assert fga.rewrite_command("git status -s", NAME, EMAIL) is None
    assert fga.rewrite_command('grep -r "commit" .', NAME, EMAIL) is None


def test_missing_identity_returns_none():
    assert fga.rewrite_command('git commit -m "x"', "", EMAIL) is None
    assert fga.rewrite_command('git commit -m "x"', NAME, "") is None
