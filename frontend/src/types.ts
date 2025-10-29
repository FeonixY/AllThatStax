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

export interface LatexSettings {
  sheetFileName: string;
  sheetName: string;
  multifaceSheetName: string;
  latexTextName: string;
  latexFileName: string;
  latexCommand: string[];
}

export interface LatexGenerationRequest {
  sheetFileName: string;
  sheetName: string;
  multifaceSheetName: string;
  latexTextName: string;
  latexFileName: string;
  latexCommand?: string[];
  fetchCards?: boolean;
  fetchFromScratch?: boolean;
  localize?: boolean;
  skipCompile?: boolean;
}

export interface LatexGenerationResult {
  latexTextPath: string;
  pdfPath?: string | null;
  command: string[];
  stdout?: string | null;
  stderr?: string | null;
}

export const CARD_DRAG_MIME = "application/x-all-that-stax-card";

export type BinderSide = "front" | "back";

export type DragSource = "library" | "staging" | "binder";

export type DeckCounts = Record<string, number>;

export interface DragPayload {
  cardId: string;
  source: DragSource;
  binderPageIndex?: number;
  binderSide?: BinderSide;
  binderSlotIndex?: number;
  stagingIndex?: number;
}

export interface BinderPage {
  id: string;
  front: (string | null)[];
  back: (string | null)[];
}
