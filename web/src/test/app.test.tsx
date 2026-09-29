import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { App } from "../App";
import { api, loginUrl, safeExternalUrl, setCsrf, unwrap } from "../api";
import type { Schema } from "../api";
import { EventPage, Home } from "../pages";
import { Quotes, comparable } from "../quotes";
import { Configuration } from "../config";

import { actor, event, detail, status, now } from "./fixtures";

function respond(data: unknown, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}
function mock(handler: (request: Request) => Response | Promise<Response>) {
  const fn = vi.fn(handler);
  vi.stubGlobal("fetch", fn);
  return fn;
}

describe("session and transport boundaries", () => {
  it("uses same-origin cookie and memory CSRF without caller identity or browser storage", async () => {
    const fetch = mock(() => respond({}));
    setCsrf("synthetic-csrf");
    await unwrap(
      api.POST("/api/v1/events/{event_id}/ack", {
        params: { path: { event_id: "e" } },
        body: { delivery_id: "d", revision: 1 },
      }),
    );
    const request = fetch.mock.calls[0][0];
    expect(request.credentials).toBe("same-origin");
    expect(request.headers.get("X-CSRF-Token")).toBe("synthetic-csrf");
    expect(new URL(request.url).origin).toBe(location.origin);
    expect(await request.clone().json()).toEqual({
      delivery_id: "d",
      revision: 1,
    });
    expect(localStorage.length).toBe(0);
    expect(sessionStorage.length).toBe(0);
  });
  it("shows unconfigured auth without claiming login success", async () => {
    mock((req) =>
      respond(
        {
          code: new URL(req.url).pathname.endsWith("challenge")
            ? "not_implemented"
            : "unauthorized",
          message: "DO NOT ECHO TOKEN",
        },
        new URL(req.url).pathname.endsWith("challenge") ? 501 : 401,
      ),
    );
    render(<App />);
    await userEvent.click(
      await screen.findByRole("button", { name: "使用飞书登录" }),
    );
    expect(
      await screen.findByText("此功能尚未配置，暂时不可用。"),
    ).toBeInTheDocument();
    expect(screen.queryByText("DO NOT ECHO TOKEN")).not.toBeInTheDocument();
    expect(screen.queryByRole("navigation")).not.toBeInTheDocument();
  });
  it("removes OAuth query before exchanging code and keeps tokens out of storage", async () => {
    history.replaceState(
      null,
      "",
      "/?code=synthetic-code&state=synthetic-state-0001",
    );
    const fetch = mock(async (req) => {
      expect(location.search).toBe("");
      if (req.method === "POST") {
        expect(await req.clone().json()).toEqual({
          code: "synthetic-code",
          state: "synthetic-state-0001",
        });
        return respond({ actor, csrf_token: "synthetic-csrf" });
      }
      if (req.url.endsWith("/status")) return respond(status);
      return respond({ items: [], next_cursor: null, data_cutoff_at: null });
    });
    render(<App />);
    expect(await screen.findByRole("navigation")).toBeInTheDocument();
    expect(
      fetch.mock.calls.filter(([req]) => req.method === "POST"),
    ).toHaveLength(1);
    expect(localStorage.length).toBe(0);
    expect(sessionStorage.length).toBe(0);
  });
  it("rejects unsafe evidence and login redirect protocols", () => {
    expect(safeExternalUrl("javascript:alert(1)")).toBeNull();
    expect(safeExternalUrl("https://user:pass@example.invalid")).toBeNull();
    expect(() => loginUrl("https://evil.invalid/?code=1")).toThrow();
    expect(safeExternalUrl("https://example.invalid/source")).toBe(
      "https://example.invalid/source",
    );
  });
  it.each([
    "error=access_denied&error_description=PRIVATE",
    "code=PRIVATE",
    "state=PRIVATE",
    "code=first&code=PRIVATE&state=state",
    "code=code&state=first&state=PRIVATE",
  ])(
    "rejects incomplete or ambiguous OAuth returns without API calls: %s",
    async (query) => {
      history.replaceState(null, "", `/?${query}`);
      const fetch = mock(() => respond({ actor }));
      render(<App />);
      expect(await screen.findByRole("alert")).toHaveTextContent(
        "登录未完成或返回信息无效，请重新使用飞书登录。",
      );
      expect(location.search).toBe("");
      expect(fetch).not.toHaveBeenCalled();
      expect(screen.queryByRole("navigation")).not.toBeInTheDocument();
      expect(document.body.textContent).not.toContain("PRIVATE");
    },
  );
});

describe("runtime classification", () => {
  it.each([
    ["fixture", "合成演练数据"],
    ["trial", "试运行 · 真实来源"],
    ["production", "生产数据"],
  ] as const)(
    "keeps %s data separate from production acceptance and an empty market",
    async (provenance, text) => {
      const value: Schema<"RuntimeStatus"> = {
        ...status,
        data_provenance: provenance,
        outbound_mode: provenance === "trial" ? "trial" : "dry_run",
        production_accepted: false,
      };
      mock((req) =>
        req.url.endsWith("/status")
          ? respond(value)
          : respond({ items: [], next_cursor: null, data_cutoff_at: null }),
      );
      render(<Home />);
      expect(
        await screen.findByText(`数据性质：${text} · 尚未完成生产验收`),
      ).toBeInTheDocument();
      expect(await screen.findByText("暂无可见事件")).toBeInTheDocument();
      if (provenance === "trial")
        expect(
          screen.getByText("试运行 · 仅授权测试接收人"),
        ).toBeInTheDocument();
    },
  );
  it.each([true, false])(
    "shows permission configuration only for admin=%s without claiming real acceptance",
    async (admin) => {
      mock((req) =>
        req.url.endsWith("/status")
          ? respond({
              ...status,
              permissions: {
                source_requests: false,
                real_identity: true,
                production_accepted: false,
              },
            })
          : respond({ code: "not_implemented" }, 501),
      );
      render(<Configuration admin={admin} />);
      await screen.findByText(/数据性质：合成演练数据/);
      expect(
        screen.queryByRole("heading", { name: "授权配置状态" }) !== null,
      ).toBe(admin);
      if (admin) {
        expect(
          screen.getByText("来源请求").nextElementSibling,
        ).toHaveTextContent("未就绪");
        expect(
          screen.getByText("飞书身份登录").nextElementSibling,
        ).toHaveTextContent("配置有效");
        expect(
          screen.getByText(/配置有效不代表实机验证通过/),
        ).toBeInTheDocument();
      } else {
        expect(screen.queryByText("飞书身份登录")).not.toBeInTheDocument();
      }
    },
  );
});

describe("business views", () => {
  it("distinguishes empty data from healthy market and keeps dry-run visible", async () => {
    mock((req) =>
      req.url.endsWith("/status")
        ? respond(status)
        : respond({ items: [], next_cursor: null, data_cutoff_at: null }),
    );
    render(<Home />);
    expect(await screen.findByText("暂无可见事件")).toBeInTheDocument();
    expect(await screen.findByText("暂无已生成日报")).toBeInTheDocument();
    expect(screen.getByText("演练 · 不外发")).toBeInTheDocument();
    expect(
      screen.getByText("暂无已接入来源，不能据此判断市场平静。"),
    ).toBeInTheDocument();
  });
  it("shows loading until data arrives", async () => {
    let finish: (response: Response) => void = () => {};
    const fetch = mock(
      () =>
        new Promise((resolve) => {
          finish = resolve;
        }),
    );
    render(<EventPage id="fixture-event" />);
    expect(screen.getByRole("status")).toHaveTextContent("正在加载");
    await waitFor(() => expect(fetch).toHaveBeenCalledTimes(1));
    finish(respond(detail));
    expect(await screen.findByText("Synthetic test event")).toBeInTheDocument();
  });
  it("uses exact delivery/revision, preserves failure and never shows fake acknowledgement", async () => {
    const fetch = mock((req) =>
      req.method === "POST"
        ? respond({ code: "revision_mismatch" }, 409)
        : respond(detail),
    );
    render(<EventPage id="fixture-event" />);
    await userEvent.click(
      await screen.findByRole("button", { name: "确认 v2" }),
    );
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "数据版本已变化",
    );
    expect(screen.queryByText(/已记录 v2 确认/)).not.toBeInTheDocument();
    const request = fetch.mock.calls.find(([req]) => req.method === "POST")![0];
    expect(await request.clone().json()).toEqual({
      delivery_id: "fixture-delivery",
      revision: 2,
    });
    expect(screen.getByText("演练数据 · web-unit")).toBeInTheDocument();
  });
  it("retains historical revision with acknowledgement disabled", async () => {
    mock(() => respond(detail));
    render(<EventPage id="fixture-event" requestedRevision={1} />);
    expect(
      await screen.findByText("正在查看历史版本；最新为 v2。"),
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "确认 v1" })).toBeDisabled();
    expect(screen.getByText("计划中")).toBeInTheDocument();
  });
  it("does not request admin configuration or expose import actions to viewers", async () => {
    const fetch = mock(() => respond(status));
    const view = render(<Configuration admin={false} />);
    expect(
      await screen.findByText("当前为查看者，业务配置仅管理员可修改。"),
    ).toBeInTheDocument();
    await waitFor(() => expect(fetch).toHaveBeenCalled());
    expect(fetch.mock.calls.every(([req]) => req.url.endsWith("/status"))).toBe(
      true,
    );
    view.unmount();
    render(<Quotes admin={false} />);
    expect(screen.getByText("需要管理员权限")).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "确认导入此预览" }),
    ).not.toBeInTheDocument();
  });
  it("only records import success from a successful API result", async () => {
    const preview: Schema<"QuotePreview"> = {
      preview_id: "fixture-preview",
      file_hash: "a".repeat(64),
      observations: [],
      issues: [],
      duplicate_rows: [],
      expires_at: "2099-01-01T00:00:00Z",
      can_import: true,
    };
    const fetch = mock((req) =>
      req.url.endsWith("/preview")
        ? respond(preview)
        : respond({ code: "preview_expired" }, 409),
    );
    render(<Quotes admin />);
    await userEvent.upload(
      screen.getByLabelText(/报价文件/),
      new File(["product,value\nDiesel,7000"], "synthetic.csv", {
        type: "text/csv",
      }),
    );
    await userEvent.type(
      screen.getByLabelText("数据使用授权或来源依据"),
      "fixture:synthetic",
    );
    await userEvent.click(screen.getByRole("button", { name: "校验并预览" }));
    await userEvent.click(
      await screen.findByRole("button", { name: "确认导入此预览" }),
    );
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "数据版本已变化",
    );
    expect(screen.queryByText(/导入完成/)).not.toBeInTheDocument();
    const request = fetch.mock.calls.find(([req]) =>
      req.url.endsWith("/import"),
    )![0];
    expect(await request.clone().json()).toEqual({
      preview_id: "fixture-preview",
    });
  });
  it("submits a quote file of exactly 2000000 bytes to the preview API", async () => {
    const fetch = mock(() => respond({ code: "not_implemented" }, 501));
    render(<Quotes admin />);
    await userEvent.upload(
      screen.getByLabelText(/报价文件/),
      new File(["x".repeat(2_000_000)], "boundary.csv", { type: "text/csv" }),
    );
    await userEvent.type(
      screen.getByLabelText("数据使用授权或来源依据"),
      "fixture:boundary",
    );
    await userEvent.click(screen.getByRole("button", { name: "校验并预览" }));
    await waitFor(() => expect(fetch).toHaveBeenCalledTimes(1));
    const request = fetch.mock.calls[0][0];
    expect(new URL(request.url).pathname).toBe("/api/v1/quotes/preview");
    expect(request.method).toBe("POST");
    const body: Schema<"QuotePreviewRequest"> = await request.clone().json();
    expect(atob(body.content_base64)).toHaveLength(2_000_000);
    expect(body.filename).toBe("boundary.csv");
    expect(body.media_type).toBe("text/csv");
    expect(body.rights_ref).toBe("fixture:boundary");
    expect(body.field_mapping).toEqual({});
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "此功能尚未配置，暂时不可用。",
    );
  });
  it("rejects a quote file of 2000001 bytes before reading or invoking the API", async () => {
    const fetch = mock(() => respond({ code: "not_implemented" }, 501));
    const read = vi.spyOn(FileReader.prototype, "readAsDataURL");
    render(<Quotes admin />);
    await userEvent.upload(
      screen.getByLabelText(/报价文件/),
      new File(["x".repeat(2_000_001)], "oversized.csv", { type: "text/csv" }),
    );
    await userEvent.type(
      screen.getByLabelText("数据使用授权或来源依据"),
      "fixture:boundary",
    );
    await userEvent.click(screen.getByRole("button", { name: "校验并预览" }));
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "文件超过 2 MB（2,000,000 字节），请缩小后重试。",
    );
    expect(fetch).not.toHaveBeenCalled();
    expect(read).not.toHaveBeenCalled();
    expect(screen.getByLabelText(/报价文件/)).toHaveAccessibleName(
      "报价文件（CSV / XLSX，最大 2 MB / 2,000,000 字节）",
    );
  });
});

it("checks all quote dimensions without float conversion or fabricated zero changes", () => {
  const row: Schema<"MarketObservation"> = {
    observation_id: "fixture-quote",
    revision: 1,
    product: "Diesel",
    spec: "0",
    region: "R",
    supplier: "S",
    quote_type: "offer",
    tax_basis: "included",
    delivery_basis: "pickup",
    currency: "CNY",
    unit: "tonne",
    value: "7000.000001",
    as_of: now,
    published_at: now,
    source_record_id: "fixture-record",
    evidence: event.evidence[0],
    quality_state: "valid",
    is_fixture: true,
    provenance: "fixture",
    fixture_dataset: "web-unit",
  };
  expect(comparable([row, { ...row, unit: "litre" }])).toMatch("不可混算");
  expect(comparable([row, { ...row, tax_basis: "unknown" }])).toMatch("不可比");
  expect(comparable([row, { ...row, value: "7000.000002" }])).toMatch(
    "同口径检查通过",
  );
  expect(row.value).toBe("7000.000001");
});
