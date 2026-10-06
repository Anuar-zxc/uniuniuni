// Thin typed fetch wrapper. Same-origin /api (proxied by Next) so the httpOnly session cookie is sent automatically.

export class ApiError extends Error {
  status: number;
  detail: unknown;
  constructor(status: number, detail: unknown, message: string) {
    super(message);
    this.status = status;
    this.detail = detail;
  }
}

const BASE = "/api/v1";

async function request<T>(method: string, path: string, body?: unknown, isForm = false, redirectOn401 = true): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method,
    credentials: "include",
    headers: isForm || body === undefined ? undefined : { "Content-Type": "application/json" },
    body: body === undefined ? undefined : isForm ? (body as FormData) : JSON.stringify(body),
  });
  if (!res.ok) {
    let detail: unknown = null;
    try {
      detail = (await res.json()).detail;
    } catch {
      /* non-JSON error */
    }
    const msg =
      typeof detail === "string"
        ? detail
        : Array.isArray(detail)
          ? detail.map((d: { msg?: string }) => d.msg).join("; ")
          : (detail as { message?: string } | null)?.message ?? res.statusText;
    if (res.status === 401 && redirectOn401 && typeof window !== "undefined" && !path.startsWith("/auth/")) {
      const next = encodeURIComponent(window.location.pathname);
      window.location.href = `/login?next=${next}`;
    }
    throw new ApiError(res.status, detail, msg);
  }
  return (await res.json()) as T;
}

export const api = {
  get: <T>(p: string) => request<T>("GET", p),
  /** GET that never redirects to /login (for public pages that adapt when signed in). */
  peek: <T>(p: string) => request<T>("GET", p, undefined, false, false),
  post: <T>(p: string, body?: unknown) => request<T>("POST", p, body ?? {}),
  put: <T>(p: string, body: unknown) => request<T>("PUT", p, body),
  patch: <T>(p: string, body: unknown) => request<T>("PATCH", p, body),
  del: <T>(p: string) => request<T>("DELETE", p),
  upload: <T>(p: string, form: FormData) => request<T>("POST", p, form, true),
};

export function isQuotaError(e: unknown): boolean {
  return e instanceof ApiError && e.status === 402;
}
