import { useEffect, useState } from "react";
import { api, errorText, loginUrl, setCsrf, unwrap } from "./api";
import type { Schema } from "./api";
import { Configuration } from "./config";
import { EventPage, Home, ReportPage, Reports } from "./pages";
import { Quotes } from "./quotes";

function route() {
  try {
    return new URL(location.hash.slice(1) || "/", location.origin);
  } catch {
    return new URL("/", location.origin);
  }
}
export function App() {
  const [session, setSession] = useState<Schema<"SessionResponse">>();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string>();
  const [busy, setBusy] = useState(false);
  const [path, setPath] = useState(route);
  useEffect(() => {
    const params = new URLSearchParams(location.search);
    const code = params.get("code");
    const state = params.get("state");
    const oauthReturn = ["code", "state", "error"].some((key) =>
      params.has(key),
    );
    const invalidReturn =
      oauthReturn &&
      (params.has("error") ||
        params.getAll("code").length !== 1 ||
        params.getAll("state").length !== 1 ||
        !code ||
        !state);
    // Remove transient OAuth values before rendering links or calling any third party.
    if (oauthReturn)
      history.replaceState(null, "", location.pathname + location.hash);
    const load = invalidReturn
      ? Promise.reject(new Error("invalid_oauth_return"))
      : code && state
        ? api.POST("/api/v1/session", { body: { code, state } })
        : api.GET("/api/v1/session");
    unwrap(load)
      .then((value) => {
        setSession(value);
        setCsrf(value.csrf_token ?? null);
      })
      .catch((e) =>
        setError(
          invalidReturn
            ? "登录未完成或返回信息无效，请重新使用飞书登录。"
            : errorText(e),
        ),
      )
      .finally(() => setLoading(false));
    const expired = () => {
      setSession(undefined);
      setCsrf(null);
      setError("登录已失效，请重新登录。");
    };
    const navigate = () => {
      setPath(route());
      window.scrollTo(0, 0);
    };
    window.addEventListener("oil-session-expired", expired);
    window.addEventListener("hashchange", navigate);
    return () => {
      window.removeEventListener("oil-session-expired", expired);
      window.removeEventListener("hashchange", navigate);
    };
  }, []);
  async function login() {
    setBusy(true);
    setError(undefined);
    try {
      const challenge = await unwrap(api.GET("/api/v1/session/challenge"));
      location.assign(loginUrl(challenge.authorization_url));
    } catch (e) {
      setError(errorText(e));
    } finally {
      setBusy(false);
    }
  }
  async function logout() {
    setBusy(true);
    setError(undefined);
    try {
      await unwrap(api.DELETE("/api/v1/session"));
      setSession(undefined);
      setCsrf(null);
    } catch (e) {
      setError(errorText(e));
    } finally {
      setBusy(false);
    }
  }
  const admin = session?.actor.role === "admin";
  const parts = path.pathname.split("/").filter(Boolean);
  const revision = Number(path.searchParams.get("revision")) || undefined;
  let page = <Home />;
  if (parts[0] === "events" && parts[1])
    page = (
      <EventPage
        key={`${parts[1]}:${revision}`}
        id={decodeURIComponent(parts[1])}
        requestedRevision={revision}
      />
    );
  else if (parts[0] === "reports")
    page = parts[1] ? (
      <ReportPage key={parts[1]} id={decodeURIComponent(parts[1])} />
    ) : (
      <Reports />
    );
  else if (parts[0] === "quotes") page = <Quotes admin={admin} />;
  else if (parts[0] === "config") page = <Configuration admin={admin} />;
  else if (parts[0])
    page = (
      <>
        <h1>页面不存在</h1>
        <a href="#/">返回首页</a>
      </>
    );
  return (
    <div className="app">
      <header className="app-header">
        <a href="#/" className="brand">
          <span className="brand-icon">油</span>
          <span>
            油讯<small>成品油预警</small>
          </span>
        </a>
        {session && (
          <div>
            <span className="role">{admin ? "管理员" : "查看者"}</span>
            <button className="text-button" onClick={logout} disabled={busy}>
              退出
            </button>
          </div>
        )}
      </header>
      {!session ? (
        <main className="login">
          <div className="eyebrow">EVIDENCE FIRST</div>
          <h1>
            把重要变化
            <br />
            看清楚。
          </h1>
          <p>
            重大事件、早间简报与可追溯的证据，
            <br />
            在一个清晰的工作台里。
          </p>
          {loading ? (
            <p role="status">正在检查会话…</p>
          ) : (
            <>
              <button className="primary" disabled={busy} onClick={login}>
                {busy ? "正在连接…" : "使用飞书登录"}
              </button>
              <p className="muted">
                需使用已获授权的账号。未配置飞书时暂不可登录。
              </p>
            </>
          )}
          {error && (
            <p className="error" role="alert">
              {error}
            </p>
          )}
        </main>
      ) : (
        <>
          <main key={session.actor.session_id}>
            {page}
            {error && (
              <p className="error" role="alert">
                {error}
              </p>
            )}
          </main>
          <nav aria-label="主导航">
            {[
              ["", "今日"],
              ["reports", "日报"],
              ["quotes", "报价"],
              ["config", "设置"],
            ].map(([href, title]) => (
              <a
                key={href}
                href={`#/${href}`}
                aria-current={(parts[0] ?? "") === href ? "page" : undefined}
              >
                {title}
              </a>
            ))}
          </nav>
        </>
      )}
      <footer>上海时间 UTC+8 · 平台受理与手机收到分别记录</footer>
    </div>
  );
}
