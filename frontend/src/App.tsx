import { useEffect, useMemo, useState } from "react";
import { CardTable } from "./components/CardTable";
import { DeckBoard } from "./components/DeckBoard";
import { fetchCards, fetchMetadata } from "./api";
import { CardData, DeckCounts, Metadata } from "./types";
import "./App.css";

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "";

function normaliseQuery(value: string) {
  return value.trim().toLowerCase();
}

export default function App() {
  const [cards, setCards] = useState<CardData[]>([]);
  const [metadata, setMetadata] = useState<Metadata | null>(null);
  const [deckCounts, setDeckCounts] = useState<DeckCounts>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [query, setQuery] = useState("");
  const [selectedStaxType, setSelectedStaxType] = useState("all");
  const [selectedCardType, setSelectedCardType] = useState("all");

  useEffect(() => {
    async function load() {
      try {
        const [cardData, meta] = await Promise.all([
          fetchCards(),
          fetchMetadata(),
        ]);
        setCards(cardData);
        setMetadata(meta);
        setError(null);
      } catch (err) {
        setError(err instanceof Error ? err.message : "未知错误");
      } finally {
        setLoading(false);
      }
    }

    load();
  }, []);

  const filteredCards = useMemo(() => {
    const q = normaliseQuery(query);
    return cards.filter((card) => {
      const primaryFace = card.faces[0];
      const matchesQuery =
        !q ||
        primaryFace.chineseName.toLowerCase().includes(q) ||
        primaryFace.englishName.toLowerCase().includes(q) ||
        primaryFace.description.toLowerCase().includes(q);

      const matchesStax =
        selectedStaxType === "all" || card.staxType?.key === selectedStaxType;

      const matchesType =
        selectedCardType === "all" || card.sortCardType === selectedCardType;

      return matchesQuery && matchesStax && matchesType;
    });
  }, [cards, query, selectedStaxType, selectedCardType]);

  const handleAddCard = (card: CardData) => {
    setDeckCounts((prev) => ({
      ...prev,
      [card.id]: (prev[card.id] ?? 0) + 1,
    }));
  };

  const handleRemoveCard = (cardId: string) => {
    setDeckCounts((prev) => {
      const current = prev[cardId] ?? 0;
      if (current <= 1) {
        const { [cardId]: _removed, ...rest } = prev;
        return rest;
      }
      return {
        ...prev,
        [cardId]: current - 1,
      };
    });
  };

  const handleClearDeck = () => setDeckCounts({});

  if (loading) {
    return <div className="app app--loading">正在加载卡牌数据…</div>;
  }

  if (error) {
    return <div className="app app--error">加载失败：{error}</div>;
  }

  return (
    <div className="app">
      <header className="app__header">
        <div>
          <h1>锁牌名录牌本构建器</h1>
          <p>浏览、筛选卡牌并构建你的锁牌牌本。</p>
        </div>
        <div className="app__filters">
          <input
            type="search"
            placeholder="搜索中文名、英文名或描述…"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
          />
          <select
            value={selectedStaxType}
            onChange={(event) => setSelectedStaxType(event.target.value)}
          >
            <option value="all">全部锁类型</option>
            {metadata?.staxTypes.map((type) => (
              <option key={type.key} value={type.key}>
                {type.label}
              </option>
            ))}
          </select>
          <select
            value={selectedCardType}
            onChange={(event) => setSelectedCardType(event.target.value)}
          >
            <option value="all">全部牌类型</option>
            {[...(metadata?.cardTypeOrder ?? [])]
              .concat(
                Array.from(
                  new Set(cards.map((card) => card.sortCardType || "其他"))
                ).filter(
                  (type) => !(metadata?.cardTypeOrder ?? []).includes(type)
                )
              )
              .map((type) => (
                <option key={type} value={type}>
                  {type}
                </option>
              ))}
          </select>
        </div>
      </header>

      <main className="app__content">
        <section className="app__panel app__panel--table">
          <h2>卡牌列表</h2>
          <CardTable cards={filteredCards} onAdd={handleAddCard} apiBase={API_BASE} />
        </section>
        <section className="app__panel app__panel--deck">
          <DeckBoard
            cards={cards}
            deckCounts={deckCounts}
            onRemove={handleRemoveCard}
            onClear={handleClearDeck}
            apiBase={API_BASE}
            metadata={metadata}
          />
        </section>
      </main>
    </div>
  );
}
