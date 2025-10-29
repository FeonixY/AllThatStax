"""Utilities for fetching Chinese card information from mtgch.com.

The mtgch.com service exposes an HTTP API (see ``https://mtgch.com/api/v1``)
that serves JSON payloads for card data.  The exact schema has changed a few
times historically and in some cases the API might not include the desired
fields for certain cards.  This module therefore tries to be resilient by
probing a handful of likely endpoints and falling back to a lightweight HTML
scraper when the API cannot be reached or does not contain the expected data.

Only a very small subset of the information exposed by mtgch is required by
the AllThatStax project: the Chinese card name, type line and oracle text for
each card face.  Images continue to be sourced from Scryfall so the scraper
never downloads any artwork from mtgch.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from html.parser import HTMLParser
from typing import Iterable, Iterator, List, MutableMapping, Optional, Sequence
from urllib.parse import urljoin

import requests

__all__ = [
    "ChineseCardFace",
    "ChineseCardInfo",
    "MTGCHClient",
    "MTGCHError",
]


LOGGER = logging.getLogger(__name__)

MTGCH_API_ROOT = "https://mtgch.com/api/v1"
MTGCH_WEB_ROOT = "https://www.mtgch.com/"
DEFAULT_TIMEOUT = 20


class MTGCHError(RuntimeError):
    """Raised when the mtgch service cannot be queried."""


@dataclass
class ChineseCardFace:
    """Chinese details for a single card face."""

    name: Optional[str] = None
    type_line: Optional[str] = None
    oracle_text: Optional[str] = None


@dataclass
class ChineseCardInfo:
    """Chinese details for a multi-faced card."""

    faces: List[ChineseCardFace]
    set_name: Optional[str] = None


def _contains_cjk(text: str) -> bool:
    """Return ``True`` if *text* contains CJK characters."""

    return bool(re.search(r"[\u3400-\u9fff]", text))


def _clean_text(value: object) -> Optional[str]:
    if isinstance(value, str):
        cleaned = value.strip()
        return cleaned or None
    return None


def _flatten_strings(value: object) -> List[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, MutableMapping):
        result: List[str] = []
        for item in value.values():
            result.extend(_flatten_strings(item))
        return result
    if isinstance(value, Iterable):
        result = []
        for item in value:
            result.extend(_flatten_strings(item))
        return result
    return []


def _collect_strings(payload: object, tokens: Sequence[str]) -> List[str]:
    lowered_tokens = [token.lower() for token in tokens]

    def _matches(key: str) -> bool:
        return any(token in key for token in lowered_tokens)

    results: List[str] = []
    if isinstance(payload, MutableMapping):
        for key, value in payload.items():
            key_lower = str(key).lower()
            if _matches(key_lower):
                results.extend(_flatten_strings(value))
            else:
                results.extend(_collect_strings(value, tokens))
    elif isinstance(payload, Iterable) and not isinstance(payload, (str, bytes)):
        for item in payload:
            results.extend(_collect_strings(item, tokens))
    return results


def _iter_candidates(payload: object) -> Iterator[MutableMapping[str, object]]:
    if isinstance(payload, MutableMapping):
        yield payload
        for value in payload.values():
            yield from _iter_candidates(value)
    elif isinstance(payload, Iterable) and not isinstance(payload, (str, bytes)):
        for item in payload:
            yield from _iter_candidates(item)


def _extract_faces(payload: MutableMapping[str, object]) -> List[MutableMapping[str, object]]:
    for key in ("faces", "card_faces", "cardFaces"):
        value = payload.get(key)
        if isinstance(value, list):
            return [face for face in value if isinstance(face, MutableMapping)]
    return [payload]


def _pick_value(
    payload: MutableMapping[str, object],
    *,
    tokens: Sequence[str],
    prefer_chinese: bool = True,
    fallback_tokens: Sequence[str] | None = None,
) -> Optional[str]:
    values = [_clean_text(item) for item in _collect_strings(payload, tokens)]
    values = [item for item in values if item]
    if prefer_chinese:
        for item in values:
            if _contains_cjk(item):
                return item
    if values:
        return values[0]
    if fallback_tokens:
        return _pick_value(payload, tokens=fallback_tokens, prefer_chinese=False)
    return None


def _build_from_candidate(
    candidate: MutableMapping[str, object],
    face_hints: Sequence[str],
) -> Optional[ChineseCardInfo]:
    faces_payload = _extract_faces(candidate)
    faces: List[ChineseCardFace] = []
    for index, face_payload in enumerate(faces_payload):
        name_tokens = [
            "printed_name",
            "name_zh",
            "zh_name",
            "name_cn",
            "chinese_name",
            "name",
        ]
        type_tokens = [
            "printed_type",
            "printed_type_line",
            "type_line_zh",
            "type_zh",
            "type",
        ]
        text_tokens = [
            "printed_text",
            "oracle_text_zh",
            "text_zh",
            "oracle_text",
            "text",
        ]

        name = _pick_value(face_payload, tokens=name_tokens)
        if not name and index < len(face_hints):
            # Some payloads group all translations at the card level. Try again
            # with the parent payload using the English face name as a hint.
            english_hint = face_hints[index]
            if english_hint:
                name = _pick_value(
                    candidate,
                    tokens=[english_hint],
                    prefer_chinese=True,
                )

        type_line = _pick_value(face_payload, tokens=type_tokens)
        oracle_text = _pick_value(face_payload, tokens=text_tokens)

        faces.append(
            ChineseCardFace(
                name=name,
                type_line=type_line,
                oracle_text=oracle_text,
            )
        )

    set_name = _pick_value(
        candidate,
        tokens=["set_name", "set", "set_cn", "set_zh", "expansion"],
        prefer_chinese=True,
    )

    if any(face.name or face.type_line or face.oracle_text for face in faces):
        return ChineseCardInfo(faces=faces, set_name=set_name)
    return None


class _HTMLTextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._parts: List[str] = []

    def handle_data(self, data: str) -> None:  # pragma: no cover - HTML parsing
        self._parts.append(data)

    def handle_entityref(self, name: str) -> None:  # pragma: no cover - HTML parsing
        self._parts.append(self.unescape(f"&{name};"))

    def get_text(self) -> str:
        return "".join(self._parts).strip()


class _MTGCHSearchParser(HTMLParser):
    """Parses the mtgch search result page."""

    def __init__(self) -> None:
        super().__init__()
        self.card_href: Optional[str] = None

    def handle_starttag(self, tag: str, attrs: List[tuple[str, Optional[str]]]) -> None:  # pragma: no cover - HTML parsing
        if tag != "a" or self.card_href:
            return
        attr_dict = dict(attrs)
        href = attr_dict.get("href")
        if href and re.search(r"/card(s)?/", href):
            self.card_href = href


class _MTGCHDetailParser(HTMLParser):
    """Extracts Chinese metadata from a card detail page."""

    FIELD_LABELS = {
        "name": ("中文名", "中文名称", "名称", "卡名"),
        "type": ("类别", "类型", "卡牌类型"),
        "text": ("卡牌叙述", "规则叙述", "叙述"),
        "set": ("系列", "扩充系列", "系列名称"),
    }

    def __init__(self) -> None:
        super().__init__()
        self.current_label: Optional[str] = None
        self._capture_text = False
        self._buffer = _HTMLTextExtractor()
        self.values: dict[str, str] = {}

    def handle_starttag(self, tag: str, attrs: List[tuple[str, Optional[str]]]) -> None:  # pragma: no cover - HTML parsing
        attr_dict = dict(attrs)
        data_field = (attr_dict.get("data-field") or "").lower()
        class_text = (attr_dict.get("class") or "").lower()
        if data_field:
            if data_field in {"zh-name", "name-zh", "cn-name"}:
                self.current_label = "name"
            elif data_field in {"type", "type-line"}:
                self.current_label = "type"
            elif data_field in {"oracle", "text", "rules"}:
                self.current_label = "text"
            elif data_field in {"set", "set-name"}:
                self.current_label = "set"
        elif any(token in class_text for token in ("card-name-zh", "name-zh", "chinese-name")):
            self.current_label = "name"
        elif any(token in class_text for token in ("card-type", "type-line")):
            self.current_label = "type"
        elif any(token in class_text for token in ("card-text", "oracle-text")):
            self.current_label = "text"
        elif any(token in class_text for token in ("set-name", "set-info")):
            self.current_label = "set"

        if self.current_label and tag in {"div", "span", "td", "dd", "h1", "h2", "h3", "h4"}:
            self._capture_text = True

    def handle_endtag(self, tag: str) -> None:  # pragma: no cover - HTML parsing
        if self._capture_text and tag in {"div", "span", "td", "dd", "h1", "h2", "h3", "h4"}:
            text = self._buffer.get_text()
            if self.current_label and text:
                self.values.setdefault(self.current_label, text)
            self._capture_text = False
            self.current_label = None
            self._buffer = _HTMLTextExtractor()

    def handle_data(self, data: str) -> None:  # pragma: no cover - HTML parsing
        if self._capture_text:
            self._buffer.handle_data(data)
            return
        stripped = data.strip()
        if not stripped:
            return
        for key, labels in self.FIELD_LABELS.items():
            if stripped in labels:
                self.current_label = key
                self._capture_text = True
                return


class MTGCHClient:
    """High level helper used by the card crawler."""

    def __init__(self, session: Optional[requests.Session] = None) -> None:
        self.session = session or requests.Session()

    # ------------------------------------------------------------------ API --
    def fetch_chinese_info(
        self,
        *,
        english_name: str,
        set_code: str,
        collector_number: str,
        face_names: Sequence[str],
    ) -> Optional[ChineseCardInfo]:
        """Fetch Chinese card information using the mtgch API."""

        api_result = self._fetch_via_api(
            english_name=english_name,
            set_code=set_code,
            collector_number=collector_number,
            face_names=face_names,
        )
        if api_result:
            return api_result

        return self._fetch_via_html(
            english_name=english_name,
            face_names=face_names,
        )

    # ----------------------------------------------------------------- API --
    def _fetch_via_api(
        self,
        *,
        english_name: str,
        set_code: str,
        collector_number: str,
        face_names: Sequence[str],
    ) -> Optional[ChineseCardInfo]:
        normalised_set = set_code.strip().lower()
        collector = collector_number.strip().lower()

        attempts: List[tuple[str, str, dict[str, str] | None]] = []
        if normalised_set and collector:
            attempts.extend(
                [
                    ("GET", f"cards/{normalised_set}/{collector}", None),
                    ("GET", f"cards/sets/{normalised_set}/{collector}", None),
                ]
            )
        attempts.extend(
            [
                ("GET", "cards/search", {"q": english_name}),
                ("GET", "cards", {"search": english_name}),
                ("GET", "cards/named", {"exact": english_name}),
            ]
        )

        for method, path, params in attempts:
            try:
                payload = self._request(method, path, params=params)
            except MTGCHError as exc:
                LOGGER.debug("mtgch API request failed (%s %s): %s", method, path, exc)
                continue
            if payload is None:
                continue
            for candidate in _iter_candidates(payload):
                if not isinstance(candidate, MutableMapping):
                    continue
                lang = str(candidate.get("lang") or candidate.get("language") or "").lower()
                if lang and not lang.startswith("zh"):
                    continue
                info = _build_from_candidate(candidate, face_names)
                if info:
                    return info
        return None

    def _request(
        self,
        method: str,
        path: str,
        *,
        params: Optional[dict[str, str]] = None,
    ) -> Optional[object]:
        url = f"{MTGCH_API_ROOT}/{path.lstrip('/') }"
        headers = {"Accept": "application/json"}
        try:
            response = self.session.request(
                method,
                url,
                params=params,
                timeout=DEFAULT_TIMEOUT,
                headers=headers,
            )
        except requests.RequestException as exc:  # pragma: no cover - network errors
            raise MTGCHError(str(exc)) from exc

        if response.status_code == 404:
            return None
        if response.status_code >= 400:
            raise MTGCHError(f"HTTP {response.status_code}: {response.text.strip() or '未知错误'}")

        if not response.content:
            return None
        try:
            return response.json()
        except ValueError as exc:  # pragma: no cover - response format issues
            raise MTGCHError("Invalid JSON returned by mtgch API") from exc

    # -------------------------------------------------------------- HTML --
    def _fetch_via_html(
        self,
        *,
        english_name: str,
        face_names: Sequence[str],
    ) -> Optional[ChineseCardInfo]:
        search_url = urljoin(MTGCH_WEB_ROOT, "cards/search")
        try:
            html = self._get_html(search_url, params={"q": english_name})
        except MTGCHError:
            return None
        parser = _MTGCHSearchParser()
        parser.feed(html)
        detail_path = parser.card_href
        if not detail_path:
            # Fall back to an alternate search endpoint used by the website.
            alt_url = urljoin(MTGCH_WEB_ROOT, "search")
            try:
                html = self._get_html(alt_url, params={"q": english_name})
            except MTGCHError:
                return None
            parser = _MTGCHSearchParser()
            parser.feed(html)
            detail_path = parser.card_href
        if not detail_path:
            return None

        detail_url = urljoin(MTGCH_WEB_ROOT, detail_path.lstrip("/"))
        try:
            detail_html = self._get_html(detail_url)
        except MTGCHError:
            return None

        detail_parser = _MTGCHDetailParser()
        detail_parser.feed(detail_html)
        values = detail_parser.values
        if not values:
            return None

        face = ChineseCardFace(
            name=values.get("name"),
            type_line=values.get("type"),
            oracle_text=values.get("text"),
        )
        # For double-faced cards the HTML page usually repeats the card name
        # separated by "//".  Split it to best-effort match the number of
        # faces we have.
        faces = [face]
        if face.name and "//" in face.name and len(face_names) > 1:
            parts = [part.strip() for part in face.name.split("//")]
            faces = [
                ChineseCardFace(
                    name=parts[index] if index < len(parts) else part,
                    type_line=values.get("type"),
                    oracle_text=values.get("text"),
                )
                for index, part in enumerate(parts)
            ]
        return ChineseCardInfo(faces=faces, set_name=values.get("set"))

    def _get_html(
        self,
        url: str,
        *,
        params: Optional[dict[str, str]] = None,
    ) -> str:
        headers = {"Accept": "text/html,application/xhtml+xml"}
        try:
            response = self.session.get(
                url,
                params=params,
                timeout=DEFAULT_TIMEOUT,
                headers=headers,
            )
        except requests.RequestException as exc:  # pragma: no cover - network errors
            raise MTGCHError(str(exc)) from exc
        if response.status_code >= 400:
            raise MTGCHError(f"HTTP {response.status_code}: {response.text.strip() or '未知错误'}")
        response.encoding = response.encoding or response.apparent_encoding
        return response.text
