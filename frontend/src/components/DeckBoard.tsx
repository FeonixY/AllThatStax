import { useMemo } from "react";
import { CardData, DeckCounts, Metadata } from "../types";
import { getCmcGroup } from "../utils/mana";
import "./DeckBoard.css";

interface DeckBoardProps {
  cards: CardData[];
  deckCounts: DeckCounts;
  onRemove: (cardId: string) => void;
  onClear: () => void;
  apiBase: string;
  metadata: Metadata | null;
}

interface GroupedEntry {
  card: CardData;
  count: number;
}

const DEFAULT_TYPES = ["生物", "神器", "结界", "其他"];
const CMC_GROUPS = ["0", "1", "2", "3", "4", "5", "6", "7+"];

export function DeckBoard({
  cards,
  deckCounts,
  onRemove,
  onClear,
  apiBase,
  metadata,
}: DeckBoardProps) {
  const cardsInDeck = useMemo(
    () => cards.filter((card) => deckCounts[card.id]),
    [cards, deckCounts]
  );

  const totalCards = useMemo(
    () =>
      cardsInDeck.reduce((acc, card) => acc + (deckCounts[card.id] ?? 0), 0),
    [cardsInDeck, deckCounts]
  );

  const grouped = useMemo(() => {
    const result: Record<string, Record<string, GroupedEntry[]>> = {};
    const cardTypes = new Set<string>();

    for (const card of cardsInDeck) {
      const count = deckCounts[card.id];
      if (!count) continue;
      const cmcGroup = getCmcGroup(card.manaValue);
      const cardType = card.sortCardType || "其他";
      cardTypes.add(cardType);

      if (!result[cmcGroup]) {
        result[cmcGroup] = {};
      }
      if (!result[cmcGroup][cardType]) {
        result[cmcGroup][cardType] = [];
      }
      result[cmcGroup][cardType].push({ card, count });
    }

    const orderedTypes = metadata?.cardTypeOrder?.length
      ? [...metadata.cardTypeOrder]
      : [...DEFAULT_TYPES];

    for (const type of cardTypes) {
      if (!orderedTypes.includes(type)) {
        orderedTypes.push(type);
      }
    }

    for (const grid of Object.values(result)) {
      for (const entryList of Object.values(grid)) {
        entryList.sort((a, b) =>
          a.card.faces[0].chineseName.localeCompare(
            b.card.faces[0].chineseName,
            "zh-Hans"
          )
        );
      }
    }

    return { grouped: result, orderedTypes };
  }, [cardsInDeck, deckCounts, metadata]);

  const manaCurve = useMemo(() => {
    const curve: Record<string, number> = {};
    for (const group of CMC_GROUPS) {
      curve[group] = 0;
    }
    for (const card of cardsInDeck) {
      const group = getCmcGroup(card.manaValue);
      curve[group] = (curve[group] ?? 0) + (deckCounts[card.id] ?? 0);
    }
    return curve;
  }, [cardsInDeck, deckCounts]);

  const staxDistribution = useMemo(() => {
    const distribution: Record<string, number> = {};
    for (const card of cardsInDeck) {
      const staxLabel = card.staxType?.label ?? "未分类";
      distribution[staxLabel] =
        (distribution[staxLabel] ?? 0) + (deckCounts[card.id] ?? 0);
    }
    return distribution;
  }, [cardsInDeck, deckCounts]);

  return (
    <section className="deck-board">
      <header className="deck-board__header">
        <div>
          <h2>牌本</h2>
          <p>当前已选择 {totalCards} 张卡牌</p>
        </div>
        <button
          type="button"
          className="deck-board__clear"
          onClick={onClear}
          disabled={totalCards === 0}
        >
          清空牌本
        </button>
      </header>

      <div className="deck-board__stats">
        <div>
          <h3>法术力曲线</h3>
          <ul>
            {CMC_GROUPS.map((group) => (
              <li key={group}>
                <span>{group}费</span>
                <span>{manaCurve[group] ?? 0}</span>
              </li>
            ))}
          </ul>
        </div>
        <div>
          <h3>锁类型分布</h3>
          <ul>
            {Object.entries(staxDistribution).map(([label, count]) => (
              <li key={label}>
                <span>{label}</span>
                <span>{count}</span>
              </li>
            ))}
            {Object.keys(staxDistribution).length === 0 && <li>尚未选择卡牌</li>}
          </ul>
        </div>
      </div>

      <div className="deck-board__grid">
        <div className="deck-board__grid-header">
          <div>法术力值 / 类型</div>
          {grouped.orderedTypes.map((type) => (
            <div key={type}>{type}</div>
          ))}
        </div>
        {CMC_GROUPS.map((group) => (
          <div className="deck-board__grid-row" key={group}>
            <div className="deck-board__grid-label">{group}费</div>
            {grouped.orderedTypes.map((type) => {
              const entries = grouped.grouped[group]?.[type] ?? [];
              return (
                <div className="deck-board__grid-cell" key={`${group}-${type}`}>
                  {entries.map(({ card, count }) => {
                    const face = card.faces[0];
                    const imageUrl = face.image
                      ? `${apiBase}${face.image}`
                      : undefined;
                    return (
                      <div className="deck-board__card" key={card.id}>
                        {imageUrl ? (
                          <img
                            src={imageUrl}
                            alt={face.chineseName}
                            className="deck-board__card-image"
                          />
                        ) : (
                          <span className="deck-board__card-placeholder">无图</span>
                        )}
                        <div className="deck-board__card-info">
                          <span className="deck-board__card-name">
                            {face.chineseName}
                          </span>
                          <small>{face.englishName}</small>
                          <span className="deck-board__card-count">x{count}</span>
                        </div>
                        <button
                          type="button"
                          className="deck-board__remove"
                          onClick={() => onRemove(card.id)}
                        >
                          移除
                        </button>
                      </div>
                    );
                  })}
                  {entries.length === 0 && (
                    <span className="deck-board__placeholder">—</span>
                  )}
                </div>
              );
            })}
          </div>
        ))}
      </div>
    </section>
  );
}
