"""Backward compatible wrapper for the old LaTeX generation entry point."""

from __future__ import annotations

from allthatstax.latex_text import generate_latex_text

__all__ = ["generate_latex_text", "genarate_latex_text"]


def genarate_latex_text(
    sheet_file_name: str,
    sheet_name: str,
    multiface_sheet_name: str,
    latex_text_name: str,
):
    return generate_latex_text(
        sheet_file_name=sheet_file_name,
        sheet_name=sheet_name,
        multiface_sheet_name=multiface_sheet_name,
        latex_text_name=latex_text_name,
    )
