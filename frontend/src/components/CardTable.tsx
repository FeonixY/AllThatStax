import type { DragEvent, MouseEvent } from "react";
import { CardData, CARD_DRAG_MIME } from "../types";
import { ManaCost } from "./ManaCost";
import "./CardTable.css";

interface CardTableProps {
  cards: CardData[];
  onAdd: (card: CardData) => void;
  onSelect: (card: CardData) => void;
  selectedCardId: string | null;
  apiBase: string;
}

export function CardTable({
  cards,
  onAdd,
  onSelect,
  selectedCardId,
  apiBase,
}: CardTableProps) {
  if (!cards.length) {
    return <p className="card-table__empty">未找到符合条件的卡牌。</p>;
  }

  return (
    <table className="card-table">
      <thead>
        <tr>
          <th>名称</th>
          <th>法术力值</th>
          <th>类型</th>
          <th>锁类型</th>
          <th>描述</th>
          <th className="card-table__actions">操作</th>
        </tr>
      </thead>
      <tbody>
        {cards.map((card) => {
          const primaryFace = card.faces[0];
          const secondaryFaces = card.faces.slice(1);
          const description = primaryFace.description || "暂无描述";
          const isSelected = selectedCardId === card.id;
          const descriptionPreview = description.length > 180
            ? `${description.slice(0, 180)}…`
            : description;

          const handleDragStart = (
            event: DragEvent<HTMLTableRowElement>
          ) => {
            const payload = {
              cardId: card.id,
              source: "library" as const,
            };

            event.dataTransfer.effectAllowed = "copy";
            event.dataTransfer.setData(
              CARD_DRAG_MIME,
              JSON.stringify(payload)
            );
            event.dataTransfer.setData("text/plain", card.id);
          };

          return (
            <tr
              key={card.id}
              className={`card-table__row${
                isSelected ? " card-table__row--selected" : ""
              }`}
              onClick={() => onSelect(card)}
              draggable
              onDragStart={handleDragStart}
            >
              <td className="card-table__name">
                <span>{primaryFace.chineseName}</span>
                <small>{primaryFace.englishName}</small>
                {secondaryFaces.length > 0 && (
                  <ul className="card-table__faces">
                    {secondaryFaces.map((face) => (
                      <li key={face.englishName}>
                        {face.chineseName} / {face.englishName}
                      </li>
                    ))}
                  </ul>
                )}
              </td>
              <td>
                <ManaCost symbols={primaryFace.manaCost} apiBase={apiBase} />
              </td>
              <td className="card-table__type">{primaryFace.cardType}</td>
              <td>{card.staxType ? card.staxType.label : "-"}</td>
              <td className="card-table__description">
                {descriptionPreview}
              </td>
              <td className="card-table__actions">
                <button
                  type="button"
                  className="card-table__add"
                  onClick={(event: MouseEvent<HTMLButtonElement>) => {
                    event.stopPropagation();
                    onAdd(card);
                  }}
                  aria-label={`将 ${primaryFace.chineseName} 加入暂留区`}
                  title="加入暂留区"
                >
                  +
                </button>
              </td>
            </tr>
          );
        })}
      </tbody>
    </table>
  );
}
