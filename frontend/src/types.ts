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
  moxfieldDeckUrl?: string | null;
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

export type CardFetchStatus = "idle" | "running" | "success" | "error";

export type CardFetchLogLevel = "info" | "warning" | "error";

export interface CardFetchLogEntry {
  id: number;
  timestamp: number;
  level: CardFetchLogLevel;
  message: string;
  processed: number;
  total: number;
  updated: number;
  imagesDownloaded: number;
  cardName?: string | null;
  setCode?: string | null;
}

export interface CardFetchJobState {
  jobId: string | null;
  status: CardFetchStatus;
  logs: CardFetchLogEntry[];
  processed: number;
  total: number;
  updated: number;
  imagesDownloaded: number;
  result: CardFetchResponse | null;
  error: string | null;
}

export function createInitialCardFetchJobState(): CardFetchJobState {
  return {
    jobId: null,
    status: "idle",
    logs: [],
    processed: 0,
    total: 0,
    updated: 0,
    imagesDownloaded: 0,
    result: null,
    error: null,
  };
}

export interface MoxfieldFetchRequest {
  deckUrl: string;
  cardListName?: string;
}

export interface MoxfieldFetchResponse {
  cardsWritten: number;
  cardListPath: string;
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
