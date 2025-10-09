import { useMemo, useState } from "react";
import type { DragEvent, MouseEvent } from "react";
import {
  BinderPage,
  BinderSide,
  CardData,
  CARD_DRAG_MIME,
  DragPayload,
} from "../types";
import "./BinderBoard.css";

interface BinderBoardProps {
  pages: BinderPage[];
  cardsById: Record<string, CardData>;
  activePageIndex: number;
  onPageChange: (index: number) => void;
  onAddPage: () => void;
  onClear: () => void;
  onSlotDrop: (
    pageIndex: number,
    side: BinderSide,
    slotIndex: number,
    payload: DragPayload
  ) => void;
  onSlotRemove: (pageIndex: number, side: BinderSide, slotIndex: number) => void;
  onStagingDrop: (payload: DragPayload) => void;
  onStagingRemove: (index: number) => void;
  stagingCards: string[];
  apiBase: string;
}

function getSlotLabel(index: number) {
  const row = Math.floor(index / 3) + 1;
  const column = (index % 3) + 1;
  return `${row}-${column}`;
}

function parseDragPayload(event: DragEvent<HTMLElement>): DragPayload | null {
  const rawData =
    event.dataTransfer.getData(CARD_DRAG_MIME) ||
    event.dataTransfer.getData("text/plain");

  if (!rawData) {
    return null;
  }

  try {
    const parsed = JSON.parse(rawData) as DragPayload;
    if (parsed && typeof parsed.cardId === "string") {
      return parsed;
    }
  } catch (error) {
    return {
      cardId: rawData,
      source: "library",
    };
  }

  return null;
}

export function BinderBoard({
  pages,
  cardsById,
  activePageIndex,
  onPageChange,
  onAddPage,
  onClear,
  onSlotDrop,
  onSlotRemove,
  onStagingDrop,
  onStagingRemove,
  stagingCards,
  apiBase,
}: BinderBoardProps) {
  const [hoveredSlot, setHoveredSlot] = useState<{
    pageIndex: number;
    side: BinderSide;
    slotIndex: number;
  } | null>(null);
  const [isStagingHovered, setIsStagingHovered] = useState(false);

  const totalCards = useMemo(() => {
    return pages.reduce((sum, page) => {
      const front = page.front.filter(Boolean).length;
      const back = page.back.filter(Boolean).length;
      return sum + front + back;
    }, 0);
  }, [pages]);

  const handleDrop = (
    event: DragEvent<HTMLDivElement>,
    pageIndex: number,
    side: BinderSide,
    slotIndex: number
  ) => {
    event.preventDefault();
    const payload = parseDragPayload(event);
    if (!payload) {
      return;
    }
    onSlotDrop(pageIndex, side, slotIndex, payload);
    setHoveredSlot(null);
  };

  const handleDragOver = (event: DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    event.dataTransfer.dropEffect = "move";
  };

  const handleDragEnter = (
    pageIndex: number,
    side: BinderSide,
    slotIndex: number
  ) => setHoveredSlot({ pageIndex, side, slotIndex });

  const handleDragLeave = (
    pageIndex: number,
    side: BinderSide,
    slotIndex: number
  ) => {
    setHoveredSlot((current) => {
      if (!current) {
        return null;
      }
      const isSameSlot =
        current.pageIndex === pageIndex &&
        current.side === side &&
        current.slotIndex === slotIndex;
      return isSameSlot ? null : current;
    });
  };

  const handleSlotDragStart = (
    event: DragEvent<HTMLDivElement>,
    pageIndex: number,
    side: BinderSide,
    slotIndex: number,
    cardId: string
  ) => {
    const payload: DragPayload = {
      cardId,
      source: "binder",
      binderPageIndex: pageIndex,
      binderSide: side,
      binderSlotIndex: slotIndex,
    };

    event.dataTransfer.effectAllowed = "move";
    event.dataTransfer.setData(CARD_DRAG_MIME, JSON.stringify(payload));
    event.dataTransfer.setData("text/plain", cardId);
  };

  const handleStagingDrop = (event: DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    const payload = parseDragPayload(event);
    if (!payload) {
      setIsStagingHovered(false);
      return;
    }
    onStagingDrop(payload);
    setIsStagingHovered(false);
  };

  const handleStagingDragEnter = () => {
    setIsStagingHovered(true);
  };

  const handleStagingDragLeave = (event: DragEvent<HTMLDivElement>) => {
    const nextTarget = event.relatedTarget as Node | null;
    if (!nextTarget || !event.currentTarget.contains(nextTarget)) {
      setIsStagingHovered(false);
    }
  };

  const handleStagingCardDragStart = (
    event: DragEvent<HTMLDivElement>,
    cardId: string,
    index: number
  ) => {
    const payload: DragPayload = {
      cardId,
      source: "staging",
      stagingIndex: index,
    };

    event.dataTransfer.effectAllowed = "move";
    event.dataTransfer.setData(CARD_DRAG_MIME, JSON.stringify(payload));
    event.dataTransfer.setData("text/plain", cardId);
  };

  return (
    <section className="binder">
      <header className="binder__header">
        <div>
          <h2>牌本</h2>
          <p>共 {pages.length} 张内页 · 已放入 {totalCards} 张卡牌</p>
        </div>
        <div className="binder__actions">
          <button
            type="button"
            className="binder__button"
            onClick={onAddPage}
          >
            新增页面
          </button>
          <button
            type="button"
            className="binder__button binder__button--clear"
            onClick={onClear}
            disabled={totalCards === 0}
          >
            清空牌本
          </button>
        </div>
      </header>

      <div className="binder__controls">
        <div className="binder__pages">
          {pages.map((page, index) => (
            <button
              key={page.id}
              type="button"
              className={`binder__tab${
                index === activePageIndex ? " binder__tab--active" : ""
              }`}
              onClick={() => onPageChange(index)}
            >
              第 {index + 1} 张（第 {index * 2 + 1}-{index * 2 + 2} 页）
            </button>
          ))}
        </div>
      </div>

      <p className="binder__hint">
        提示：拖拽卡牌图片到任一格子，可在同一内页同时管理第
        {activePageIndex * 2 + 1} 与第 {activePageIndex * 2 + 2} 页。
      </p>

      <section className="binder__staging">
        <header className="binder__staging-header">
          <h3>暂留区</h3>
          <p>暂存卡牌以便在不同页面之间调整位置。</p>
        </header>
        <div
          className={`binder__staging-dropzone${
            isStagingHovered ? " binder__staging-dropzone--hovered" : ""
          }`}
          onDrop={handleStagingDrop}
          onDragOver={handleDragOver}
          onDragEnter={handleStagingDragEnter}
          onDragLeave={handleStagingDragLeave}
        >
          {stagingCards.length === 0 ? (
            <span className="binder__staging-empty">
              暂无卡牌。使用“+”按钮或从牌表拖拽加入。
            </span>
          ) : (
            <ul className="binder__staging-list">
              {stagingCards.map((cardId, index) => {
                const card = cardsById[cardId];
                const face = card?.faces[0];
                const imageUrl = face?.image ? `${apiBase}${face.image}` : null;

                return (
                  <li key={`${cardId}-${index}`} className="binder__staging-item">
                    <div
                      className="binder__staging-card"
                      draggable
                      onDragStart={(event: DragEvent<HTMLDivElement>) =>
                        handleStagingCardDragStart(event, cardId, index)
                      }
                    >
                      {imageUrl ? (
                        <img
                          src={imageUrl}
                          alt={face?.chineseName ?? "卡牌"}
                          className="binder__staging-image"
                        />
                      ) : (
                        <span className="binder__staging-placeholder">无图</span>
                      )}
                      <div className="binder__staging-info">
                        <span className="binder__staging-name">
                          {face?.chineseName ?? "未知卡牌"}
                        </span>
                        <span className="binder__staging-subname">
                          {face?.englishName ?? card?.id}
                        </span>
                      </div>
                      <button
                        type="button"
                        className="binder__staging-remove"
                        onClick={(event: MouseEvent<HTMLButtonElement>) => {
                          event.stopPropagation();
                          onStagingRemove(index);
                        }}
                      >
                        移除
                      </button>
                    </div>
                  </li>
                );
              })}
            </ul>
          )}
        </div>
      </section>

      <div className="binder__spreads">
        {pages.map((page, pageIndex) => {
          const frontPageNumber = pageIndex * 2 + 1;
          const backPageNumber = frontPageNumber + 1;

          return (
            <article
              key={page.id}
              className={`binder__spread${
                pageIndex === activePageIndex ? " binder__spread--active" : ""
              }`}
            >
              {(["front", "back"] as const).map((side, sideIdx) => {
                const slots = page[side];
                const pageNumber = sideIdx === 0 ? frontPageNumber : backPageNumber;
                const sideLabel = side === "front" ? "正面" : "背面";

                return (
                  <section key={`${page.id}-${side}`} className="binder__page">
                    <header className="binder__page-header">
                      <h3>
                        第 {pageNumber} 页 · {sideLabel}
                      </h3>
                      <p>内页 {pageIndex + 1} · {sideLabel}</p>
                    </header>
                    <div className="binder__grid">
                      {slots.map((cardId, index) => {
                        const card = cardId ? cardsById[cardId] : null;
                        const face = card?.faces[0];
                        const imageUrl = face?.image ? `${apiBase}${face.image}` : null;
                        const isHovered =
                          hoveredSlot?.pageIndex === pageIndex &&
                          hoveredSlot?.side === side &&
                          hoveredSlot?.slotIndex === index;

                        return (
                          <div
                            key={`${page.id}-${side}-${index}`}
                            className={`binder__slot${
                              isHovered ? " binder__slot--hovered" : ""
                            }`}
                            onDrop={(event: DragEvent<HTMLDivElement>) =>
                              handleDrop(event, pageIndex, side, index)
                            }
                            onDragOver={(event: DragEvent<HTMLDivElement>) =>
                              handleDragOver(event)
                            }
                            onDragEnter={() =>
                              handleDragEnter(pageIndex, side, index)
                            }
                            onDragLeave={() =>
                              handleDragLeave(pageIndex, side, index)
                            }
                            draggable={Boolean(cardId)}
                            onDragStart={(event: DragEvent<HTMLDivElement>) => {
                              if (cardId) {
                                handleSlotDragStart(
                                  event,
                                  pageIndex,
                                  side,
                                  index,
                                  cardId
                                );
                              }
                            }}
                          >
                            <div className="binder__slot-label">
                              格 {getSlotLabel(index)}
                            </div>
                            {card && imageUrl ? (
                              <img
                                src={imageUrl}
                                alt={face?.chineseName ?? "卡牌"}
                                className="binder__slot-image"
                              />
                            ) : (
                              <span className="binder__slot-placeholder">
                                拖拽卡牌到此
                              </span>
                            )}
                            <footer className="binder__slot-footer">
                              <span className="binder__slot-name">
                                {face?.chineseName ?? "空位"}
                              </span>
                              <button
                                type="button"
                                className="binder__slot-remove"
                                onClick={() =>
                                  onSlotRemove(pageIndex, side, index)
                                }
                                disabled={!cardId}
                              >
                                移除
                              </button>
                            </footer>
                          </div>
                        );
                      })}
                    </div>
                  </section>
                );
              })}
            </article>
          );
        })}
      </div>
    </section>
  );
}
