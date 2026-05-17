import { operations, type ApiOperation } from "@truecare/api-client";

export type ApiErrorBody = {
  code?: string;
  detail?: string;
  status?: number;
  title?: string;
};

export class ApiProblem extends Error {
  status: number;
  body: ApiErrorBody;

  constructor(status: number, body: ApiErrorBody) {
    super(body.detail || body.code || `HTTP ${status}`);
    this.status = status;
    this.body = body;
  }
}

const byOperationId = new Map<string, ApiOperation>(
  operations.map((operation) => [operation.operationId, operation])
);

export const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";

export function operationPath(operationId: string, params: Record<string, string> = {}) {
  const operation = byOperationId.get(operationId);
  if (!operation) {
    throw new Error(`Unknown API operation: ${operationId}`);
  }
  return operation.path.replace(/\{([^}]+)\}/g, (_, key: string) => {
    const value = params[key];
    if (!value) {
      throw new Error(`Missing path param '${key}' for ${operationId}`);
    }
    return encodeURIComponent(value);
  });
}

export async function apiRequest<T>(
  operationId: string,
  options: {
    params?: Record<string, string>;
    query?: Record<string, string | number | boolean | undefined | null>;
    body?: unknown;
    token?: string | null;
  } = {}
): Promise<T> {
  const operation = byOperationId.get(operationId);
  if (!operation) {
    throw new Error(`Unknown API operation: ${operationId}`);
  }
  const url = new URL(operationPath(operationId, options.params), apiBaseUrl);
  for (const [key, value] of Object.entries(options.query || {})) {
    if (value !== undefined && value !== null) {
      url.searchParams.set(key, String(value));
    }
  }

  const response = await fetch(url.toString(), {
    method: operation.method,
    headers: {
      "content-type": "application/json",
      ...(options.token ? { authorization: `Bearer ${options.token}` } : {})
    },
    body: options.body === undefined ? undefined : JSON.stringify(options.body)
  });

  if (!response.ok) {
    let body: ApiErrorBody = {};
    try {
      body = await response.json();
    } catch {
      body = { detail: response.statusText };
    }
    throw new ApiProblem(response.status, body);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  const text = await response.text();
  return (text ? JSON.parse(text) : undefined) as T;
}
