import { useMemo, useState } from "react";
import { BinderPage, BinderSide, CardData, CARD_DRAG_MIME } from "../types";
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
    cardId: string
  ) => void;
  onSlotRemove: (pageIndex: number, side: BinderSide, slotIndex: number) => void;
  apiBase: string;
}

function getSlotLabel(index: number) {
  const row = Math.floor(index / 3) + 1;
  const column = (index % 3) + 1;
  return `${row}-${column}`;
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
  apiBase,
}: BinderBoardProps) {
  const [hoveredSlot, setHoveredSlot] = useState<{
    pageIndex: number;
    side: BinderSide;
    slotIndex: number;
  } | null>(null);

  const totalCards = useMemo(() => {
    return pages.reduce((sum, page) => {
      const front = page.front.filter(Boolean).length;
      const back = page.back.filter(Boolean).length;
      return sum + front + back;
    }, 0);
  }, [pages]);

  const handleDrop = (
    event: React.DragEvent<HTMLDivElement>,
    pageIndex: number,
    side: BinderSide,
    slotIndex: number
  ) => {
    event.preventDefault();
    const data =
      event.dataTransfer.getData(CARD_DRAG_MIME) ||
      event.dataTransfer.getData("text/plain");
    if (!data) {
      return;
    }
    onSlotDrop(pageIndex, side, slotIndex, data);
    setHoveredSlot(null);
  };

  const handleDragOver = (event: React.DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    event.dataTransfer.dropEffect = "copy";
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
                            onDrop={(event) =>
                              handleDrop(event, pageIndex, side, index)
                            }
                            onDragOver={handleDragOver}
                            onDragEnter={() =>
                              handleDragEnter(pageIndex, side, index)
                            }
                            onDragLeave={() =>
                              handleDragLeave(pageIndex, side, index)
                            }
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
