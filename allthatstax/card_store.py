"""Utilities for reading and writing the project card data store."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterator, List, Optional
import json
import time

EXCLUDED_LEGALITY_FORMATS = {"alchemy", "historic", "explorer", "timeless", "brawl"}

__all__ = [
    "CardFaceRecord",
    "CardRecord",
    "CardStore",
    "load_card_store",
    "save_card_store",
    "EXCLUDED_LEGALITY_FORMATS",
]


@dataclass
class CardFaceRecord:
    """Representation of a single face within a card entry."""

    english_name: str
    chinese_name: str
    image_file: str
    mana_cost: str
    card_type: str
    description: str

    @classmethod
    def from_dict(cls, payload: Dict[str, object]) -> "CardFaceRecord":
        return cls(
            english_name=str(payload.get("english_name", "")),
            chinese_name=str(payload.get("chinese_name", "")),
            image_file=str(payload.get("image_file", "")),
            mana_cost=str(payload.get("mana_cost", "")),
            card_type=str(payload.get("card_type", "")),
            description=str(payload.get("description", "")),
        )

    def to_dict(self) -> Dict[str, object]:
        return {
            "english_name": self.english_name,
            "chinese_name": self.chinese_name,
            "image_file": self.image_file,
            "mana_cost": self.mana_cost,
            "card_type": self.card_type,
            "description": self.description,
        }


@dataclass
class CardRecord:
    """Representation of a card entry in the data store."""

    id: str
    kind: str
    faces: List[CardFaceRecord] = field(default_factory=list)
    stax_type: Optional[str] = None
    is_restricted: bool = False
    legalities: Dict[str, str] = field(default_factory=dict)
    mana_value: float = 0
    sort_card_type: str = "其他"
    set_code: Optional[str] = None
    collector_number: Optional[str] = None
    tags: List[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, payload: Dict[str, object]) -> "CardRecord":
        faces_payload = payload.get("faces", [])
        faces = [CardFaceRecord.from_dict(face) for face in faces_payload or []]
        legalities_payload = payload.get("legalities", {})
        legalities: Dict[str, str] = {}
        if isinstance(legalities_payload, dict):
            for key, value in legalities_payload.items():
                key_str = str(key)
                if key_str.lower() in EXCLUDED_LEGALITY_FORMATS:
                    continue
                legalities[key_str] = str(value)
        return cls(
            id=str(payload.get("id", "")),
            kind=str(payload.get("kind", "single")),
            faces=faces,
            stax_type=(
                str(payload.get("stax_type")) if payload.get("stax_type") else None
            ),
            is_restricted=bool(payload.get("is_restricted", False)),
            legalities=legalities,
            mana_value=float(payload.get("mana_value", 0)),
            sort_card_type=str(payload.get("sort_card_type", "其他")),
            set_code=(
                str(payload.get("set_code")) if payload.get("set_code") else None
            ),
            collector_number=(
                str(payload.get("collector_number"))
                if payload.get("collector_number")
                else None
            ),
            tags=[str(tag) for tag in payload.get("tags", [])],
        )

    def to_dict(self) -> Dict[str, object]:
        return {
            "id": self.id,
            "kind": self.kind,
            "faces": [face.to_dict() for face in self.faces],
            "stax_type": self.stax_type,
            "is_restricted": self.is_restricted,
            "legalities": dict(self.legalities),
            "mana_value": self.mana_value,
            "sort_card_type": self.sort_card_type,
            "set_code": self.set_code,
            "collector_number": self.collector_number,
            "tags": list(self.tags),
        }


@dataclass
class CardStore:
    """Container for all card records."""

    cards: Dict[str, CardRecord] = field(default_factory=dict)
    version: int = 1
    updated_at: float = field(default_factory=lambda: time.time())

    def __iter__(self) -> Iterator[CardRecord]:
        for card in self.cards.values():
            yield card

    def upsert(self, card: CardRecord) -> None:
        self.cards[card.id] = card
        self.updated_at = time.time()

    def remove(self, card_id: str) -> None:
        if card_id in self.cards:
            del self.cards[card_id]
            self.updated_at = time.time()

    def to_dict(self) -> Dict[str, object]:
        return {
            "version": self.version,
            "updated_at": self.updated_at,
            "cards": [card.to_dict() for card in sorted(self.cards.values(), key=lambda c: c.id)],
        }

    @classmethod
    def from_dict(cls, payload: Dict[str, object]) -> "CardStore":
        cards_payload = payload.get("cards", [])
        cards: Dict[str, CardRecord] = {}
        for entry in cards_payload or []:
            card = CardRecord.from_dict(entry)
            if card.id:
                cards[card.id] = card
        version = int(payload.get("version", 1))
        updated_at = float(payload.get("updated_at", time.time()))
        return cls(cards=cards, version=version, updated_at=updated_at)

    def save(self, path: str | Path) -> None:
        save_card_store(path, self)


def load_card_store(path: str | Path) -> CardStore:
    data_path = Path(path)
    if not data_path.exists():
        return CardStore()
    with data_path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    return CardStore.from_dict(payload)


def save_card_store(path: str | Path, store: CardStore) -> None:
    data_path = Path(path)
    data_path.parent.mkdir(parents=True, exist_ok=True)
    with data_path.open("w", encoding="utf-8") as handle:
        json.dump(store.to_dict(), handle, ensure_ascii=False, indent=2)
