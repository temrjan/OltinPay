// Server-only API client. Reads API_URL from server env; the browser never sees
// it — client components poll the same-origin /api/* proxy routes (spec: CORS /
// same-origin, review note #1). Do NOT import this from a client component.
import type { PorHistoryItem, PorResponse, RatesResponse } from "./types";

const API_URL = process.env.API_URL ?? "http://localhost:8000/api/v1";

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, { cache: "no-store" });
  if (!res.ok) {
    throw new Error(`Upstream ${path} responded ${res.status}`);
  }
  return (await res.json()) as T;
}

export const getPor = (): Promise<PorResponse> => get<PorResponse>("/por");

export const getRates = (): Promise<RatesResponse> =>
  get<RatesResponse>("/rates");

export const getHistory = (): Promise<PorHistoryItem[]> =>
  get<PorHistoryItem[]>("/por/history");
