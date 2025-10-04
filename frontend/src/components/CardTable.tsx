import { useState } from "react";
import { CardData } from "../types";
import { ManaCost } from "./ManaCost";
import "./CardTable.css";

interface CardTableProps {
  cards: CardData[];
  onAdd: (card: CardData) => void;
  apiBase: string;
}

export function CardTable({ cards, onAdd, apiBase }: CardTableProps) {
  const [expandedCard, setExpandedCard] = useState<string | null>(null);

  if (!cards.length) {
    return <p className="card-table__empty">未找到符合条件的卡牌。</p>;
  }

  return (
    <table className="card-table">
      <thead>
        <tr>
          <th>卡图</th>
          <th>名称</th>
          <th>法术力值</th>
          <th>类型</th>
          <th>锁类型</th>
          <th>描述</th>
          <th>操作</th>
        </tr>
      </thead>
      <tbody>
        {cards.map((card) => {
          const primaryFace = card.faces[0];
          const secondaryFaces = card.faces.slice(1);
          const description = primaryFace.description || "暂无描述";
          const isExpanded = expandedCard === card.id;
          const descriptionPreview = description.length > 120 && !isExpanded
            ? `${description.slice(0, 120)}…`
            : description;

          const imageUrl = primaryFace.image
            ? `${apiBase}${primaryFace.image}`
            : undefined;

          return (
            <tr key={card.id} className="card-table__row">
              <td>
                {imageUrl ? (
                  <img
                    src={imageUrl}
                    alt={primaryFace.chineseName}
                    className="card-table__thumbnail"
                  />
                ) : (
                  <span className="card-table__no-image">无图</span>
                )}
              </td>
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
                {description.length > 120 && (
                  <button
                    type="button"
                    className="card-table__toggle"
                    onClick={() =>
                      setExpandedCard(isExpanded ? null : card.id)
                    }
                  >
                    {isExpanded ? "收起" : "展开"}
                  </button>
                )}
              </td>
              <td>
                <button
                  type="button"
                  className="card-table__add"
                  onClick={() => onAdd(card)}
                >
                  加入牌本
                </button>
              </td>
            </tr>
          );
        })}
      </tbody>
    </table>
  );
}
