import { ManaSymbol } from "../types";
import { getManaImageUrl } from "../utils/mana";
import "./ManaCost.css";

interface ManaCostProps {
  symbols: ManaSymbol[];
  apiBase: string;
}

export function ManaCost({ symbols, apiBase }: ManaCostProps) {
  if (!symbols.length) {
    return <span className="mana-cost__none">-</span>;
  }

  return (
    <span className="mana-cost">
      {symbols.map((symbol, index) => {
        const normalised = symbol.toUpperCase();
        if (/^[A-Z0-9]{1,3}$/.test(normalised)) {
          return (
            <img
              key={`${symbol}-${index}`}
              src={getManaImageUrl(normalised, apiBase)}
              alt={normalised}
              className="mana-cost__icon"
            />
          );
        }
        return (
          <span key={`${symbol}-${index}`} className="mana-cost__text">
            {symbol}
          </span>
        );
      })}
    </span>
  );
}
