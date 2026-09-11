import { useState } from "react";
import { api, errorText, unwrap } from "./api";
import type { Schema } from "./api";
import { Fixture, label, Panel, time } from "./ui";

const MAX_QUOTE_FILE_BYTES = 2_000_000;

const dimensions = [
  "product",
  "spec",
  "region",
  "supplier",
  "quote_type",
  "tax_basis",
  "delivery_basis",
  "currency",
  "unit",
] as const;
export function comparable(rows: Schema<"MarketObservation">[]): string {
  if (rows.length < 2) return "至少两条有效报价才能检查同口径";
  if (
    rows.some(
      (row) =>
        row.quality_state !== "valid" ||
        dimensions.some((k) => !row[k] || row[k] === "unknown"),
    )
  ) {
    return "不可比：存在缺失口径、无效或过期数据";
  }
  if (rows.some((row) => dimensions.some((k) => row[k] !== rows[0][k])))
    return "不可混算：产品、地区、供应商或税运单位口径不同";
  return "同口径检查通过；此处仅预览原值，不自动折算单位或计算价差";
}

async function readBase64(file: File): Promise<string> {
  if (file.size > MAX_QUOTE_FILE_BYTES) throw new Error("file_size");
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onerror = reject;
    reader.onload = () => resolve(String(reader.result).split(",")[1]);
    reader.readAsDataURL(file);
  });
}

export function Quotes({ admin }: { admin: boolean }) {
  const [file, setFile] = useState<File>();
  const [rights, setRights] = useState("");
  const [mapping, setMapping] = useState("{}");
  const [preview, setPreview] = useState<Schema<"QuotePreview">>();
  const [result, setResult] = useState<Schema<"QuoteImportResult">>();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string>();
  function clear() {
    setPreview(undefined);
    setResult(undefined);
    setError(undefined);
  }
  async function inspect() {
    if (!file || !admin) return;
    clear();
    setBusy(true);
    try {
      if (file.size > MAX_QUOTE_FILE_BYTES) {
        setError("文件超过 2 MB（2,000,000 字节），请缩小后重试。");
        return;
      }
      const extension = file.name.split(".").at(-1)?.toLowerCase();
      if (!["csv", "xlsx"].includes(extension ?? "")) {
        setError("仅支持 CSV 和 XLSX 文件。");
        return;
      }
      let fields: unknown;
      try {
        fields = JSON.parse(mapping);
      } catch {
        setError("字段映射需为 JSON 对象。");
        return;
      }
      if (
        !fields ||
        Array.isArray(fields) ||
        typeof fields !== "object" ||
        Object.values(fields).some((v) => typeof v !== "string")
      ) {
        setError("字段映射需使用字段名与列名字符串。");
        return;
      }
      const body: Schema<"QuotePreviewRequest"> = {
        filename: file.name,
        media_type:
          extension === "csv"
            ? "text/csv"
            : "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        content_base64: await readBase64(file),
        field_mapping: fields as Record<string, string>,
        rights_ref: rights.trim(),
      };
      setPreview(await unwrap(api.POST("/api/v1/quotes/preview", { body })));
    } catch (e) {
      setError(errorText(e));
    } finally {
      setBusy(false);
    }
  }
  async function importFile() {
    if (
      !preview?.can_import ||
      new Date(preview.expires_at) <= new Date() ||
      !admin ||
      result
    )
      return;
    setBusy(true);
    setError(undefined);
    try {
      setResult(
        await unwrap(
          api.POST("/api/v1/quotes/import", {
            body: { preview_id: preview.preview_id },
          }),
        ),
      );
    } catch (e) {
      setError(errorText(e));
    } finally {
      setBusy(false);
    }
  }
  return (
    <>
      <div className="page-heading">
        <p className="eyebrow">LOCAL QUOTES</p>
        <h1>报价导入</h1>
        <p>先核对原值、税运口径和授权，再保存。</p>
      </div>
      {!admin ? (
        <Panel title="需要管理员权限">
          <p>当前账号可以阅读预警与日报，报价导入由管理员操作。</p>
        </Panel>
      ) : (
        <>
          <Panel title="上传与字段映射">
            <label>
              报价文件（CSV / XLSX，最大 2 MB / 2,000,000 字节）
              <input
                type="file"
                accept=".csv,.xlsx"
                disabled={busy}
                onChange={(e) => {
                  clear();
                  setFile(e.target.files?.[0]);
                }}
              />
            </label>
            <label>
              数据使用授权或来源依据
              <input
                value={rights}
                maxLength={2000}
                disabled={busy}
                onChange={(e) => {
                  clear();
                  setRights(e.target.value);
                }}
                placeholder="填写已获准的来源或授权编号"
              />
            </label>
            <details>
              <summary>自定义字段映射</summary>
              <p>
                保持空对象可使用标准列名。需要映射时填写“标准字段名：文件列名”。
              </p>
              <textarea
                aria-label="字段映射 JSON"
                value={mapping}
                disabled={busy}
                onChange={(e) => {
                  clear();
                  setMapping(e.target.value);
                }}
                spellCheck={false}
              />
            </details>
            <p className="muted">
              文件由服务端安全校验；不会在浏览器执行表格公式。
            </p>
            <button
              className="primary"
              disabled={busy || !file || !rights.trim()}
              onClick={inspect}
            >
              校验并预览
            </button>
          </Panel>
          {preview && (
            <Panel title="导入前核对">
              <p>
                有效期至 {time(preview.expires_at)} · 重复行{" "}
                {preview.duplicate_rows.length}
              </p>
              <p className="notice">{comparable(preview.observations)}</p>
              {preview.issues.length > 0 && (
                <ul className="error">
                  {preview.issues.map((issue, index) => (
                    <li key={index}>
                      第 {issue.row_number} 行：{issue.message}（{issue.code}）
                    </li>
                  ))}
                </ul>
              )}
              {preview.observations.length ? (
                <div className="quotes">
                  {preview.observations.map((row) => (
                    <article key={row.observation_id} className="quote-row">
                      <Fixture item={row} />
                      <h3>
                        {row.product ?? "产品未提供"} ·{" "}
                        {row.spec ?? "规格未提供"}
                      </h3>
                      <strong>
                        {row.value} {row.currency ?? "币种未提供"} /{" "}
                        {row.unit ?? "单位未提供"}
                      </strong>
                      <p>
                        {row.region ?? "地区未提供"} ·{" "}
                        {row.supplier ?? "供应商未提供"}
                      </p>
                      <p>
                        {label(row.quote_type)} · {label(row.tax_basis)} ·{" "}
                        {label(row.delivery_basis)} · {label(row.quality_state)}
                      </p>
                      <small>
                        报价时间 {time(row.as_of)} · 来源 {row.source_record_id}
                      </small>
                    </article>
                  ))}
                </div>
              ) : (
                <p className="empty">没有可导入报价</p>
              )}
              {!preview.can_import && (
                <p className="notice">校验未通过，请修正文件后重新预览。</p>
              )}
              {new Date(preview.expires_at) <= new Date() && (
                <p className="error">预览已过期，请重新校验。</p>
              )}
              <button
                className="primary"
                disabled={
                  busy ||
                  !preview.can_import ||
                  !!result ||
                  new Date(preview.expires_at) <= new Date()
                }
                onClick={importFile}
              >
                {result ? "已导入" : "确认导入此预览"}
              </button>
            </Panel>
          )}
        </>
      )}
      {busy && <p role="status">正在处理，请稍候…</p>}
      {error && (
        <p className="error" role="alert">
          {error}
        </p>
      )}
      {result && (
        <p className="success" role="status">
          导入完成：新增 {result.imported_count} 条，重复{" "}
          {result.duplicate_count} 条。编号 {result.import_id}
        </p>
      )}
    </>
  );
}
