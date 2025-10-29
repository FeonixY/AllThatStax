"""Generate LaTeX snippets from the JSON card store."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Sequence

from allthatstax.card_store import CardFaceRecord, CardRecord, load_card_store
from allthatstax.config import load_config

__all__ = ["generate_latex_text"]

CARD_TYPE_ORDER: Dict[str, int] = {
    "生物": 1,
    "神器": 2,
    "结界": 3,
    "其他": 4,
}

LEGALITY_FIELDS: Sequence[str] = (
    "standard",
    "pioneer",
    "modern",
    "legacy",
    "pauper",
    "vintage",
    "commander",
    "duel",
)


@dataclass
class LatexCard:
    body: str
    mana_value: int
    sort_type: str
    english_name: str

    def base_sort_key(self) -> tuple[int, int, str]:
        return (
            self.mana_value,
            CARD_TYPE_ORDER.get(self.sort_type, len(CARD_TYPE_ORDER) + 1),
            self.english_name,
        )

    def plus_sort_key(self) -> tuple[int, int, str]:
        return (
            CARD_TYPE_ORDER.get(self.sort_type, len(CARD_TYPE_ORDER) + 1),
            self.mana_value,
            self.english_name,
        )


def _coerce_text(value: object, default: str = "") -> str:
    text = str(value) if value is not None else default
    if text.strip().lower() == "none":
        return default
    return text


def _format_mana_cost(value: str) -> str:
    if not value:
        return "无费用（法术力值为0）"
    return value.replace("{", "\\MTGsymbol{").replace("}", "}{5}")


def _format_description(value: str) -> str:
    if not value:
        return ""
    return value.replace("{", "\\MTGsymbol{").replace("}", "}{3}").replace("\n", "\\\\\n")


def _format_legalities(legalities: Dict[str, str]) -> str:
    rendered: List[str] = []
    for index, label in enumerate(LEGALITY_FIELDS):
        entry = _coerce_text(legalities.get(label, "unknown"))
        suffix = "," if index < len(LEGALITY_FIELDS) - 1 else ""
        rendered.append(f"\tlegality / {label} = {entry}{suffix}")
    return "\n".join(rendered)


def _stax_label(stax_key: str | None, mapping: Dict[str, str]) -> str:
    if not stax_key:
        return ""
    return _coerce_text(mapping.get(stax_key, stax_key))


def _build_single_card(
    card: CardRecord,
    face: CardFaceRecord,
    stax_mapping: Dict[str, str],
) -> LatexCard:
    lines = [
        "\\card",
        "{",
        f"\tcard_english_name = {{{_coerce_text(face.english_name)}}},",
        f"\tcard_chinese_name = {{{_coerce_text(face.chinese_name)}}},",
        f"\tcard_image = {face.image_file},",
        f"\tmana_cost = {_format_mana_cost(_coerce_text(face.mana_cost))},",
        f"\tcard_type = {_coerce_text(face.card_type)},",
        f"\tdescription = {{{_format_description(_coerce_text(face.description))}}},",
        f"\tstax_type = {_stax_label(card.stax_type, stax_mapping)},",
        f"\tis_in_restricted_list = {'RL' if card.is_restricted else 'Not RL'},",
        _format_legalities(card.legalities),
        "}",
        "",
    ]
    return LatexCard("\n".join(lines), int(card.mana_value), card.sort_card_type, face.english_name)


def _build_multiface_card(
    card: CardRecord,
    faces: Iterable[CardFaceRecord],
    stax_mapping: Dict[str, str],
) -> LatexCard:
    faces_list = list(faces)
    if len(faces_list) < 2:
        raise ValueError("Multiface card requires at least two faces")
    front, back = faces_list[0], faces_list[1]
    lines = [
        "\\mfcard",
        "{",
        f"\tfront_card_english_name = {{{_coerce_text(front.english_name)}}},",
        f"\tfront_card_chinese_name = {{{_coerce_text(front.chinese_name)}}},",
        f"\tfront_card_image = {front.image_file},",
        f"\tfront_mana_cost = {_format_mana_cost(_coerce_text(front.mana_cost))},",
        f"\tfront_card_type = {_coerce_text(front.card_type)},",
        f"\tfront_description = {{{_format_description(_coerce_text(front.description))}}},",
        f"\tback_card_english_name = {{{_coerce_text(back.english_name)}}},",
        f"\tback_card_chinese_name = {{{_coerce_text(back.chinese_name)}}},",
        f"\tback_card_image = {back.image_file},",
        f"\tback_mana_cost = {_format_mana_cost(_coerce_text(back.mana_cost))},",
        f"\tback_card_type = {_coerce_text(back.card_type)},",
        f"\tback_description = {{{_format_description(_coerce_text(back.description))}}},",
        f"\tstax_type = {_stax_label(card.stax_type, stax_mapping)},",
        f"\tis_in_restricted_list = {'RL' if card.is_restricted else 'Not RL'},",
        _format_legalities(card.legalities),
        "}",
        "",
    ]
    return LatexCard("\n".join(lines), int(card.mana_value), card.sort_card_type, front.english_name)


def _group_cards(cards: List[LatexCard]) -> Dict[object, List[LatexCard]]:
    cards.sort(key=lambda card: card.base_sort_key())
    groups: Dict[object, List[LatexCard]] = {i: [] for i in range(7)}
    groups["7+"] = []
    for card in cards:
        if card.mana_value >= 7:
            groups["7+"].append(card)
        else:
            groups.setdefault(card.mana_value, []).append(card)
    groups["7+"].sort(key=lambda card: card.plus_sort_key())
    return groups


def generate_latex_text(
    data_file_name: str | Path,
    latex_text_name: str | Path,
    *,
    config_path: str | Path | None = None,
) -> Path:
    """Generate LaTeX snippets from the JSON card data file."""

    data_path = Path(data_file_name)
    if not data_path.exists():
        raise FileNotFoundError(f"Card data file not found: {data_path}")

    store = load_card_store(data_path)
    if not store.cards:
        raise ValueError("卡牌数据为空，无法生成 LaTeX 内容")

    config = load_config(config_path) if config_path else load_config()
    stax_mapping = {str(key): str(value) for key, value in config.get("stax_type", {}).items()}

    latex_cards: List[LatexCard] = []
    for card in store.cards.values():
        if not card.faces:
            continue
        if card.kind == "multiface" and len(card.faces) >= 2:
            latex_cards.append(_build_multiface_card(card, card.faces, stax_mapping))
        else:
            latex_cards.append(_build_single_card(card, card.faces[0], stax_mapping))

    if not latex_cards:
        raise ValueError("未找到任何可用卡牌用于生成 LaTeX")

    groups = _group_cards(latex_cards)

    output_path = Path(latex_text_name)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", encoding="utf-8") as handle:
        for cmc in range(1, 7):
            handle.write(f"\\chapter{{{cmc}费}}\n\n")
            current_type = None
            for card in groups.get(cmc, []):
                if card.sort_type != current_type:
                    current_type = card.sort_type
                    handle.write(f"\\section{{{current_type}}}\n\n")
                handle.write(card.body)
        handle.write("\\chapter{7+费}\n\n")
        current_type = None
        for card in groups["7+"]:
            if card.sort_type != current_type:
                current_type = card.sort_type
                handle.write(f"\\section{{{current_type}}}\n\n")
            handle.write(card.body)
        handle.write("\\chapter{0费（包括地）}\n\n")
        current_type = None
        for card in groups.get(0, []):
            if card.sort_type != current_type:
                current_type = card.sort_type
                handle.write(f"\\section{{{current_type}}}\n\n")
            handle.write(card.body)

    return output_path
