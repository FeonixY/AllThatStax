import { CardData } from "../types";
import { ManaCost } from "./ManaCost";
import "./CardDetails.css";

interface CardDetailsProps {
  card: CardData | null;
  apiBase: string;
  onAdd: (card: CardData) => void;
}

export function CardDetails({ card, apiBase, onAdd }: CardDetailsProps) {
  if (!card) {
    return (
      <div className="card-details card-details--empty">
        <p>从左侧选择一张卡牌以查看详细信息。</p>
      </div>
    );
  }

  const primaryFace = card.faces[0];

  return (
    <div className="card-details">
      <header className="card-details__header">
        <div className="card-details__title">
          <h3>{primaryFace.chineseName}</h3>
          <p>{primaryFace.englishName}</p>
        </div>
        <div className="card-details__actions">
          {card.isRestricted && (
            <span className="card-details__badge card-details__badge--restricted">
              限制
            </span>
          )}
          <button
            type="button"
            className="card-details__add"
            onClick={() => onAdd(card)}
            aria-label={`将 ${primaryFace.chineseName} 加入牌本`}
          >
            +
          </button>
        </div>
      </header>

      <div className="card-details__meta">
        <div>
          <span className="card-details__label">锁类型</span>
          <span>{card.staxType ? card.staxType.label : "—"}</span>
        </div>
        <div>
          <span className="card-details__label">法术力费用</span>
          <ManaCost symbols={primaryFace.manaCost} apiBase={apiBase} />
        </div>
        <div>
          <span className="card-details__label">法术力值</span>
          <span>{card.manaValue}</span>
        </div>
        <div>
          <span className="card-details__label">类型</span>
          <span>{primaryFace.cardType}</span>
        </div>
      </div>

      <div className="card-details__faces">
        {card.faces.map((face, index) => (
          <article key={`${face.englishName}-${index}`} className="card-details__face">
            {card.faces.length > 1 && (
              <header className="card-details__face-header">
                <h4>{face.chineseName}</h4>
                <small>{face.englishName}</small>
              </header>
            )}
            <div className="card-details__face-body">
              {face.image ? (
                <img
                  src={`${apiBase}${face.image}`}
                  alt={face.chineseName}
                  className="card-details__image"
                />
              ) : null}
              <div className="card-details__face-content">
                <div className="card-details__face-meta">
                  <ManaCost symbols={face.manaCost} apiBase={apiBase} />
                  <span className="card-details__face-type">{face.cardType}</span>
                </div>
                <p className="card-details__description">
                  {face.description || "暂无描述"}
                </p>
              </div>
            </div>
          </article>
        ))}
      </div>
    </div>
  );
}
