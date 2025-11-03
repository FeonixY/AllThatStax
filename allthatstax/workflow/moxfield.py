"""Utilities for retrieving decklists from Moxfield."""

from __future__ import annotations

import re
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, MutableMapping, Optional, Sequence
from urllib.parse import urlparse

import requests

REQUEST_TIMEOUT = 20
MOXFIELD_API_ROOT = "https://api2.moxfield.com/v2/decks/all"

__all__ = ["MoxfieldError", "DeckCard", "fetch_deck_cards", "save_deck_to_file"]


class MoxfieldError(RuntimeError):
    """Raised when a decklist cannot be retrieved from Moxfield."""


@dataclass
class DeckCard:
    quantity: int
    name: str
    set_code: str
    collector_number: str
    categories: List[str]


def _extract_deck_id(deck_identifier: str) -> str:
    """Extract the deck identifier from either a URL or a raw ID."""

    value = deck_identifier.strip()
    if not value:
        raise MoxfieldError("Moxfield 牌表链接不能为空")

    parsed = urlparse(value)
    if parsed.scheme:
        path = parsed.path.rstrip("/")
        if not path:
            raise MoxfieldError("无法从提供的链接解析牌表 ID")
        deck_id = path.split("/")[-1]
    else:
        deck_id = value

    deck_id = deck_id.strip()
    if not deck_id:
        raise MoxfieldError("无法从提供的链接解析牌表 ID")
    if not re.fullmatch(r"[A-Za-z0-9]+", deck_id):
        raise MoxfieldError("牌表 ID 格式不正确")
    return deck_id


def _request_deck_payload(deck_id: str, session: Optional[requests.Session] = None) -> Dict[str, object]:
    """Retrieve the raw deck payload from the Moxfield API."""

    if session is None:
        session = requests.Session()
    url = f"{MOXFIELD_API_ROOT}/{deck_id}"
    headers = {
        "Accept": "application/json, text/plain, */*",
        "User-Agent": "AllThatStax/1.0 (+https://github.com)",
        "Origin": "https://www.moxfield.com",
        "Referer": "https://www.moxfield.com/",
        "X-Moxfield-Platform": "web",
    }
    response = session.get(url, timeout=REQUEST_TIMEOUT, headers=headers)
    if response.status_code != 200:
        raise MoxfieldError(
            f"Moxfield 请求失败（状态码 {response.status_code}）"
        )
    try:
        payload = response.json()
    except ValueError as exc:  # pragma: no cover - defensive
        raise MoxfieldError("Moxfield 返回了无效的 JSON") from exc
    if not isinstance(payload, dict):
        raise MoxfieldError("Moxfield 返回的 JSON 结构无效")
    return payload


def _normalise_categories(raw: object) -> List[str]:
    result: List[str] = []
    if isinstance(raw, (list, tuple, set)):
        for item in raw:
            if isinstance(item, str):
                stripped = item.strip()
                if stripped:
                    result.append(stripped)
    elif isinstance(raw, str):
        stripped = raw.strip()
        if stripped:
            result.append(stripped)
    return result


def _iter_category_groups(payload: Dict[str, object]) -> Iterable[MutableMapping[str, object]]:
    custom = payload.get("customCategories")
    if not isinstance(custom, MutableMapping):
        return []

    groups: Sequence[object] = ()
    for key in ("groups", "categoryGroups", "categories"):
        value = custom.get(key)
        if isinstance(value, MutableMapping):
            groups = list(value.values())
            break
        if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
            groups = list(value)
            break
    else:
        return []

    filtered: List[MutableMapping[str, object]] = []
    for item in groups:
        if isinstance(item, MutableMapping):
            filtered.append(item)
    return filtered


def _extract_group_card_ids(group: MutableMapping[str, object]) -> List[str]:
    card_ids: List[str] = []
    for key in ("cardUuids", "cards", "entries", "slots"):
        raw = group.get(key)
        if isinstance(raw, MutableMapping):
            for value in raw.values():
                if isinstance(value, str):
                    card_ids.append(value)
                elif isinstance(value, MutableMapping):
                    for candidate_key in ("cardUuid", "boardCardId", "id", "uuid"):
                        candidate = value.get(candidate_key)
                        if isinstance(candidate, str):
                            card_ids.append(candidate)
                            break
        elif isinstance(raw, Sequence) and not isinstance(raw, (str, bytes)):
            for value in raw:
                if isinstance(value, str):
                    card_ids.append(value)
                elif isinstance(value, MutableMapping):
                    for candidate_key in ("cardUuid", "boardCardId", "id", "uuid"):
                        candidate = value.get(candidate_key)
                        if isinstance(candidate, str):
                            card_ids.append(candidate)
                            break
    return card_ids


def _build_category_map(payload: Dict[str, object]) -> Dict[str, List[str]]:
    mapping: Dict[str, List[str]] = {}
    for group in _iter_category_groups(payload):
        name = group.get("name")
        if not isinstance(name, str):
            continue
        title = name.strip()
        if not title:
            continue
        for card_id in _extract_group_card_ids(group):
            if not card_id:
                continue
            mapping.setdefault(card_id, []).append(title)
    return mapping


def _iter_mainboard_cards(payload: Dict[str, object]) -> Iterable[tuple[str, MutableMapping[str, object]]]:
    mainboard = payload.get("mainboard")
    if isinstance(mainboard, MutableMapping):
        cards = mainboard.get("cards")
        if isinstance(cards, MutableMapping):
            for key, value in cards.items():
                if isinstance(key, str) and isinstance(value, MutableMapping):
                    yield key, value
        elif isinstance(cards, Sequence):
            for item in cards:
                if isinstance(item, MutableMapping):
                    key = item.get("boardCardId")
                    if isinstance(key, str):
                        yield key, item
    return []


def fetch_deck_cards(
    deck_identifier: str,
    *,
    session: Optional[requests.Session] = None,
) -> List[DeckCard]:
    """Fetch the list of cards contained in a Moxfield deck."""

    deck_id = _extract_deck_id(deck_identifier)
    payload = _request_deck_payload(deck_id, session=session)
    category_map = _build_category_map(payload)

    cards: List[DeckCard] = []
    for key, entry in _iter_mainboard_cards(payload):
        quantity_raw = entry.get("quantity")
        try:
            quantity = int(quantity_raw) if quantity_raw is not None else 0
        except (TypeError, ValueError):
            quantity = 0
        if quantity <= 0:
            continue

        card_payload = entry.get("card")
        if not isinstance(card_payload, MutableMapping):
            continue

        name = str(card_payload.get("name") or "").strip()
        set_code = str(
            card_payload.get("setCode")
            or card_payload.get("set")
            or card_payload.get("set_id")
            or ""
        ).strip()
        collector_number = str(
            card_payload.get("collectorNumber")
            or card_payload.get("collector_number")
            or card_payload.get("number")
            or ""
        ).strip()

        if not name or not set_code or not collector_number:
            raise MoxfieldError(f"牌 {name or key} 缺少必要的信息（系列或编号）")

        categories = []
        categories.extend(_normalise_categories(entry.get("categories")))
        categories.extend(_normalise_categories(entry.get("tags")))
        card_key = str(entry.get("boardCardId") or entry.get("uuid") or key or "")
        if card_key and card_key in category_map:
            categories.extend(category_map[card_key])

        # Remove duplicates while preserving order.
        seen: set[str] = set()
        unique_categories: List[str] = []
        for category in categories:
            if category not in seen:
                seen.add(category)
                unique_categories.append(category)

        cards.append(
            DeckCard(
                quantity=quantity,
                name=name,
                set_code=set_code.upper(),
                collector_number=collector_number,
                categories=unique_categories,
            )
        )

    if not cards:
        raise MoxfieldError("未能在 Moxfield 牌表中找到主牌信息")

    return cards


def save_deck_to_file(
    deck_identifier: str,
    destination: Path,
    *,
    session: Optional[requests.Session] = None,
) -> tuple[int, Path]:
    """Fetch a Moxfield deck and persist it to ``destination`` as JSON."""

    deck_id = _extract_deck_id(deck_identifier)
    cards = fetch_deck_cards(deck_id, session=session)
    destination = destination.resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)

    total_cards = 0
    payload_cards: List[Dict[str, object]] = []
    for card in cards:
        total_cards += max(card.quantity, 0)
        payload_cards.append(
            {
                "quantity": card.quantity,
                "name": card.name,
                "setCode": card.set_code,
                "collectorNumber": card.collector_number,
                "lockTypes": list(card.categories),
            }
        )

    payload: Dict[str, object] = {
        "source": "moxfield",
        "deckId": deck_id,
        "cards": payload_cards,
    }

    destination.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return total_cards, destination
