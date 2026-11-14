import { API_BASE_URL } from "./config";

export class ApiError extends Error {
  readonly status: number;
  readonly endpoint: string;

  constructor(message: string, status: number, endpoint: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.endpoint = endpoint;
  }
}

export interface RequestOptions {
  timeoutMs?: number;
  cache?: RequestCache;
}

export async function apiGet<T>(
  endpoint: string,
  options: RequestOptions = {}
): Promise<T> {
  const timeoutMs = options.timeoutMs ?? 8000;
  const controller = new AbortController();

  const timeout = setTimeout(
    () => controller.abort(),
    timeoutMs
  );

  try {
    const response = await fetch(
      `${API_BASE_URL}${endpoint}`,
      {
        method: "GET",
        headers: {
          Accept: "application/json"
        },
        cache: options.cache ?? "no-store",
        signal: controller.signal
      }
    );

    if (!response.ok) {
      throw new ApiError(
        `Backend returned HTTP ${response.status}`,
        response.status,
        endpoint
      );
    }

    return (await response.json()) as T;
  } catch (error) {
    if (error instanceof ApiError) {
      throw error;
    }

    if (error instanceof Error && error.name === "AbortError") {
      throw new Error(`Request timed out: ${endpoint}`);
    }

    throw new Error(
      error instanceof Error
        ? error.message
        : `Request failed: ${endpoint}`
    );
  } finally {
    clearTimeout(timeout);
  }
}