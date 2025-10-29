"""Fetch card information from Scryfall and persist it to the local JSON store."""

from __future__ import annotations

import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple
from urllib.parse import urlparse

import requests

from allthatstax.card_store import CardFaceRecord, CardRecord, CardStore, load_card_store

REQUEST_TIMEOUT = 20
SCRYFALL_ROOT = "https://api.scryfall.com"
IMAGE_VARIANTS = ("png", "large", "normal")

__all__ = ["get_cards_information"]


@dataclass
class CardListEntry:
    name: str
    set_code: str
    collector_number: str
    tags: List[str]


class CardFetchError(RuntimeError):
    """Raised when a card cannot be retrieved from Scryfall."""

    def __init__(self, message: str, entry: CardListEntry):
        super().__init__(message)
        self.entry = entry


def _slugify(text: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9]+", "-", text).strip("-")
    return cleaned.lower() or "card"


def _normalise_set_code(value: str) -> str:
    return value.strip().lower()


def _parse_card_list(card_list_path: Path) -> List[CardListEntry]:
    if not card_list_path.exists():
        raise FileNotFoundError(f"Card list not found: {card_list_path}")

    pattern = re.compile(r"^\s*\d+\s+(.+?)\s+\(([^)]+)\)\s+([^\s#]+)\s*(.*)$")
    entries: List[CardListEntry] = []

    with card_list_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            stripped = line.strip()
            if not stripped:
                continue
            match = pattern.match(stripped)
            if not match:
                continue
            name = match.group(1).strip()
            set_code = match.group(2).strip()
            collector_number = match.group(3).strip()
            tag_blob = match.group(4) or ""
            tags = [token.strip() for token in tag_blob.split("#") if token.strip()]
            entries.append(
                CardListEntry(
                    name=name,
                    set_code=set_code,
                    collector_number=collector_number,
                    tags=tags,
                )
            )
    return entries


def _build_image_name(entry: CardListEntry, face_name: str, suffix: str) -> str:
    slug = _slugify(face_name or entry.name)
    set_code = entry.set_code.lower()
    collector = entry.collector_number.lower().replace("/", "-")
    return f"{set_code}-{collector}-{slug}{suffix}"


def _download_image(
    session: requests.Session,
    image_url: str,
    destination: Path,
    entry: CardListEntry,
    face_name: str,
    face_index: int,
) -> str:
    destination.mkdir(parents=True, exist_ok=True)
    parsed = urlparse(image_url)
    ext = ".png"
    if parsed.path:
        tail = Path(parsed.path).suffix
        if tail:
            ext = tail
    suffix = "" if face_index == 0 else f"-face{face_index+1}"
    file_name = _build_image_name(entry, face_name, suffix) + ext
    file_path = destination / file_name

    response = session.get(image_url, timeout=REQUEST_TIMEOUT)
    if response.status_code != 200:
        raise CardFetchError(
            f"Failed to download image ({response.status_code}): {image_url}", entry
        )
    file_path.write_bytes(response.content)
    return file_name


def _select_image_uri(card_payload: Dict[str, object], *, face_index: int = 0) -> Optional[str]:
    if "card_faces" in card_payload:
        faces = card_payload.get("card_faces") or []
        if 0 <= face_index < len(faces):
            face = faces[face_index] or {}
            image_map = face.get("image_uris") or {}
            for variant in IMAGE_VARIANTS:
                if variant in image_map:
                    return str(image_map[variant])
    image_map = card_payload.get("image_uris") or {}
    for variant in IMAGE_VARIANTS:
        if variant in image_map:
            return str(image_map[variant])
    return None


def _extract_face(
    card_payload: Dict[str, object],
    entry: CardListEntry,
    session: requests.Session,
    images_dir: Path,
    face_index: int,
    download_images: bool,
) -> Tuple[CardFaceRecord, Optional[str]]:
    if "card_faces" in card_payload:
        faces = card_payload.get("card_faces") or []
        face_payload = faces[face_index] if face_index < len(faces) else {}
    else:
        face_payload = card_payload

    english_name = str(face_payload.get("name") or card_payload.get("name") or "")
    mana_cost = str(face_payload.get("mana_cost") or card_payload.get("mana_cost") or "")
    card_type = str(face_payload.get("type_line") or card_payload.get("type_line") or "")
    oracle_text = str(
        face_payload.get("oracle_text") or card_payload.get("oracle_text") or ""
    )

    image_uri = _select_image_uri(card_payload, face_index=face_index)
    image_file = None

    if download_images and image_uri:
        image_file = _download_image(
            session,
            image_uri,
            images_dir,
            entry,
            english_name,
            face_index,
        )

    face_record = CardFaceRecord(
        english_name=english_name,
        chinese_name=english_name,
        image_file=image_file or "",
        mana_cost=mana_cost,
        card_type=card_type,
        description=oracle_text,
    )
    return face_record, image_file


def _determine_sort_type(card_type: str, *, default: str = "其他") -> str:
    mapping = {
        "creature": "生物",
        "artifact": "神器",
        "enchantment": "结界",
    }
    lowered = card_type.lower()
    for key, label in mapping.items():
        if key in lowered:
            return label
    return default


def _resolve_stax_key(tags: Iterable[str], stax_type_dict: Dict[str, str]) -> Optional[str]:
    for tag in tags:
        if tag in stax_type_dict:
            return tag
    return None


def _fetch_card_payload(session: requests.Session, entry: CardListEntry) -> Dict[str, object]:
    set_code = _normalise_set_code(entry.set_code)
    collector = entry.collector_number.lower()
    url = f"{SCRYFALL_ROOT}/cards/{set_code}/{collector}"
    response = session.get(url, timeout=REQUEST_TIMEOUT)
    if response.status_code == 200:
        return response.json()
    if response.status_code == 404:
        query = {
            "exact": entry.name,
            "set": set_code,
        }
        response = session.get(
            f"{SCRYFALL_ROOT}/cards/named", params=query, timeout=REQUEST_TIMEOUT
        )
        if response.status_code == 200:
            return response.json()
    raise CardFetchError(
        f"Failed to fetch card data ({response.status_code})", entry
    )


def _build_card_record(
    payload: Dict[str, object],
    entry: CardListEntry,
    stax_type_dict: Dict[str, str],
    images_dir: Path,
    session: requests.Session,
    download_images: bool,
) -> Tuple[CardRecord, int]:
    faces: List[CardFaceRecord] = []
    downloads = 0
    face_count = len(payload.get("card_faces") or [])
    if face_count:
        for index in range(face_count):
            face, image_name = _extract_face(
                payload,
                entry,
                session,
                images_dir,
                index,
                download_images,
            )
            faces.append(face)
            if image_name:
                downloads += 1
    else:
        face, image_name = _extract_face(
            payload,
            entry,
            session,
            images_dir,
            0,
            download_images,
        )
        faces.append(face)
        if image_name:
            downloads += 1

    stax_key = _resolve_stax_key(entry.tags, stax_type_dict)
    mana_raw = payload.get("cmc")
    mana_value = float(mana_raw) if mana_raw is not None else 0
    mana_value_int = int(round(mana_value))
    card_type = faces[0].card_type if faces else str(payload.get("type_line") or "")

    card_id = "-".join(
        filter(
            None,
            [
                entry.set_code.lower(),
                entry.collector_number.lower().replace("/", "-"),
                _slugify(payload.get("name", "")),
            ],
        )
    )

    record = CardRecord(
        id=card_id,
        kind="multiface" if len(faces) > 1 else "single",
        faces=faces,
        stax_type=stax_key,
        is_restricted=bool(payload.get("reserved", False)),
        legalities={
            str(key): str(value)
            for key, value in (payload.get("legalities") or {}).items()
        },
        mana_value=mana_value_int,
        sort_card_type=_determine_sort_type(card_type),
        set_code=entry.set_code,
        collector_number=entry.collector_number,
        tags=list(entry.tags),
    )
    return record, downloads


def get_cards_information(
    image_folder_name: str,
    data_file_name: str,
    card_list_name: str,
    stax_type_dict: Dict[str, str],
    *,
    from_scratch: bool = False,
    download_images: bool = True,
) -> Dict[str, object]:
    """Fetch cards defined in ``card_list_name`` and persist them to JSON."""

    images_dir = Path(image_folder_name)
    data_path = Path(data_file_name)
    card_list_path = Path(card_list_name)

    entries = _parse_card_list(card_list_path)
    if not entries:
        raise ValueError("Card list is empty or could not be parsed")

    if from_scratch:
        store = CardStore()
    else:
        store = load_card_store(data_path)

    session = requests.Session()
    session.headers.setdefault("User-Agent", "AllThatStax/1.0 (+https://github.com)")

    updated = 0
    downloaded_images = 0
    errors: List[str] = []
    start_time = time.time()

    for entry in entries:
        try:
            payload = _fetch_card_payload(session, entry)
            card_record, downloads = _build_card_record(
                payload,
                entry,
                stax_type_dict,
                images_dir,
                session,
                download_images,
            )
        except CardFetchError as exc:
            errors.append(f"{entry.name} ({entry.set_code}) - {exc}")
            continue
        except requests.RequestException as exc:
            errors.append(f"{entry.name} ({entry.set_code}) - network error: {exc}")
            continue

        store.upsert(card_record)
        updated += 1
        downloaded_images += downloads
        time.sleep(0.05)

    save_path = data_path
    store.save(save_path)

    duration = time.time() - start_time
    return {
        "cardsProcessed": len(entries),
        "cardsUpdated": updated,
        "imagesDownloaded": downloaded_images,
        "errors": errors,
        "dataFile": str(save_path),
        "duration": duration,
    }
