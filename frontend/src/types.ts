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
  dataFileName: string;
  latexTextName: string;
  latexFileName: string;
  latexCommand: string[];
}

export interface LatexGenerationRequest {
  dataFileName: string;
  latexTextName: string;
  latexFileName: string;
  latexCommand?: string[];
  fetchCards?: boolean;
  fetchFromScratch?: boolean;
  downloadImages?: boolean;
  skipCompile?: boolean;
}

export interface LatexGenerationResult {
  latexTextPath: string;
  pdfPath?: string | null;
  command: string[];
  stdout?: string | null;
  stderr?: string | null;
}

export interface CardFetchSettings {
  cardListName: string;
  dataFileName: string;
  imageFolderName: string;
  downloadImages: boolean;
}

export interface CardFetchRequest {
  cardListName: string;
  dataFileName: string;
  imageFolderName: string;
  fromScratch: boolean;
  downloadImages: boolean;
}

export interface CardFetchResponse {
  cardsProcessed: number;
  cardsUpdated: number;
  imagesDownloaded: number;
  errors: string[];
  dataFile: string;
  duration: number;
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
