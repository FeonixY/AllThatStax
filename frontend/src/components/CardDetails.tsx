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
  const legalityEntries = Object.entries(card.legalities ?? {});

  const allowedFormats = new Map<string, string>([
    ["standard", "标准"],
    ["pioneer", "先驱"],
    ["modern", "摩登"],
    ["legacy", "薪传"],
    ["vintage", "特选"],
    ["commander", "官禁"],
    ["duel_commander", "法禁"],
    ["pauper", "纯铁"],
  ]);

  const statusLabels: Record<string, string> = {
    legal: "合法",
    not_legal: "非法",
    banned: "禁用",
    restricted: "限制",
    suspended: "暂停",
    playable: "可用",
    unknown: "未知",
  };

  const normaliseStatus = (value: string) => {
    const key = value.toLowerCase();
    return statusLabels[key] ?? value;
  };

  const displayedLegalities = legalityEntries.filter(([format]) =>
    allowedFormats.has(format)
  );

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

      <section className="card-details__section">
        <h4>赛制合法性</h4>
        <ul className="card-details__legalities">
          {displayedLegalities.map(([format, state]) => {
            const stateLabel = normaliseStatus(state);
            const classState = state.toLowerCase().replace(/[^a-z_]/g, "-");
            return (
              <li key={format} className="card-details__legal-item">
                <span
                  className={`card-details__legal-state card-details__legal-state--${classState}`}
                >
                  {stateLabel}
                </span>
                <span className="card-details__legal-format">
                  {allowedFormats.get(format) ?? format}
                </span>
              </li>
            );
          })}
        </ul>
      </section>

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
