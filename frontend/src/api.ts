import {
  CardData,
  CardFetchJobState,
  CardFetchRequest,
  CardFetchSettings,
  LatexGenerationRequest,
  LatexGenerationResult,
  LatexSettings,
  MoxfieldFetchRequest,
  MoxfieldFetchResponse,
  Metadata,
} from "./types";

const defaultApiBase = "";
const apiBase = import.meta.env.VITE_API_BASE_URL ?? defaultApiBase;

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${apiBase}${path}`, init);
  if (!response.ok) {
    let message = `请求失败: ${response.status}`;
    try {
      const data = await response.json();
      if (data && typeof data.detail === "string" && data.detail.trim()) {
        message = data.detail;
      }
    } catch {
      // ignore body parsing errors
    }
    throw new Error(message);
  }
  const contentType = response.headers.get("Content-Type");
  if (contentType && contentType.includes("application/json")) {
    return (await response.json()) as T;
  }
  return Promise.reject(new Error("响应格式不是 JSON"));
}

export function fetchCards(): Promise<CardData[]> {
  return request<CardData[]>("/cards");
}

export function fetchMetadata(): Promise<Metadata> {
  return request<Metadata>("/metadata");
}

export function fetchLatexSettings(): Promise<LatexSettings> {
  return request<LatexSettings>("/latex/settings");
}

export function generateLatex(
  payload: LatexGenerationRequest
): Promise<LatexGenerationResult> {
  return request<LatexGenerationResult>("/latex/generate", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });
}

export function fetchCardFetchSettings(): Promise<CardFetchSettings> {
  return request<CardFetchSettings>("/cards/fetch/settings");
}

export function fetchMoxfieldDeck(
  payload: MoxfieldFetchRequest
): Promise<MoxfieldFetchResponse> {
  return request<MoxfieldFetchResponse>("/cards/fetch/moxfield", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });
}

export function startCardFetch(
  payload: CardFetchRequest
): Promise<CardFetchJobState> {
  return request<CardFetchJobState>("/cards/fetch/start", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });
}

export function fetchCardFetchStatus(
  jobId?: string | null
): Promise<CardFetchJobState> {
  const query = jobId ? `?jobId=${encodeURIComponent(jobId)}` : "";
  return request<CardFetchJobState>(`/cards/fetch/status${query}`);
}
