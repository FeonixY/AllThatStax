"""Utility for fetching card data from Moxfield, Scryfall and MTGCH.

This module downloads a deck list from Moxfield, collects detailed card
information from Scryfall (English) and mtgch.com (Chinese), stores the
information locally as JSON and saves the earliest printing card image.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from dataclasses import dataclass, asdict
from html.parser import HTMLParser
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urljoin
from urllib.request import Request, urlopen


USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)
DEFAULT_SLEEP_SECONDS = 0.2


class CardListError(RuntimeError):
    """Base error for card list operations."""


class HTTPRequestError(CardListError):
    """Raised when an HTTP request fails."""


@dataclass
class CardPrint:
    set_code: str
    set_name: str
    released_at: str
    image_path: str


@dataclass
class CardEnglishInfo:
    name: str
    type_line: str
    mana_cost: str
    oracle_text: str
    print: CardPrint


@dataclass
class CardChineseInfo:
    name: str
    type_line: str
    mana_cost: str
    oracle_text: str
    set_name: str


class _HTMLTextExtractor(HTMLParser):
    """Collects text content from HTML snippets."""

    def __init__(self) -> None:
        super().__init__()
        self._parts: List[str] = []

    def handle_data(self, data: str) -> None:  # pragma: no cover - simple data collector
        self._parts.append(data)

    def handle_entityref(self, name: str) -> None:  # pragma: no cover - simple data collector
        self._parts.append(self.unescape(f"&{name};"))

    def get_text(self) -> str:
        return "".join(self._parts).strip()


class MTGCHSearchParser(HTMLParser):
    """Parses the mtgch search results page to find the first card link."""

    def __init__(self) -> None:
        super().__init__()
        self.card_href: Optional[str] = None
        self._inside_result = False

    def handle_starttag(self, tag: str, attrs: List[Tuple[str, Optional[str]]]) -> None:  # pragma: no cover - HTML parsing
        if self.card_href:
            return
        attr_dict = dict(attrs)
        if tag == "a" and attr_dict.get("href"):
            href = attr_dict["href"]
            if re.search(r"/card(s)?/", href):
                self.card_href = href
                return
        if tag in {"article", "div"} and "card" in " ".join(filter(None, attr_dict.values())):
            self._inside_result = True

    def handle_endtag(self, tag: str) -> None:  # pragma: no cover - HTML parsing
        if tag in {"article", "div"}:
            self._inside_result = False

    def handle_data(self, data: str) -> None:  # pragma: no cover
        if not self.card_href and self._inside_result:
            text = data.strip()
            if text and not text.startswith("#"):
                # If the first readable text looks like a card link we keep waiting
                pass


class MTGCHDetailParser(HTMLParser):
    """Parses the card detail page for Chinese metadata."""

    FIELD_LABELS = {
        "name": ("中文名", "中文名称", "名称", "卡名"),
        "type": ("类别", "类型", "卡牌类型"),
        "mana": ("法术力费用", "费用"),
        "text": ("卡牌叙述", "规则叙述", "叙述"),
        "set": ("系列", "扩充系列", "系列名称"),
    }

    def __init__(self) -> None:
        super().__init__()
        self.current_label: Optional[str] = None
        self._capture_text = False
        self._buffer = _HTMLTextExtractor()
        self.values: Dict[str, str] = {}

    def handle_starttag(self, tag: str, attrs: List[Tuple[str, Optional[str]]]) -> None:  # pragma: no cover - HTML parsing
        if tag in {"h1", "h2", "h3", "h4", "th", "dt", "span", "div"}:
            attr_dict = dict(attrs)
            class_text = attr_dict.get("class", "")
            data_field = attr_dict.get("data-field")
            if data_field:
                key = data_field.lower()
                if key in {"zh-name", "name-zh", "cn-name"}:
                    self.current_label = "name"
                    self._start_capture()
                    return
                if key in {"type", "type-line"}:
                    self.current_label = "type"
                    self._start_capture()
                    return
                if key in {"mana", "mana-cost"}:
                    self.current_label = "mana"
                    self._start_capture()
                    return
                if key in {"oracle", "text", "rules"}:
                    self.current_label = "text"
                    self._start_capture()
                    return
                if key in {"set", "set-name"}:
                    self.current_label = "set"
                    self._start_capture()
                    return

            if any(label in class_text for label in ("card-name-zh", "name-zh", "chinese-name")):
                self.current_label = "name"
                self._start_capture()
                return
            if any(label in class_text for label in ("card-type", "type-line")):
                self.current_label = "type"
                self._start_capture()
                return
            if any(label in class_text for label in ("mana-cost", "card-mana")):
                self.current_label = "mana"
                self._start_capture()
                return
            if any(label in class_text for label in ("card-text", "oracle-text")):
                self.current_label = "text"
                self._start_capture()
                return
            if any(label in class_text for label in ("set-name", "set-info")):
                self.current_label = "set"
                self._start_capture()
                return

        if tag in {"td", "dd", "span", "div"} and self.current_label and not self._capture_text:
            # Some layouts put <th>Label</th><td>Value</td>
            self._capture_text = True

    def handle_endtag(self, tag: str) -> None:  # pragma: no cover - HTML parsing
        if self._capture_text and tag in {"td", "dd", "span", "div", "h1", "h2", "h3", "h4"}:
            text = self._buffer.get_text()
            if self.current_label and text:
                self.values.setdefault(self.current_label, text)
            self._capture_text = False
            self.current_label = None
            self._buffer = _HTMLTextExtractor()

    def handle_data(self, data: str) -> None:  # pragma: no cover - HTML parsing
        if self._capture_text:
            self._buffer.handle_data(data)
        else:
            stripped = data.strip()
            if stripped:
                for key, labels in self.FIELD_LABELS.items():
                    if stripped in labels:
                        self.current_label = key
                        self._capture_text = True
                        self._buffer = _HTMLTextExtractor()
                        return

    def handle_entityref(self, name: str) -> None:  # pragma: no cover
        if self._capture_text:
            self._buffer.handle_entityref(name)

    def _start_capture(self) -> None:
        self._capture_text = True
        self._buffer = _HTMLTextExtractor()


class CardListManager:
    """High level interface for fetching and storing card information."""

    def __init__(
        self,
        deck_id: str,
        output_path: Path,
        image_dir: Path,
        pause: float = DEFAULT_SLEEP_SECONDS,
        *,
        overwrite: bool = True,
    ) -> None:
        self.deck_id = deck_id
        self.output_path = output_path
        self.image_dir = image_dir
        self.pause = pause
        self.overwrite = overwrite
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        self.image_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def run(self) -> Dict[str, object]:
        deck_cards = self._fetch_moxfield_cards()
        aggregated: List[Dict[str, object]] = []

        for entry in deck_cards:
            time.sleep(self.pause)
            english_info = self._fetch_scryfall_info(entry["name"])
            chinese_info = None
            try:
                chinese_info = self._fetch_mtgch_info(entry["name"])
            except CardListError:
                # mtgch is occasionally missing some cards; we allow missing info
                chinese_info = None

            aggregated.append(
                {
                    "quantity": entry["quantity"],
                    "tags": entry["tags"],
                    "english": asdict(english_info),
                    "chinese": asdict(chinese_info) if chinese_info else None,
                }
            )

        payload = {
            "deckId": self.deck_id,
            "source": f"https://moxfield.com/decks/{self.deck_id}",
            "fetchedAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "cards": aggregated,
        }

        with self.output_path.open("w", encoding="utf-8") as fh:
            json.dump(payload, fh, ensure_ascii=False, indent=2)

        return payload

    # ------------------------------------------------------------------
    # Network helpers
    # ------------------------------------------------------------------
    def _http_get(self, url: str, *, expect_json: bool = False) -> str | Dict[str, object]:
        request = Request(url, headers={"User-Agent": USER_AGENT})
        try:
            with urlopen(request, timeout=30) as response:
                body = response.read()
        except (HTTPError, URLError) as exc:  # pragma: no cover - network errors
            raise HTTPRequestError(f"Failed to fetch {url}: {exc}") from exc
        if expect_json:
            try:
                return json.loads(body.decode("utf-8"))
            except json.JSONDecodeError as exc:  # pragma: no cover - data issues
                raise CardListError(f"Invalid JSON response from {url}: {exc}") from exc
        return body.decode("utf-8", errors="replace")

    # ------------------------------------------------------------------
    # Data fetching
    # ------------------------------------------------------------------
    def _fetch_moxfield_cards(self) -> List[Dict[str, object]]:
        url = f"https://api.moxfield.com/v2/decks/all/{self.deck_id}"
        data = self._http_get(url, expect_json=True)
        cards: Dict[str, Dict[str, object]] = {}

        def _iter_cards(board: Dict[str, object]) -> Iterable[Dict[str, object]]:
            if not isinstance(board, dict):
                return []
            cards_obj = board.get("cards") or board.get("cardList")
            if isinstance(cards_obj, dict):
                return cards_obj.values()
            if isinstance(cards_obj, list):
                return cards_obj
            return []

        def _consume_board(board: Dict[str, object]) -> None:
            for item in _iter_cards(board):
                oracle = (
                    item.get("card")
                    or item.get("oracleCard")
                    or item.get("oracleCardData")
                    or item
                )
                name = oracle.get("name") if isinstance(oracle, dict) else None
                if not name:
                    continue
                tags = item.get("tags") or []
                if isinstance(tags, dict):
                    tags = list(tags.values())
                elif isinstance(tags, str):
                    tags = [tags]
                entry = cards.setdefault(
                    name,
                    {"name": name, "quantity": 0, "tags": []},
                )
                entry["quantity"] += int(item.get("quantity", 1))
                entry["tags"] = sorted(set(entry["tags"]) | set(tags))

        _consume_board(data.get("mainboard", {}))
        _consume_board(data.get("sideboard", {}))
        _consume_board(data.get("maybeboard", {}))

        if not cards:
            raise CardListError(f"No cards found in deck {self.deck_id}")

        return sorted(cards.values(), key=lambda entry: entry["name"].lower())

    def _fetch_scryfall_info(self, card_name: str) -> CardEnglishInfo:
        query_url = "https://api.scryfall.com/cards/named?" + urlencode({"exact": card_name})
        data = self._http_get(query_url, expect_json=True)
        if not isinstance(data, dict) or data.get("object") == "error":
            raise CardListError(f"Card '{card_name}' not found on Scryfall")

        prints_url = data.get("prints_search_uri")
        if not prints_url:
            raise CardListError(f"No print information for {card_name}")
        if "order=" not in prints_url:
            separator = "&" if "?" in prints_url else "?"
            prints_url = f"{prints_url}{separator}order=released&dir=asc"
        else:
            # ensure ascending order
            if "dir=" not in prints_url:
                prints_url += "&dir=asc"
        prints_data = self._http_get(prints_url, expect_json=True)
        if not isinstance(prints_data, dict) or not prints_data.get("data"):
            raise CardListError(f"Failed to load prints for {card_name}")
        earliest = prints_data["data"][0]

        def _extract_field(card: Dict[str, object], key: str) -> str:
            value = card.get(key, "")
            if isinstance(value, str):
                return value
            return ""

        english_name = _extract_field(earliest, "name") or card_name
        type_line = _extract_field(earliest, "type_line")
        mana_cost = _extract_field(earliest, "mana_cost")
        oracle_text = _extract_field(earliest, "oracle_text")

        if "card_faces" in earliest and earliest["card_faces"]:
            faces = earliest["card_faces"]
            type_line = " // ".join(filter(None, (face.get("type_line", "") for face in faces)))
            mana_cost = " // ".join(filter(None, (face.get("mana_cost", "") for face in faces)))
            oracle_text = "\n//\n".join(filter(None, (face.get("oracle_text", "") for face in faces)))
        image_uri = self._select_image_uri(earliest)
        image_path = self._download_image(english_name, earliest.get("set"), image_uri)

        print_info = CardPrint(
            set_code=_extract_field(earliest, "set"),
            set_name=_extract_field(earliest, "set_name"),
            released_at=_extract_field(earliest, "released_at"),
            image_path=image_path,
        )

        return CardEnglishInfo(
            name=english_name,
            type_line=type_line,
            mana_cost=mana_cost,
            oracle_text=oracle_text,
            print=print_info,
        )

    def _select_image_uri(self, card: Dict[str, object]) -> Optional[str]:
        if "image_uris" in card and isinstance(card["image_uris"], dict):
            for key in ("png", "large", "normal"):
                if card["image_uris"].get(key):
                    return card["image_uris"][key]
        if "card_faces" in card and card["card_faces"]:
            for face in card["card_faces"]:
                image_uris = face.get("image_uris")
                if isinstance(image_uris, dict):
                    for key in ("png", "large", "normal"):
                        if image_uris.get(key):
                            return image_uris[key]
        return None

    def _sanitize_filename(self, value: str) -> str:
        value = re.sub(r"[^A-Za-z0-9._-]+", "_", value)
        value = re.sub(r"_+", "_", value)
        return value.strip("_") or "card_image"

    def _download_image(self, card_name: str, set_code: Optional[str], image_url: Optional[str]) -> str:
        if not image_url:
            return ""
        filename_parts = [card_name]
        if set_code:
            filename_parts.append(set_code)
        filename = self._sanitize_filename("-".join(filename_parts)) + ".png"
        destination = self.image_dir / filename
        if destination.exists() and not self.overwrite:
            return str(destination)
        request = Request(image_url, headers={"User-Agent": USER_AGENT})
        try:
            with urlopen(request, timeout=60) as response:
                data = response.read()
        except (HTTPError, URLError) as exc:  # pragma: no cover - network errors
            raise HTTPRequestError(f"Failed to download image {image_url}: {exc}") from exc
        with destination.open("wb") as fh:
            fh.write(data)
        return str(destination)

    def _fetch_mtgch_info(self, card_name: str) -> Optional[CardChineseInfo]:
        base_url = "https://www.mtgch.com/"
        search_url = urljoin(base_url, f"cards/search?{urlencode({'q': card_name})}")
        html = self._http_get(search_url)
        parser = MTGCHSearchParser()
        parser.feed(html)
        if not parser.card_href:
            # Attempt alternate search endpoint
            alt_url = urljoin(base_url, f"search?{urlencode({'q': card_name})}")
            html = self._http_get(alt_url)
            parser = MTGCHSearchParser()
            parser.feed(html)
        if not parser.card_href:
            raise CardListError(f"Card '{card_name}' not found on mtgch.com")
        detail_url = urljoin(base_url, parser.card_href.lstrip("/"))
        detail_html = self._http_get(detail_url)
        detail_parser = MTGCHDetailParser()
        detail_parser.feed(detail_html)
        values = detail_parser.values
        if not values:
            raise CardListError(f"Unable to parse mtgch data for '{card_name}'")
        return CardChineseInfo(
            name=values.get("name", card_name),
            type_line=values.get("type", ""),
            mana_cost=values.get("mana", ""),
            oracle_text=values.get("text", ""),
            set_name=values.get("set", ""),
        )


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Fetch card information for a Moxfield deck")
    parser.add_argument("deck_id", help="Moxfield deck identifier")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/card_data.json"),
        help="Path to the output JSON file",
    )
    parser.add_argument(
        "--image-dir",
        type=Path,
        default=Path("data/images"),
        help="Directory for storing downloaded card images",
    )
    parser.add_argument(
        "--pause",
        type=float,
        default=DEFAULT_SLEEP_SECONDS,
        help="Pause between requests to avoid overwhelming the services",
    )
    parser.add_argument(
        "--keep-existing",
        action="store_true",
        help="Do not re-download images that already exist",
    )
    return parser


def main(argv: Optional[Iterable[str]] = None) -> int:
    parser = build_argument_parser()
    args = parser.parse_args(argv)

    manager = CardListManager(
        deck_id=args.deck_id,
        output_path=args.output,
        image_dir=args.image_dir,
        pause=args.pause,
        overwrite=not args.keep_existing,
    )

    try:
        manager.run()
    except CardListError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    raise SystemExit(main())
