import { CardData, Metadata } from "./types";

const defaultApiBase = "";
const apiBase = import.meta.env.VITE_API_BASE_URL ?? defaultApiBase;

async function request<T>(path: string): Promise<T> {
  const response = await fetch(`${apiBase}${path}`);
  if (!response.ok) {
    throw new Error(`请求失败: ${response.status}`);
  }
  return (await response.json()) as T;
}

export function fetchCards(): Promise<CardData[]> {
  return request<CardData[]>("/cards");
}

export function fetchMetadata(): Promise<Metadata> {
  return request<Metadata>("/metadata");
}
