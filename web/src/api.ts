import createClient from "openapi-fetch";
import type { components, paths } from "./generated/api";

export type Schema<T extends keyof components["schemas"]> =
  components["schemas"][T];
let csrf: string | null = null;
export function setCsrf(value: string | null) {
  csrf = value;
}

export const api = createClient<paths>({
  // Browser API calls stay on this origin. Server/proxy owns session and routing.
  baseUrl: globalThis.location?.origin ?? "http://localhost",
  credentials: "same-origin",
  fetch: (request) => fetch(request),
});
api.use({
  onRequest({ request }) {
    if (!["GET", "HEAD"].includes(request.method) && csrf)
      request.headers.set("X-CSRF-Token", csrf);
    return new Request(request, {
      signal: AbortSignal.any([request.signal, AbortSignal.timeout(12000)]),
    });
  },
  onResponse({ response }) {
    if (response.status === 401) {
      setCsrf(null);
      window.dispatchEvent(new Event("oil-session-expired"));
    }
  },
});

export class ApiFailure extends Error {
  constructor(
    public status: number,
    public code: string,
  ) {
    super(
      status === 401
        ? "登录已失效，请重新登录。"
        : status === 403
          ? "当前账号没有此操作权限。"
          : status === 501 || code === "not_implemented"
            ? "此功能尚未配置，暂时不可用。"
            : status === 409
              ? "数据版本已变化，请刷新后重试。"
              : status === 422
                ? "提交内容未通过校验，请检查输入。"
                : status === 429
                  ? "请求较多，请稍后重试。"
                  : "服务暂时不可用，请稍后重试。",
    );
  }
}

export async function unwrap<T>(
  result: Promise<{ data?: T; error?: unknown; response: Response }>,
): Promise<T> {
  const { data, error, response } = await result;
  if (!response.ok || error) {
    const code =
      error && typeof error === "object" && "code" in error
        ? String(error.code)
        : "request_failed";
    throw new ApiFailure(response.status, code);
  }
  return data as T;
}

export function errorText(error: unknown): string {
  return error instanceof ApiFailure
    ? error.message
    : "网络连接失败或请求超时，请检查连接后重试。";
}

export function safeExternalUrl(value: string | null): string | null {
  if (!value) return null;
  try {
    const url = new URL(value);
    return ["https:", "http:"].includes(url.protocol) &&
      !url.username &&
      !url.password
      ? url.href
      : null;
  } catch {
    return null;
  }
}

export function loginUrl(value: string): string {
  const url = new URL(value);
  if (
    url.origin !== "https://accounts.feishu.cn" ||
    url.pathname !== "/open-apis/authen/v1/authorize"
  ) {
    throw new ApiFailure(501, "invalid_login_configuration");
  }
  return url.href;
}
