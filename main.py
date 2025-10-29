"""Command line entry point for the AllThatStax toolchain."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from allthatstax.config import load_config
from allthatstax.latex_text import generate_latex_text
from get_cards_information import get_cards_information
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
        "--no-download-images",
        action="store_true",
        help="Skip downloading card images during the fetch step",
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
        "data_file": base_dir / str(config["data_file_name"]),
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

    stax_types = dict(config.get("stax_type", {}))

    fetch_cards = args.fetch or args.fetch_from_scratch
    if fetch_cards:
        print("Fetching card information…")
        get_cards_information(
            str(paths["image_folder"]),
            str(paths["data_file"]),
            str(paths["card_list"]),
            stax_types,
            from_scratch=args.fetch_from_scratch,
            download_images=not args.no_download_images,
        )

    print("Generating LaTeX snippets…")
    generate_latex_text(
        data_file_name=str(paths["data_file"]),
        latex_text_name=str(paths["latex_text"]),
        config_path=str(config_path),
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
