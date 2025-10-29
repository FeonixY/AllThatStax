"""Utilities for working with card legality information."""

from __future__ import annotations

from typing import Dict, Iterable, Mapping, Sequence

__all__ = ["LEGALITY_ORDER", "extract_legalities"]


#: The canonical ordering of legality entries the application cares about.
LEGALITY_ORDER: Sequence[str] = (
    "standard",
    "pioneer",
    "modern",
    "legacy",
    "pauper",
    "vintage",
    "commander",
    "duel_commander",
)


def _normalise_key(value: str) -> str:
    return value.strip().lower()


def _candidate_source_keys(target: str) -> Iterable[str]:
    """Yield possible source keys for a canonical legality entry.

    Scryfall uses ``"duel"`` for the Duel Commander legality, while the
    application historically refers to the format as ``"duel_commander"``.
    Rather than hard-coding a manual mapping, we derive aliases based on common
    naming conventions so new formats following the same pattern automatically
    work.
    """

    yield target
    # Treat ``foo_commander`` as a potential alias of ``foo`` because Scryfall
    # omits the suffix for Duel Commander.
    if target.endswith("_commander"):
        yield target[: -len("_commander")]


def extract_legalities(raw: Mapping[str, object]) -> Dict[str, str]:
    """Normalise Scryfall legality data into the canonical format order."""

    if not raw:
        return {}

    normalised = {}
    for key, value in raw.items():
        normalised_key = _normalise_key(str(key))
        if normalised_key not in normalised:
            normalised[normalised_key] = str(value)

    cleaned: Dict[str, str] = {}
    for target in LEGALITY_ORDER:
        for candidate in _candidate_source_keys(target):
            normalised_key = _normalise_key(candidate)
            if normalised_key in normalised:
                cleaned[target] = normalised[normalised_key]
                break
    return cleaned

