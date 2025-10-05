import { ManaSymbol } from "../types";

export function getManaImageUrl(symbol: ManaSymbol, apiBase: string): string {
  return `${apiBase}/symbols/${symbol.toUpperCase()}.svg`;
}

export function getCmcGroup(value: number): string {
  if (value >= 7) {
    return "7+";
  }
  return String(value);
}
