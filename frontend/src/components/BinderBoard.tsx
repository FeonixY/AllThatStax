import { useMemo, useState } from "react";
import { BinderPage, BinderSide, CardData, CARD_DRAG_MIME } from "../types";
import "./BinderBoard.css";

interface BinderBoardProps {
  pages: BinderPage[];
  cardsById: Record<string, CardData>;
  activePageIndex: number;
  activeSide: BinderSide;
  onPageChange: (index: number) => void;
  onSideChange: (side: BinderSide) => void;
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

const SLOT_COUNT = 9;

function getSlotLabel(index: number) {
  const row = Math.floor(index / 3) + 1;
  const column = (index % 3) + 1;
  return `${row}-${column}`;
}

export function BinderBoard({
  pages,
  cardsById,
  activePageIndex,
  activeSide,
  onPageChange,
  onSideChange,
  onAddPage,
  onClear,
  onSlotDrop,
  onSlotRemove,
  apiBase,
}: BinderBoardProps) {
  const [hoveredSlot, setHoveredSlot] = useState<number | null>(null);

  const activePage = pages[activePageIndex] ?? null;

  const totalCards = useMemo(() => {
    return pages.reduce((sum, page) => {
      const front = page.front.filter(Boolean).length;
      const back = page.back.filter(Boolean).length;
      return sum + front + back;
    }, 0);
  }, [pages]);

  const slots = useMemo(() => {
    if (!activePage) {
      return Array<string | null>(SLOT_COUNT).fill(null);
    }
    return [...activePage[activeSide]];
  }, [activePage, activeSide]);

  const handleDrop = (event: React.DragEvent<HTMLDivElement>, slotIndex: number) => {
    event.preventDefault();
    const data =
      event.dataTransfer.getData(CARD_DRAG_MIME) ||
      event.dataTransfer.getData("text/plain");
    if (!data) {
      return;
    }
    onSlotDrop(activePageIndex, activeSide, slotIndex, data);
    setHoveredSlot(null);
  };

  const handleDragOver = (event: React.DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    event.dataTransfer.dropEffect = "copy";
  };

  const handleDragEnter = (slotIndex: number) => setHoveredSlot(slotIndex);
  const handleDragLeave = (slotIndex: number) => {
    setHoveredSlot((current) => (current === slotIndex ? null : current));
  };

  return (
    <section className="binder">
      <header className="binder__header">
        <div>
          <h2>牌本</h2>
          <p>
            第 {activePageIndex + 1} 页 · {activeSide === "front" ? "正面" : "背面"}
            · 已放入 {totalCards} 张卡牌
          </p>
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
              第 {index + 1} 页
            </button>
          ))}
        </div>
        <div className="binder__side-toggle">
          <button
            type="button"
            className={`binder__side${
              activeSide === "front" ? " binder__side--active" : ""
            }`}
            onClick={() => onSideChange("front")}
          >
            正面
          </button>
          <button
            type="button"
            className={`binder__side${
              activeSide === "back" ? " binder__side--active" : ""
            }`}
            onClick={() => onSideChange("back")}
          >
            背面
          </button>
        </div>
      </div>

      <p className="binder__hint">将卡牌图片从上方“卡牌列表”标签页拖拽到任一格子即可放入牌本。</p>

      <div className="binder__grid">
        {slots.map((cardId, index) => {
          const card = cardId ? cardsById[cardId] : null;
          const face = card?.faces[0];
          const imageUrl = face?.image ? `${apiBase}${face.image}` : null;
          const isHovered = hoveredSlot === index;

          return (
            <div
              key={`${activeSide}-${index}`}
              className={`binder__slot${isHovered ? " binder__slot--hovered" : ""}`}
              onDrop={(event) => handleDrop(event, index)}
              onDragOver={handleDragOver}
              onDragEnter={() => handleDragEnter(index)}
              onDragLeave={() => handleDragLeave(index)}
            >
              <div className="binder__slot-label">格 {getSlotLabel(index)}</div>
              {card && imageUrl ? (
                <img
                  src={imageUrl}
                  alt={face?.chineseName ?? "卡牌"}
                  className="binder__slot-image"
                />
              ) : (
                <span className="binder__slot-placeholder">拖拽卡牌到此</span>
              )}
              <footer className="binder__slot-footer">
                <span className="binder__slot-name">
                  {face?.chineseName ?? "空位"}
                </span>
                <button
                  type="button"
                  className="binder__slot-remove"
                  onClick={() => onSlotRemove(activePageIndex, activeSide, index)}
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
}
