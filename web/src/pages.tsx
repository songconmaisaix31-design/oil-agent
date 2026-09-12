import { useState } from "react";
import { api, errorText, unwrap } from "./api";
import type { Schema } from "./api";
import {
  Evidence,
  EventSummary,
  Fixture,
  label,
  Panel,
  RuntimeClassification,
  State,
  time,
  useLoad,
} from "./ui";

export function Home() {
  const [cursor, setCursor] = useState<string>();
  const events = useLoad(
    () =>
      unwrap(
        api.GET("/api/v1/events", { params: { query: { limit: 20, cursor } } }),
      ),
    [cursor],
  );
  const reports = useLoad(() =>
    unwrap(api.GET("/api/v1/reports", { params: { query: { limit: 1 } } })),
  );
  const status = useLoad(() => unwrap(api.GET("/api/v1/status")));
  return (
    <>
      <div className="page-heading">
        <p className="eyebrow">MARKET WATCH</p>
        <h1>今日关注</h1>
        <p>保留来源，区分事实与判断。</p>
      </div>
      <Panel title="运行概况">
        <State resource={status} />
        {status.data && (
          <>
            <RuntimeClassification status={status.data} />
            <div className="status-grid">
              <div>
                <small>通知模式</small>
                <strong>{label(status.data.outbound_mode)}</strong>
              </div>
              <div>
                <small>数据库</small>
                <strong>{label(status.data.database)}</strong>
              </div>
            </div>
            {!status.data.business_api_implemented && (
              <p className="notice">业务服务尚未就绪</p>
            )}
            {status.data.sources.length ? (
              status.data.sources.map((s) => (
                <p key={s.source_id}>
                  {s.source_id} · {label(s.gap_state)} · 最近成功{" "}
                  {time(s.last_success_at)}
                  {s.expected_next_at &&
                    new Date(s.expected_next_at) < new Date() && (
                      <span className="badge urgent">更新已逾期</span>
                    )}
                </p>
              ))
            ) : (
              <p className="muted">暂无已接入来源，不能据此判断市场平静。</p>
            )}
          </>
        )}
      </Panel>
      <Panel title="事件动态">
        <State resource={events} />
        {events.data && (
          <>
            <p className="muted">
              数据截止：{time(events.data.data_cutoff_at)}（上海时间）
            </p>
            {events.data.items.length ? (
              [...events.data.items]
                .sort(
                  (a, b) =>
                    Number(b.severity === "urgent") -
                    Number(a.severity === "urgent"),
                )
                .map((e) => (
                  <EventSummary key={`${e.event_id}:${e.revision}`} event={e} />
                ))
            ) : (
              <p className="empty">
                暂无可见事件
                <br />
                <small>不代表无市场变化，请同时检查来源健康。</small>
              </p>
            )}
            <div className="actions">
              {cursor && (
                <button onClick={() => setCursor(undefined)}>返回最新</button>
              )}
              {events.data.next_cursor && (
                <button
                  onClick={() =>
                    setCursor(events.data?.next_cursor ?? undefined)
                  }
                >
                  下一页
                </button>
              )}
            </div>
          </>
        )}
      </Panel>
      <Panel title="最新日报">
        <State resource={reports} />
        {reports.data &&
          (reports.data.items.length ? (
            reports.data.items.map((r) => (
              <a
                className="event-row"
                key={r.report_id}
                href={`#/reports/${encodeURIComponent(r.report_id)}`}
              >
                <Fixture item={r} />
                <h3>
                  {r.report_date} 早间简报 · v{r.revision}
                </h3>
                <p>
                  截止 {time(r.cutoff_at)}{" "}
                  {r.delayed && <span className="badge">延迟生成</span>}
                </p>
              </a>
            ))
          ) : (
            <p className="empty">暂无已生成日报</p>
          ))}
      </Panel>
    </>
  );
}

export function EventPage({
  id,
  requestedRevision,
}: {
  id: string;
  requestedRevision?: number;
}) {
  const detail = useLoad(
    () =>
      unwrap(
        api.GET("/api/v1/events/{event_id}", {
          params: { path: { event_id: id } },
        }),
      ),
    [id],
  );
  const [selectedRevision, setSelectedRevision] = useState<number | undefined>(
    requestedRevision,
  );
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<string>();
  const [failure, setFailure] = useState<string>();
  const [feedback, setFeedback] = useState<Schema<"FeedbackKind">>("useful");
  const [comment, setComment] = useState("");
  const value = detail.data;
  const event =
    value &&
    (selectedRevision
      ? [value.current, ...value.timeline].find(
          (e) => e.revision === selectedRevision,
        )
      : value.current);
  const delivery = value?.deliveries.find(
    (d) =>
      d.revision === event?.revision &&
      ["accepted", "dry_run"].includes(d.state),
  );
  const current = event?.revision === value?.current.revision;
  async function mutate(kind: "ack" | "feedback") {
    if (!event) return;
    setBusy(true);
    setResult(undefined);
    setFailure(undefined);
    try {
      if (kind === "ack" && delivery) {
        const ack = await unwrap(
          api.POST("/api/v1/events/{event_id}/ack", {
            params: { path: { event_id: id } },
            body: {
              delivery_id: delivery.delivery_id,
              revision: event.revision,
            },
          }),
        );
        setResult(`已记录 v${ack.revision} 确认 · ${time(ack.ack_at)}`);
      } else if (kind === "feedback") {
        const saved = await unwrap(
          api.POST("/api/v1/events/{event_id}/feedback", {
            params: { path: { event_id: id } },
            body: { revision: event.revision, kind: feedback, comment },
          }),
        );
        setResult(`反馈已记录 · ${time(saved.created_at)}`);
      }
      detail.reload();
    } catch (e) {
      setFailure(errorText(e));
    } finally {
      setBusy(false);
    }
  }
  return (
    <>
      <a href="#/">← 今日关注</a>
      <h1>事件详情</h1>
      <State resource={detail} />
      {value && !event && (
        <p className="notice">
          该版本不存在或无权查看。
          <button onClick={() => setSelectedRevision(undefined)}>
            查看当前版本
          </button>
        </p>
      )}
      {event && value && (
        <>
          <Panel title={event.title}>
            <Fixture item={event} />
            <div className="tags">
              <span className={`badge ${event.severity}`}>
                {label(event.severity)}
              </span>
              <span>{label(event.assertion_status)}</span>
              <span>{label(event.evidence_status)}</span>
            </div>
            <p>
              版本 v{event.revision} · 研判时间 {time(event.assessed_at)}
            </p>
            {!current && (
              <p className="notice">
                正在查看历史版本；最新为 v{value.current.revision}。
              </p>
            )}
            <p>{event.change_summary}</p>
            <h3>影响判断</h3>
            {event.impact_path.length ? (
              <ul>
                {event.impact_path.map((t, i) => (
                  <li key={i}>{t}</li>
                ))}
              </ul>
            ) : (
              <p className="muted">暂未形成影响判断</p>
            )}
            <h3>仍待核实</h3>
            {event.unknowns.length ? (
              <ul>
                {event.unknowns.map((t, i) => (
                  <li key={i}>{t}</li>
                ))}
              </ul>
            ) : (
              <p className="muted">当前版本未列出待核实事项</p>
            )}
            <p>
              原始发布方：
              {event.origin_groups.map((g) => g.origin_publisher).join(" / ")}
            </p>
          </Panel>
          <Panel title="版本时间线">
            <div className="timeline">
              {[
                ...new Map(
                  [value.current, ...value.timeline].map((e) => [
                    e.revision,
                    e,
                  ]),
                ).values(),
              ]
                .sort((a, b) => b.revision - a.revision)
                .map((e) => (
                  <button
                    className="timeline-row"
                    key={e.revision}
                    onClick={() => {
                      setSelectedRevision(e.revision);
                      setResult(undefined);
                      setFailure(undefined);
                    }}
                    aria-pressed={e.revision === event.revision}
                  >
                    <strong>
                      v{e.revision} · {time(e.assessed_at)}
                    </strong>
                    <span>{e.change_summary}</span>
                  </button>
                ))}
            </div>
          </Panel>
          <Panel title="证据与来源">
            <Evidence items={event.evidence} />
          </Panel>
          <Panel title="确认与反馈">
            <p>确认仅针对所示版本，不等同于认同研判结论。</p>
            <p>
              {delivery
                ? `本次通知：${label(delivery.state)}`
                : "本版本暂无可确认的通知"}
            </p>
            <button
              className="primary"
              disabled={
                busy ||
                !current ||
                !value.can_ack ||
                !delivery ||
                value.acknowledged_revision === event.revision
              }
              onClick={() => mutate("ack")}
            >
              {value.acknowledged_revision === event.revision
                ? "本版本已确认"
                : `确认 v${event.revision}`}
            </button>
            {!current && (
              <p className="muted">
                历史版本保留供查阅，当前页面仅确认最新版本。
              </p>
            )}
            <div className="feedback">
              <label>
                反馈类型
                <select
                  value={feedback}
                  onChange={(e) =>
                    setFeedback(e.target.value as Schema<"FeedbackKind">)
                  }
                >
                  <option value="useful">有用</option>
                  <option value="irrelevant">无关</option>
                  <option value="error">内容有误</option>
                </select>
              </label>
              <label>
                补充说明
                <textarea
                  value={comment}
                  maxLength={2000}
                  onChange={(e) => setComment(e.target.value)}
                  placeholder="请描述具体信息或引用问题"
                />
              </label>
              <button
                disabled={busy || (feedback === "error" && !comment.trim())}
                onClick={() => mutate("feedback")}
              >
                提交反馈
              </button>
            </div>
          </Panel>
        </>
      )}
      {busy && <p role="status">正在提交…</p>}
      {result && (
        <p className="success" role="status">
          {result}
        </p>
      )}
      {failure && (
        <p className="error" role="alert">
          {failure}
        </p>
      )}
    </>
  );
}

function ReportContent({ report }: { report: Schema<"Report"> }) {
  return (
    <>
      <Panel title={`${report.report_date} 简报 · v${report.revision}`}>
        <Fixture item={report} />
        <p>
          数据截止：{time(report.cutoff_at)} · {report.timezone}
        </p>
        <p>
          生成时间：{time(report.created_at)} {report.delayed && "· 延迟生成"}
        </p>
        <h3>事实</h3>
        {report.facts.length ? (
          report.facts.map((f, i) => (
            <div key={i}>
              <p>{f.text}</p>
              <Evidence items={f.evidence} />
            </div>
          ))
        ) : (
          <p className="muted">暂无已引用事实</p>
        )}
        <h3>量化指标</h3>
        {report.computed_metrics.length ? (
          report.computed_metrics.map((m, i) => (
            <div className="metric" key={i}>
              <strong>
                {m.name}：{m.value ?? "缺数据"} {m.unit}
              </strong>
              <p>
                {label(m.quality_state)} · {time(m.as_of)}
              </p>
              <small>计算口径：{m.formula}</small>
              <Evidence items={m.evidence} />
            </div>
          ))
        ) : (
          <p className="muted">缺少可计算数据，不推断价格持平。</p>
        )}
        <h3>影响分析</h3>
        <ul>
          {report.impact_analysis.map((t, i) => (
            <li key={i}>{t}</li>
          ))}
        </ul>
        <h3>后续关注</h3>
        <ul>
          {report.watch_items.map((t, i) => (
            <li key={i}>{t}</li>
          ))}
        </ul>
        <h3>数据缺口</h3>
        {report.gaps.length ? (
          <ul>
            {report.gaps.map((t, i) => (
              <li key={i}>{t}</li>
            ))}
          </ul>
        ) : (
          <p className="muted">本报告未列出额外缺口</p>
        )}
      </Panel>
      <Panel title="全部证据">
        <Evidence items={report.evidence} />
      </Panel>
    </>
  );
}
export function ReportPage({ id }: { id: string }) {
  const report = useLoad(
    () =>
      unwrap(
        api.GET("/api/v1/reports/{report_id}", {
          params: { path: { report_id: id } },
        }),
      ),
    [id],
  );
  return (
    <>
      <a href="#/reports">← 日报历史</a>
      <h1>早间简报</h1>
      <State resource={report} />
      {report.data && <ReportContent report={report.data} />}
    </>
  );
}
export function Reports() {
  const [cursor, setCursor] = useState<string>();
  const reports = useLoad(
    () =>
      unwrap(
        api.GET("/api/v1/reports", {
          params: { query: { limit: 20, cursor } },
        }),
      ),
    [cursor],
  );
  return (
    <>
      <div className="page-heading">
        <p className="eyebrow">DAILY BRIEF</p>
        <h1>日报历史</h1>
        <p>按数据截止时间回看，不用今日信息改写昨日判断。</p>
      </div>
      <Panel title="已生成报告">
        <State resource={reports} />
        {reports.data && (
          <>
            {reports.data.items.length ? (
              reports.data.items.map((r) => (
                <a
                  className="event-row"
                  key={`${r.report_id}:${r.revision}`}
                  href={`#/reports/${encodeURIComponent(r.report_id)}`}
                >
                  <Fixture item={r} />
                  <h3>
                    {r.report_date} · v{r.revision}
                  </h3>
                  <p>
                    截止 {time(r.cutoff_at)} {r.delayed && "· 延迟"}
                  </p>
                </a>
              ))
            ) : (
              <p className="empty">暂无可见日报</p>
            )}
            <div className="actions">
              {cursor && (
                <button onClick={() => setCursor(undefined)}>返回最新</button>
              )}
              {reports.data.next_cursor && (
                <button
                  onClick={() =>
                    setCursor(reports.data?.next_cursor ?? undefined)
                  }
                >
                  下一页
                </button>
              )}
            </div>
          </>
        )}
      </Panel>
    </>
  );
}
