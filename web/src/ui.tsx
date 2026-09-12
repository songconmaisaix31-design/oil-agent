import { useEffect, useState } from "react";
import type { ReactNode } from "react";
import { api, errorText, safeExternalUrl, unwrap } from "./api";
import type { Schema } from "./api";

export const labels: Record<string, string> = {
  occurred: "已发生",
  planned: "计划中",
  denied: "已否认",
  unknown: "待核验",
  urgent: "紧急",
  important: "重要",
  routine: "一般",
  credible_single_source: "可信单源 · 待独立核实",
  publisher_statement: "发布方声明",
  independent_multi_source: "独立多源",
  conflicting: "证据冲突",
  corrected: "已更正",
  withdrawn: "已撤回",
  unverified: "未核验",
  dry_run: "演练 · 不外发",
  trial: "试运行 · 仅授权测试接收人",
  production: "生产模式",
  available: "正常",
  unavailable: "不可用",
  not_configured: "未配置",
  accepted: "平台已受理",
  acked: "已确认",
  in_flight: "提交中",
  pending: "待处理",
  failed_retryable: "发送失败 · 可重试",
  failed_final: "发送失败",
  valid: "有效",
  stale: "已过期",
  incomplete: "信息不完整",
  invalid: "无效",
  offer: "报价",
  transaction: "成交",
  indicative: "参考价",
  included: "含税",
  excluded: "未税",
  pickup: "自提",
  delivered: "送到",
  none: "无缺口",
  degraded: "降级",
  pagination_limit: "分页缺口",
  retention_exceeded: "历史缺口",
};
export const label = (value: string) => labels[value] ?? value;
export function time(value: string | null | undefined) {
  return value
    ? new Intl.DateTimeFormat("zh-CN", {
        timeZone: "Asia/Shanghai",
        month: "2-digit",
        day: "2-digit",
        hour: "2-digit",
        minute: "2-digit",
      }).format(new Date(value))
    : "未提供";
}

export function useLoad<T>(
  load: () => Promise<T>,
  dependencies: unknown[] = [],
) {
  const [data, setData] = useState<T>();
  const [error, setError] = useState<string>();
  const [loading, setLoading] = useState(true);
  const [version, setVersion] = useState(0);
  useEffect(() => {
    let active = true;
    setLoading(true);
    setError(undefined);
    setData(undefined);
    load()
      .then((value) => {
        if (active) setData(value);
      })
      .catch((reason) => {
        if (active) setError(errorText(reason));
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [...dependencies, version]);
  return { data, error, loading, reload: () => setVersion((v) => v + 1) };
}

export function Panel({
  title,
  children,
}: {
  title: string;
  children: ReactNode;
}) {
  return (
    <section className="panel">
      <h2>{title}</h2>
      {children}
    </section>
  );
}
export function State({
  resource,
}: {
  resource: { error?: string; loading: boolean; reload: () => void };
}) {
  if (resource.loading)
    return (
      <p className="muted" role="status">
        正在加载…
      </p>
    );
  if (resource.error)
    return (
      <div className="error" role="alert">
        {resource.error} <button onClick={resource.reload}>重试</button>
      </div>
    );
  return null;
}
export function Fixture({
  item,
}: {
  item: Pick<
    Schema<"EventAssessment">,
    "is_fixture" | "provenance" | "fixture_dataset"
  >;
}) {
  return item.is_fixture ? (
    <span className="badge fixture">演练数据 · {item.fixture_dataset}</span>
  ) : item.provenance === "trial" ? (
    <span className="badge">试运行 · 真实来源</span>
  ) : (
    <span className="badge">生产数据</span>
  );
}
export function EventSummary({ event }: { event: Schema<"EventAssessment"> }) {
  return (
    <a
      className="event-row"
      href={`#/events/${encodeURIComponent(event.event_id)}`}
    >
      <div className="tags">
        <span className={`badge ${event.severity}`}>
          {label(event.severity)}
        </span>
        <span className="muted">
          {label(event.assertion_status)} · v{event.revision}
        </span>
        <Fixture item={event} />
      </div>
      <h3>{event.title}</h3>
      <p>{label(event.evidence_status)}</p>
      <small>
        {time(event.assessed_at)} 研判 ·{" "}
        {event.origin_groups.map((g) => g.origin_publisher).join(" / ")}
      </small>
    </a>
  );
}

function EvidenceItem({ evidence }: { evidence: Schema<"EvidenceRef"> }) {
  const [open, setOpen] = useState(false);
  const [record, setRecord] = useState<Schema<"SourceRecord">>();
  const [error, setError] = useState<string>();
  const [loading, setLoading] = useState(false);
  async function inspect() {
    setOpen(true);
    setError(undefined);
    setLoading(true);
    try {
      setRecord(
        await unwrap(
          api.GET("/api/v1/records/{record_id}/revisions/{revision}", {
            params: {
              path: {
                record_id: evidence.record_id,
                revision: evidence.revision,
              },
            },
          }),
        ),
      );
    } catch (e) {
      setError(errorText(e));
    } finally {
      setLoading(false);
    }
  }
  const url = safeExternalUrl(record?.url ?? null);
  return (
    <div className="evidence">
      <blockquote>{evidence.excerpt}</blockquote>
      <small>
        {evidence.record_id} · v{evidence.revision} · {evidence.field}
      </small>
      <button className="text-button" onClick={inspect} disabled={loading}>
        核对原始记录
      </button>
      {open && (
        <div>
          {loading && <p role="status">读取来源中…</p>}
          {error && <p role="alert">{error}</p>}
          {record && (
            <>
              <Fixture item={record} />
              <p>
                {record.origin_publisher} · {record.title}
              </p>
              <p>
                发布时间：{time(record.published_at)} · 事件发生：
                {time(record.occurred_at)}
              </p>
              <p>
                发现时间：{time(record.discovered_at)} · 时间质量：
                {label(record.time_quality)}
              </p>
              {url ? (
                <a href={url} target="_blank" rel="noopener noreferrer">
                  查看原文 ↗
                </a>
              ) : (
                <p>未提供可访问的原文链接</p>
              )}
            </>
          )}
        </div>
      )}
    </div>
  );
}
export function Evidence({ items }: { items: Schema<"EvidenceRef">[] }) {
  return items.length ? (
    <div>
      {items.map((item, index) => (
        <EvidenceItem key={`${item.record_id}:${index}`} evidence={item} />
      ))}
    </div>
  ) : (
    <p className="muted">尚无可定位证据</p>
  );
}
