import { useState } from "react";
import { api, errorText, unwrap } from "./api";
import type { Schema } from "./api";
import { label, Panel, State, time, useLoad } from "./ui";

function ConfigForm({ initial }: { initial: Schema<"BusinessConfig"> }) {
  const [draft, setDraft] = useState(initial);
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<string>();
  const [error, setError] = useState<string>();
  const listFields = {
    regions: "关注地区",
    products: "关注产品",
    suppliers: "关注供应商",
    watched_events: "关注事件类型",
    recipient_ids: "已配置接收人 ID",
  } as const;
  async function save() {
    setBusy(true);
    setError(undefined);
    setResult(undefined);
    try {
      const body = { ...draft };
      for (const key of Object.keys(listFields) as (keyof typeof listFields)[])
        body[key] = (body[key] ?? []).map((v) => v.trim()).filter(Boolean);
      setDraft(await unwrap(api.PUT("/api/v1/config", { body })));
      setResult("配置已保存");
    } catch (e) {
      setError(errorText(e));
    } finally {
      setBusy(false);
    }
  }
  return (
    <>
      <p className="muted">多项用换行分隔。接收人必须已在服务端建立授权。</p>
      {(Object.keys(listFields) as (keyof typeof listFields)[]).map((key) => (
        <label key={key}>
          {listFields[key]}
          <textarea
            disabled={busy}
            value={(draft[key] ?? []).join("\n")}
            onChange={(e) => {
              setResult(undefined);
              setDraft({ ...draft, [key]: e.target.value.split("\n") });
            }}
          />
        </label>
      ))}
      <label>
        首报证据策略
        <select
          disabled={busy}
          value={draft.first_report_policy ?? ""}
          onChange={(e) =>
            setDraft({
              ...draft,
              first_report_policy:
                (e.target
                  .value as Schema<"BusinessConfig">["first_report_policy"]) ||
                null,
            })
          }
        >
          <option value="">未配置</option>
          <option value="credible_single_source">
            可信单源（标注待独立核实）
          </option>
          <option value="independent_only">仅独立多源</option>
        </select>
      </label>
      <label>
        日报时间（上海时间）
        <input
          type="time"
          disabled={busy}
          value={(draft.report_time ?? "06:00:00").slice(0, 5)}
          onChange={(e) =>
            setDraft({ ...draft, report_time: e.target.value + ":00" })
          }
        />
      </label>
      <p>
        通知模式：{label(draft.outbound_mode ?? "dry_run")} · 渠道：
        {draft.notification_channel === "feishu" ? "飞书" : "演练"}
      </p>
      <p>
        重复提醒：{draft.reminders_enabled ? "已开启" : "关闭"} · 短信：
        {draft.sms_enabled ? "已开启" : "关闭"} · 电话：
        {draft.phone_enabled ? "已开启" : "关闭"}
      </p>
      <p className="notice">
        真实外发、短信和电话需完成业务授权与实机验证，本页面暂不提供开启操作。
      </p>
      <button className="primary" disabled={busy} onClick={save}>
        {busy ? "保存中…" : "保存配置"}
      </button>
      {result && (
        <p className="success" role="status">
          {result}
        </p>
      )}
      {error && (
        <p className="error" role="alert">
          {error}
        </p>
      )}
    </>
  );
}
function AdminConfig() {
  const config = useLoad(() => unwrap(api.GET("/api/v1/config")));
  return (
    <Panel title="业务配置">
      <State resource={config} />
      {config.data && <ConfigForm initial={config.data} />}
    </Panel>
  );
}
export function Configuration({ admin }: { admin: boolean }) {
  const status = useLoad(() => unwrap(api.GET("/api/v1/status")));
  return (
    <>
      <div className="page-heading">
        <p className="eyebrow">WORKSPACE</p>
        <h1>配置与健康</h1>
        <p>查看运行状态，及时发现数据缺口。</p>
      </div>
      {admin ? (
        <AdminConfig />
      ) : (
        <p className="notice">当前为查看者，业务配置仅管理员可修改。</p>
      )}
      <Panel title="运行健康">
        <State resource={status} />
        {status.data && (
          <>
            <dl>
              <dt>数据库</dt>
              <dd>{label(status.data.database)}</dd>
              <dt>业务服务</dt>
              <dd>
                {status.data.business_api_implemented ? "已接入" : "尚未接入"}
              </dd>
              <dt>通知模式</dt>
              <dd>{label(status.data.outbound_mode)}</dd>
            </dl>
            {status.data.sources.length ? (
              status.data.sources.map((s) => (
                <article className="quote-row" key={s.source_id}>
                  <h3>
                    {s.source_id} · {label(s.gap_state)}
                  </h3>
                  <p>最近成功 {time(s.last_success_at)}</p>
                  <p>预计更新 {time(s.expected_next_at)}</p>
                  <p>{s.gap_reason}</p>
                </article>
              ))
            ) : (
              <p className="muted">暂无来源健康记录</p>
            )}
            {admin && (
              <>
                <h3>运行计数</h3>
                {Object.keys(status.data.counters ?? {}).length ? (
                  <dl>
                    {Object.entries(status.data.counters ?? {}).map(
                      ([k, v]) => (
                        <div key={k}>
                          <dt>{k}</dt>
                          <dd>{v}</dd>
                        </div>
                      ),
                    )}
                  </dl>
                ) : (
                  <p className="muted">暂无计数</p>
                )}
                {Object.entries(status.data.health ?? {}).map(([k, v]) => (
                  <p key={k}>
                    {k}：{label(v)}
                  </p>
                ))}
              </>
            )}
          </>
        )}
      </Panel>
    </>
  );
}
