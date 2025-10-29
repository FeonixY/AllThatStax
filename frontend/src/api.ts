import {
  CardData,
  LatexGenerationRequest,
  LatexGenerationResult,
  LatexSettings,
  Metadata,
} from "./types";

const defaultApiBase = "";
const apiBase = import.meta.env.VITE_API_BASE_URL ?? defaultApiBase;

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${apiBase}${path}`, init);
  if (!response.ok) {
    throw new Error(`请求失败: ${response.status}`);
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
