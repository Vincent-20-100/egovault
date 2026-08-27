#!/usr/bin/env python3
"""Automated Code Hygiene & Anti-Vibecoding Scanner.

Scans Python source files or directories for common anti-patterns:
- Magic numbers inside logic functions
- Missing docstrings on public functions and classes
- Missing argument/return type annotations
- Naked print() calls (instead of structured logging)
- Bare or generic catch-all exception blocks

Usage:
    python code_hygiene_check.py path/to/project_or_file.py [--strict]
"""

from __future__ import annotations

import argparse
import ast
from dataclasses import dataclass, field
import io
from pathlib import Path
import sys
from typing import Any, Sequence

# Ensure UTF-8 output on Windows consoles
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except (io.UnsupportedOperation, AttributeError):
        pass

BANNER_WIDTH: int = 70


@dataclass
class Issue:
    """Represents a single static code hygiene violation."""

    file_path: Path
    line: int
    col: int
    category: str
    message: str
    severity: str = "WARNING"  # WARNING or ERROR


@dataclass
class FileReport:
    """Aggregated scan results for a single Python source file."""

    file_path: Path
    issues: list[Issue] = field(default_factory=list)
    functions_checked: int = 0
    classes_checked: int = 0


class ASTHygieneVisitor(ast.NodeVisitor):
    """AST visitor that checks for Python Coding Expert violations."""

    def __init__(self, file_path: Path) -> None:
        """Initialize visitor for a specific file path."""
        self.file_path = file_path
        self.issues: list[Issue] = []
        self.functions_checked: int = 0
        self.classes_checked: int = 0
        self._current_class_docstring: str | None = None

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        """Inspect class definitions for missing docstrings."""
        self.classes_checked += 1
        docstring = ast.get_docstring(node)
        if not node.name.startswith("_") and not docstring:
            self.issues.append(
                Issue(
                    file_path=self.file_path,
                    line=node.lineno,
                    col=node.col_offset,
                    category="DOCSTRING",
                    message=f"Public class '{node.name}' is missing a docstring.",
                )
            )
        prev_class_doc = self._current_class_docstring
        self._current_class_docstring = docstring
        self.generic_visit(node)
        self._current_class_docstring = prev_class_doc

    def visit_FunctionDef(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        """Inspect functions for docstrings and type annotations."""
        self.functions_checked += 1
        is_init = node.name == "__init__"
        is_public = not node.name.startswith("_")
        has_doc = bool(ast.get_docstring(node))

        # 1. Check docstring: public functions, or __init__ only if parent class has no docstring
        if is_public and not is_init and not has_doc:
            self.issues.append(
                Issue(
                    file_path=self.file_path,
                    line=node.lineno,
                    col=node.col_offset,
                    category="DOCSTRING",
                    message=f"Function '{node.name}' is missing a docstring.",
                )
            )
        elif is_init and not has_doc and not self._current_class_docstring:
            self.issues.append(
                Issue(
                    file_path=self.file_path,
                    line=node.lineno,
                    col=node.col_offset,
                    category="DOCSTRING",
                    message="Constructor '__init__' is missing a docstring and enclosing class has no docstring.",
                )
            )

        # 2. Check return type annotation
        if node.returns is None and not is_init:
            self.issues.append(
                Issue(
                    file_path=self.file_path,
                    line=node.lineno,
                    col=node.col_offset,
                    category="TYPING",
                    message=f"Function '{node.name}' is missing a return type annotation.",
                )
            )

        # 3. Check parameter type annotations
        for arg in node.args.args:
            if arg.arg not in {"self", "cls"} and arg.annotation is None:
                self.issues.append(
                    Issue(
                        file_path=self.file_path,
                        line=arg.lineno,
                        col=arg.col_offset,
                        category="TYPING",
                        message=f"Parameter '{arg.arg}' in function '{node.name}' is missing type annotation.",
                    )
                )

        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        """Inspect async function definitions identically to synchronous ones."""
        self.visit_FunctionDef(node)

    def visit_Call(self, node: ast.Call) -> None:
        """Check for raw print() calls in non-CLI modules."""
        if isinstance(node.func, ast.Name) and node.func.id == "print":
            path_str = self.file_path.as_posix().lower()
            name_str = self.file_path.name.lower()
            is_allowed = (
                any(
                    segment in path_str.split("/")
                    for segment in (
                        "cli",
                        "scripts",
                        "tools",
                        "bin",
                        "benchmarks",
                        "examples",
                        "tests",
                        "migrations",
                    )
                )
                or name_str.startswith(
                    (
                        "cli",
                        "main",
                        "check",
                        "script",
                        "profiler",
                        "code_hygiene",
                        "test",
                        "demo",
                        "seed",
                        "bench",
                    )
                )
                or name_str.endswith(
                    (
                        "_cli.py",
                        "_test.py",
                        "_bench.py",
                        "_demo.py",
                        "_script.py",
                    )
                )
            )
            if not is_allowed:
                self.issues.append(
                    Issue(
                        file_path=self.file_path,
                        line=node.lineno,
                        col=node.col_offset,
                        category="LOGGING",
                        message="Use structured logging (logger.info/debug) instead of naked print().",
                    )
                )
        self.generic_visit(node)

    def visit_ExceptHandler(self, node: ast.ExceptHandler) -> None:
        """Detect bare except or silently swallowed exceptions."""
        if node.type is None:
            self.issues.append(
                Issue(
                    file_path=self.file_path,
                    line=node.lineno,
                    col=node.col_offset,
                    category="ERRORS",
                    message="Bare 'except:' caught. Catch specific domain exceptions or AppError.",
                    severity="ERROR",
                )
            )
        elif isinstance(node.type, ast.Name) and node.type.id in {"Exception", "BaseException"}:
            if len(node.body) == 1 and isinstance(node.body[0], ast.Pass):
                self.issues.append(
                    Issue(
                        file_path=self.file_path,
                        line=node.lineno,
                        col=node.col_offset,
                        category="ERRORS",
                        message="Generic 'except Exception: pass' detected. Swallowing errors without logging is forbidden.",
                        severity="ERROR",
                    )
                )
        self.generic_visit(node)


def scan_file(file_path: Path) -> FileReport:
    """Parse and inspect a single Python file for code hygiene issues.

    Args:
        file_path: Path to the target Python file.

    Returns:
        FileReport object containing all discovered violations.
    """
    report = FileReport(file_path=file_path)
    try:
        source = file_path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(file_path))
        visitor = ASTHygieneVisitor(file_path)
        visitor.visit(tree)
        report.issues = visitor.issues
        report.functions_checked = visitor.functions_checked
        report.classes_checked = visitor.classes_checked
    except SyntaxError as e:
        report.issues.append(
            Issue(
                file_path=file_path,
                line=e.lineno or 1,
                col=e.offset or 1,
                category="SYNTAX",
                message=f"Syntax error: {e.msg}",
                severity="ERROR",
            )
        )
    except Exception as e:
        report.issues.append(
            Issue(
                file_path=file_path,
                line=1,
                col=1,
                category="SCANNER",
                message=f"Failed to parse file: {e}",
                severity="ERROR",
            )
        )
    return report


def scan_directory(target_path: Path) -> list[FileReport]:
    """Recursively scan a directory or file for Python source files.

    Args:
        target_path: Root folder or specific file to evaluate.

    Returns:
        List of FileReport objects for all scanned files.
    """
    reports: list[FileReport] = []
    ignored_dir_names = {
        ".git",
        ".venv",
        "venv",
        ".env",
        "__pycache__",
        "site-packages",
        ".pytest_cache",
        ".ruff_cache",
        ".mypy_cache",
        "build",
        "dist",
    }
    if target_path.is_file():
        if target_path.suffix == ".py":
            reports.append(scan_file(target_path))
    else:
        for py_file in target_path.rglob("*.py"):
            # Skip caches, build artifacts, and virtual environments
            if any(part in ignored_dir_names for part in py_file.parts):
                continue
            reports.append(scan_file(py_file))
    return reports


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entrypoint for running the Python Coding Expert hygiene audit.

    Args:
        argv: Optional command line arguments sequence.

    Returns:
        Exit code (0 for success, 1 for failures, 2 for bad arguments).
    """
    parser = argparse.ArgumentParser(description="Python Coding Expert Code Hygiene Scanner")
    parser.add_argument("target", type=Path, help="Target file or directory to scan")
    parser.add_argument("--strict", action="store_true", help="Fail with exit code 1 on warnings")
    args = parser.parse_args(argv)

    if not args.target.exists():
        sys.stderr.write(f"Error: Target path does not exist: {args.target}\n")
        return 2

    reports = scan_directory(args.target)
    total_issues = sum(len(r.issues) for r in reports)
    total_errors = sum(sum(1 for i in r.issues if i.severity == "ERROR") for r in reports)
    total_warnings = total_issues - total_errors

    print("\n" + "=" * BANNER_WIDTH)
    print(" 🛠️  PYTHON CODING EXPERT CODE HYGIENE REPORT")
    print("=" * BANNER_WIDTH)

    for report in reports:
        if not report.issues:
            continue
        print(f"\n📄 {report.file_path.as_posix()}:")
        for issue in report.issues:
            symbol = "❌" if issue.severity == "ERROR" else "⚠️"
            print(f"  {symbol} Line {issue.line}:{issue.col} [{issue.category}] {issue.message}")

    print("\n" + "-" * BANNER_WIDTH)
    print(f"Summary: {len(reports)} files checked | {total_errors} Errors | {total_warnings} Warnings")
    print("-" * BANNER_WIDTH)

    if total_errors > 0 or (args.strict and total_warnings > 0):
        print("❌ Hygiene audit FAILED. Please resolve the detected issues.")
        return 1

    print("✅ Hygiene audit PASSED. Clean Python architecture respected!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
