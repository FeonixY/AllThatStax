export type ManaSymbol = string;

export interface CardFace {
  englishName: string;
  chineseName: string;
  image: string;
  manaCost: ManaSymbol[];
  cardType: string;
  description: string;
}

export interface StaxType {
  key: string;
  label: string;
}

export interface CardData {
  id: string;
  kind: "single" | "multiface";
  faces: CardFace[];
  staxType: StaxType | null;
  isRestricted: boolean;
  legalities: Record<string, string>;
  manaValue: number;
  sortCardType: string;
}

export interface Metadata {
  staxTypes: StaxType[];
  cardTypeOrder: string[];
}

export const CARD_DRAG_MIME = "application/x-all-that-stax-card";

export type BinderSide = "front" | "back";

export interface BinderPage {
  id: string;
  front: (string | null)[];
  back: (string | null)[];
}
