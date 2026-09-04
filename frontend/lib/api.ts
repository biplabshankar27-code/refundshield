import type {
  AuditEvent,
  BootstrapResponse,
  ClaimResultRow,
  RingDetectionResult,
} from "./types";

export const API_URL =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
    cache: "no-store",
  });
  if (!res.ok) {
    const detail = await res.text().catch(() => "");
    throw new Error(`${res.status} ${res.statusText}${detail ? ` — ${detail}` : ""}`);
  }
  return res.json() as Promise<T>;
}

export const api = {
  bootstrap: (force = false) =>
    request<BootstrapResponse>("/api/demo/bootstrap", {
      method: "POST",
      body: JSON.stringify(force ? { force_regenerate: true } : {}),
    }),

  claims: () => request<ClaimResultRow[]>("/api/claims/results?limit=400"),

  ringsLatest: () => request<RingDetectionResult | null>("/api/rings/latest"),

  audit: () => request<AuditEvent[]>("/api/audit?limit=60"),

  costOfDelay: () => request<Record<string, unknown>>("/api/demo/cost-of-delay"),
};
