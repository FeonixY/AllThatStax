"""Command line entry point for the AllThatStax toolchain."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from allthatstax.config import load_config
from allthatstax.latex_text import generate_latex_text
from get_cards_information import get_cards_information
from localization import localization
from run_latex import run_latex

DEFAULT_CONFIG = Path("config.json")


def _resolve_config_path(path: Path) -> Path:
    return path if path.is_absolute() else (Path.cwd() / path)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate the AllThatStax LaTeX book.")
    parser.add_argument(
        "--config",
        type=Path,
        default=DEFAULT_CONFIG,
        help="Path to the configuration JSON file",
    )
    parser.add_argument(
        "--fetch",
        action="store_true",
        help="Refresh card information using the network fetcher",
    )
    parser.add_argument(
        "--fetch-from-scratch",
        action="store_true",
        help="Rebuild the workbook from scratch when fetching cards",
    )
    parser.add_argument(
        "--localize",
        action="store_true",
        help="Augment the workbook with localized text using Selenium",
    )
    parser.add_argument(
        "--skip-compile",
        action="store_true",
        help="Skip running the LaTeX compiler after updating the document",
    )
    parser.add_argument(
        "--latex-command",
        nargs="+",
        help="Override the LaTeX command (defaults to xelatex …)",
    )
    return parser


def _resolve_paths(config_path: Path, config: Mapping[str, Any]) -> dict[str, Path]:
    base_dir = config_path.parent
    return {
        "image_folder": base_dir / str(config["image_folder_name"]),
        "sheet_file": base_dir / str(config["sheet_file_name"]),
        "card_list": base_dir / str(config["card_list_name"]),
        "latex_text": base_dir / str(config["latex_text_name"]),
        "latex_file": base_dir / str(config["latex_file_name"]),
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    config_path = _resolve_config_path(args.config)
    config = load_config(config_path)
    try:
        paths = _resolve_paths(config_path, config)
    except KeyError as exc:
        parser.error(f"Missing configuration key: {exc.args[0]}")

    try:
        sheet_name = str(config["sheet_name"])
        multiface_sheet_name = str(config["multiface_sheet_name"])
    except KeyError as exc:
        parser.error(f"Missing configuration key: {exc.args[0]}")

    stax_types = dict(config.get("stax_type", {}))

    fetch_cards = args.fetch or args.fetch_from_scratch
    if fetch_cards:
        print("Fetching card information…")
        get_cards_information(
            str(paths["image_folder"]),
            str(paths["sheet_file"]),
            sheet_name,
            multiface_sheet_name,
            str(paths["card_list"]),
            stax_types,
            from_scratch=args.fetch_from_scratch,
        )

    if args.localize:
        print("Localizing missing card information…")
        localization(
            str(paths["sheet_file"]),
            sheet_name,
            multiface_sheet_name,
        )

    print("Generating LaTeX snippets…")
    generate_latex_text(
        sheet_file_name=str(paths["sheet_file"]),
        sheet_name=sheet_name,
        multiface_sheet_name=multiface_sheet_name,
        latex_text_name=str(paths["latex_text"]),
    )

    if args.skip_compile:
        print("Skipping LaTeX compilation as requested.")
        return 0

    command: Iterable[str] | None = tuple(args.latex_command) if args.latex_command else None
    print("Compiling LaTeX document…")
    run_latex(
        latex_file_name=str(paths["latex_file"]),
        latex_text_name=str(paths["latex_text"]),
        command=command,
    )
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    raise SystemExit(main())
