import { useEffect, useMemo, useState } from "react";
import { CardTable } from "./components/CardTable";
import { CardDetails } from "./components/CardDetails";
import { BinderBoard } from "./components/BinderBoard";
import { fetchCards, fetchMetadata } from "./api";
import { BinderPage, BinderSide, CardData, Metadata } from "./types";
import "./App.css";

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "";
const SLOTS_PER_PAGE = 9;

type TabKey = "library" | "binder";

type BinderPlacement = {
  pageIndex: number;
  side: BinderSide;
  slotIndex: number;
};

function normaliseQuery(value: string) {
  return value.trim().toLowerCase();
}

function createEmptyPage(index: number): BinderPage {
  return {
    id: `page-${index}`,
    front: Array(SLOTS_PER_PAGE).fill(null),
    back: Array(SLOTS_PER_PAGE).fill(null),
  };
}

export default function App() {
  const [activeTab, setActiveTab] = useState<TabKey>("library");
  const [cards, setCards] = useState<CardData[]>([]);
  const [metadata, setMetadata] = useState<Metadata | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [query, setQuery] = useState("");
  const [selectedStaxType, setSelectedStaxType] = useState("all");
  const [selectedCardType, setSelectedCardType] = useState("all");
  const [selectedCardId, setSelectedCardId] = useState<string | null>(null);
  const [binderPages, setBinderPages] = useState<BinderPage[]>([
    createEmptyPage(1),
  ]);
  const [activePageIndex, setActivePageIndex] = useState(0);

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

  useEffect(() => {
    if (!filteredCards.length) {
      if (selectedCardId !== null) {
        setSelectedCardId(null);
      }
      return;
    }

    const stillVisible = filteredCards.some((card) => card.id === selectedCardId);

    if (!stillVisible) {
      setSelectedCardId(filteredCards[0].id);
    }
  }, [filteredCards, selectedCardId]);

  const selectedCard = useMemo(() => {
    if (!selectedCardId) {
      return null;
    }
    return cards.find((card) => card.id === selectedCardId) ?? null;
  }, [cards, selectedCardId]);

  const cardsById = useMemo(() => {
    const result: Record<string, CardData> = {};
    for (const card of cards) {
      result[card.id] = card;
    }
    return result;
  }, [cards]);

  const handleSelectCard = (card: CardData) => {
    setSelectedCardId(card.id);
  };

  const placeCardInBinder = (card: CardData, preferred?: BinderPlacement) => {
    setBinderPages((prev) => {
      let next = prev.map((page) => ({
        ...page,
        front: [...page.front],
        back: [...page.back],
      }));

      let pageIndex = preferred?.pageIndex ?? activePageIndex;
      let side: BinderSide = preferred?.side ?? "front";
      let slotIndex = preferred?.slotIndex ?? -1;

      if (preferred) {
        if (!next[pageIndex]) {
          return prev;
        }
        const sideSlots = next[pageIndex][side];
        if (slotIndex < 0 || slotIndex >= sideSlots.length) {
          return prev;
        }
      } else {
        if (!next[pageIndex]) {
          pageIndex = 0;
        }

        const findFirstEmpty = (pageIdx: number, binderSide: BinderSide) => {
          const slots = next[pageIdx]?.[binderSide] ?? [];
          return slots.findIndex((value) => !value);
        };

        let available = next[pageIndex]
          ? findFirstEmpty(pageIndex, side)
          : -1;

        if (available === -1 && next[pageIndex]) {
          const alternateSide: BinderSide = side === "front" ? "back" : "front";
          const alternateIndex = findFirstEmpty(pageIndex, alternateSide);
          if (alternateIndex !== -1) {
            side = alternateSide;
            available = alternateIndex;
          }
        }

        if (available === -1) {
          let found = false;
          for (let p = 0; p < next.length && !found; p++) {
            for (const candidateSide of ["front", "back"] as const) {
              const idx = findFirstEmpty(p, candidateSide);
              if (idx !== -1) {
                pageIndex = p;
                side = candidateSide;
                available = idx;
                found = true;
                break;
              }
            }
          }

          if (!found) {
            next = [...next, createEmptyPage(next.length + 1)];
            pageIndex = next.length - 1;
            side = "front";
            available = 0;
          }
        }

        slotIndex = available;
      }

      next[pageIndex][side][slotIndex] = card.id;
      setActivePageIndex(pageIndex);
      return next;
    });
  };

  const handleQuickAdd = (card: CardData) => {
    placeCardInBinder(card);
    setActiveTab("binder");
  };

  const handleSlotDrop = (
    pageIndex: number,
    side: BinderSide,
    slotIndex: number,
    cardId: string
  ) => {
    const card = cardsById[cardId];
    if (!card) {
      return;
    }
    placeCardInBinder(card, { pageIndex, side, slotIndex });
  };

  const handleSlotRemove = (
    pageIndex: number,
    side: BinderSide,
    slotIndex: number
  ) => {
    setBinderPages((prev) =>
      prev.map((page, idx) => {
        if (idx !== pageIndex) {
          return page;
        }
        const updatedSide = [...page[side]];
        updatedSide[slotIndex] = null;
        return {
          ...page,
          [side]: updatedSide,
        };
      })
    );
  };

  const handleClearBinder = () => {
    setBinderPages([createEmptyPage(1)]);
    setActivePageIndex(0);
  };

  const handleAddPage = () => {
    setBinderPages((prev) => {
      const next = [...prev, createEmptyPage(prev.length + 1)];
      setActivePageIndex(next.length - 1);
      return next;
    });
  };

  const handlePageChange = (index: number) => {
    setActivePageIndex(index);
  };

  const handleTabChange = (tab: TabKey) => {
    setActiveTab(tab);
  };

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
          <p>浏览、筛选卡牌并构建你的牌本页面布局。</p>
        </div>
      </header>

      <nav className="app__tabs" aria-label="主视图切换">
        <button
          type="button"
          className={`app__tab${activeTab === "library" ? " app__tab--active" : ""}`}
          onClick={() => handleTabChange("library")}
        >
          卡牌列表
        </button>
        <button
          type="button"
          className={`app__tab${activeTab === "binder" ? " app__tab--active" : ""}`}
          onClick={() => handleTabChange("binder")}
        >
          牌本
        </button>
      </nav>

      <main className="app__body">
        {activeTab === "library" ? (
          <section className="library-panel">
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

            <div className="library">
              <div className="library__list">
                <CardTable
                  cards={filteredCards}
                  onAdd={handleQuickAdd}
                  onSelect={handleSelectCard}
                  selectedCardId={selectedCardId}
                  apiBase={API_BASE}
                />
              </div>
              <div className="library__details">
                <CardDetails
                  card={selectedCard}
                  onAdd={handleQuickAdd}
                  apiBase={API_BASE}
                />
              </div>
            </div>
          </section>
        ) : (
          <BinderBoard
            pages={binderPages}
            cardsById={cardsById}
            activePageIndex={activePageIndex}
            onPageChange={handlePageChange}
            onAddPage={handleAddPage}
            onClear={handleClearBinder}
            onSlotDrop={handleSlotDrop}
            onSlotRemove={handleSlotRemove}
            apiBase={API_BASE}
          />
        )}
      </main>
    </div>
  );
}
