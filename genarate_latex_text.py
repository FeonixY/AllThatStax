"""Backward compatible wrapper for the old LaTeX generation entry point."""

from __future__ import annotations

from allthatstax.latex_text import generate_latex_text

__all__ = ["generate_latex_text", "genarate_latex_text"]


def genarate_latex_text(
    data_file_name: str,
    latex_text_name: str,
    *,
    config_path: str | None = None,
):
    return generate_latex_text(
        data_file_name=data_file_name,
        latex_text_name=latex_text_name,
        config_path=config_path,
    )
