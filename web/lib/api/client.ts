import createClient from "openapi-fetch";

import type { components, paths } from "./schema";

export type Schemas = components["schemas"];

export const api = createClient<paths>({ baseUrl: "/api" });

export class ApiError extends Error {
  constructor(
    readonly status: number,
    message: string,
  ) {
    super(message);
  }
}

export async function unwrap<T>(
  request: Promise<{ data?: T; error?: unknown; response: Response }>,
): Promise<T> {
  const { data, error, response } = await request;
  if (error !== undefined || !response.ok) {
    const detail = (error as { detail?: unknown } | undefined)?.detail;
    throw new ApiError(response.status, typeof detail === "string" ? detail : response.statusText);
  }
  // 204 responses have no body; their callers ignore the value.
  return data as T;
}
