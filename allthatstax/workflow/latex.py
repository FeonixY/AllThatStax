"""Utilities for updating and compiling the LaTeX document."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Iterable, Sequence

DEFAULT_COMMAND: Sequence[str] = (
    "xelatex",
    "-synctex=1",
    "-interaction=nonstopmode",
    "-shell-escape",
)
START_MARKER = "% Latex text starts here"
END_MARKER = "% Latex text ends here"

__all__ = ["DEFAULT_COMMAND", "run_latex", "inject_latex_text", "compile_latex"]


def inject_latex_text(
    latex_file: str | Path,
    latex_text: str | Path,
    *,
    start_marker: str = START_MARKER,
    end_marker: str = END_MARKER,
) -> Path:
    """Insert ``latex_text`` into ``latex_file`` between the configured markers."""

    latex_path = Path(latex_file)
    text_path = Path(latex_text)

    if not latex_path.exists():
        raise FileNotFoundError(f"LaTeX file not found: {latex_path}")
    if not text_path.exists():
        raise FileNotFoundError(f"LaTeX text file not found: {text_path}")

    latex_lines = latex_path.read_text(encoding="utf-8").splitlines(keepends=True)
    text_content = text_path.read_text(encoding="utf-8").rstrip()

    start_index = None
    end_index = None
    for idx, line in enumerate(latex_lines):
        if start_marker in line and start_index is None:
            start_index = idx + 1
        elif end_marker in line and start_index is not None:
            end_index = idx
            break

    if start_index is None or end_index is None:
        raise ValueError(
            f"Could not locate both start ('{start_marker}') and end ('{end_marker}') markers in {latex_path}"
        )

    replacement = f"\n{text_content}\n\n"
    latex_lines[start_index:end_index] = [replacement]
    latex_path.write_text("".join(latex_lines), encoding="utf-8")
    return latex_path


def compile_latex(
    latex_file: str | Path,
    *,
    command: Iterable[str] | None = None,
) -> subprocess.CompletedProcess[str]:
    """Compile the LaTeX document using the given command."""

    latex_path = Path(latex_file)
    if not latex_path.exists():
        raise FileNotFoundError(f"LaTeX file not found: {latex_path}")

    command_list = list(command or DEFAULT_COMMAND)
    command_list.append(str(latex_path))

    try:
        result = subprocess.run(
            command_list,
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
    except FileNotFoundError as exc:  # pragma: no cover - depends on environment
        raise RuntimeError(f"LaTeX compiler '{command_list[0]}' not found") from exc
    return result


def run_latex(
    latex_file_name: str | Path,
    latex_text_name: str | Path,
    *,
    command: Iterable[str] | None = None,
) -> subprocess.CompletedProcess[str]:
    """Update the LaTeX document and compile it."""

    inject_latex_text(latex_file_name, latex_text_name)
    result = compile_latex(latex_file_name, command=command)
    print(result.stdout)
    if result.stderr:
        print(result.stderr)
    return result
