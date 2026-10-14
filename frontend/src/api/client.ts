import type { ApiErrorBody, Place, TripAnalysis, TripRequest } from './types';

const BASE_URL = (import.meta.env.VITE_API_URL ?? '').replace(/\/$/, '');

export class ApiError extends Error {
  constructor(
    message: string,
    readonly code: string,
    readonly status: number,
  ) {
    super(message);
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${BASE_URL}${path}`, {
      headers: { 'Content-Type': 'application/json' },
      ...init,
    });
  } catch {
    throw new ApiError('Cannot reach the server. Check your connection.', 'network_error', 0);
  }
  if (!response.ok) {
    const body = (await response.json().catch(() => null)) as ApiErrorBody | null;
    throw new ApiError(
      describeError(body) ?? `Request failed (${response.status}).`,
      body?.error?.code ?? 'error',
      response.status,
    );
  }
  return (await response.json()) as T;
}

function describeError(body: ApiErrorBody | null): string | null {
  if (!body?.error) return null;
  const { message, details } = body.error;
  if (details && typeof details === 'object') {
    const first = Object.entries(details as Record<string, unknown>)[0];
    if (first) return `${first[0]}: ${JSON.stringify(first[1]).replace(/[[\]{}"]/g, '')}`;
  }
  return message;
}

export const api = {
  analyzeTrip: (payload: TripRequest, signal?: AbortSignal) =>
    request<TripAnalysis>('/api/trips/analyze/', {
      method: 'POST',
      body: JSON.stringify(payload),
      signal,
    }),
  autocomplete: (q: string, signal?: AbortSignal) =>
    request<Place[]>(`/api/geocode/autocomplete/?q=${encodeURIComponent(q)}`, { signal }),
};
