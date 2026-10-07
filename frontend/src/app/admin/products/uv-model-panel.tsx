"use client";

import { useEffect, useState } from "react";
import { RefreshCw, ShieldCheck, Undo2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import "./uv-model-panel.css";

type Score = { n: number; mae: number; bias: number; undercalls: Record<string, number> };
type Comparison = { candidate: Score; incumbent: Score; persistence: Score; passed: boolean };
type Overview = {
  active: string | null;
  previous: string | null;
  history: { from: string | null; to: string; actor: string; action: string; at: string }[];
  data_dates: Record<string, string>;
  forecast_generated_at: string | null;
  active_manifest: { trained_through: Record<string, string> } | null;
  pipeline: { status: string; at: string; message?: string } | null;
  monitoring: { status: string; alerts: string[]; label_corrections: string[] } | null;
  candidate: {
    version: string; can_promote: boolean; issue: string | null;
    gate: { passed: boolean; base_version: string; cities: Record<string, Record<string, Comparison>> } | null;
    tracking: { run_id: string } | null;
    evaluation: { cities: Record<string, { p90_absolute_error: number; max_absolute_error: number }> } | null;
  } | null;
};

const cities: Record<string, string> = { bangkok: "กรุงเทพฯ", songkhla: "สงขลา", chiang_mai: "เชียงใหม่" };
const statuses: Record<string, string> = {
  not_ready: "รอข้อมูลเพิ่ม", failed: "Pipeline ขัดข้อง", rejected: "ไม่ผ่านเกณฑ์คุณภาพ",
  awaiting_review: "รอผู้ดูแลตรวจและอนุมัติ", collecting: "กำลังสะสมผลจริง", ok: "อยู่ในเกณฑ์", alert: "พบการแจ้งเตือน",
};
const timestamp = (value?: string | null) => value ? new Date(value).toLocaleString("th-TH", { timeZone: "Asia/Bangkok" }) : "ยังไม่มีข้อมูล";
const decimal = (value: number) => value.toFixed(3);

async function requestOverview(body?: object) {
  const response = await fetch("/api/admin/uv", {
    method: body ? "POST" : "GET", cache: "no-store",
    headers: body ? { "Content-Type": "application/json" } : undefined,
    body: body ? JSON.stringify(body) : undefined,
  });
  const result = await response.json();
  if (!response.ok) throw new Error(typeof result.detail === "string" ? result.detail : "อ่านข้อมูล UV ไม่สำเร็จ");
  return result;
}

export function UvModelPanel() {
  const [data, setData] = useState<Overview | null>(null);
  const [busy, setBusy] = useState(true);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  useEffect(() => {
    let cancelled = false;
    requestOverview().then((result) => { if (!cancelled) setData(result); })
      .catch((reason) => { if (!cancelled) setError(reason.message); })
      .finally(() => { if (!cancelled) setBusy(false); });
    return () => { cancelled = true; };
  }, []);

  async function refresh() {
    setBusy(true); setError(""); setMessage("");
    try { setData(await requestOverview()); }
    catch (reason) { setError(reason instanceof Error ? reason.message : "โหลดข้อมูลไม่สำเร็จ"); }
    finally { setBusy(false); }
  }

  async function deploy(action: "promote" | "rollback", version: string) {
    if (!data?.active || !window.confirm(`${action === "promote" ? "อนุมัติใช้" : "ย้อนกลับไปใช้"}โมเดล ${version}?\nรุ่นปัจจุบัน: ${data.active}\nระบบจะบันทึกบัญชีแอดมินผู้ดำเนินการ`)) return;
    setBusy(true); setError(""); setMessage("");
    try {
      const result = await requestOverview({ action, version, expected_active: data.active });
      setMessage(`เปลี่ยนรุ่นใช้งานเป็น ${result.active} แล้ว · ผู้ดำเนินการ: ${result.actor}`);
      setData(null);
      setData(await requestOverview());
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "ทำรายการไม่สำเร็จ กรุณาโหลดข้อมูลใหม่");
    } finally { setBusy(false); }
  }

  const candidate = data?.candidate;
  const earliest = data?.pipeline?.message?.match(/Earliest test end: (\d{4}-\d{2}-\d{2})/)?.[1];

  return <section id="uv-models" className="uv-admin-panel" aria-labelledby="uv-admin-heading" aria-busy={busy}>
    <header className="uv-admin-header">
      <div><h2 id="uv-admin-heading">จัดการโมเดล UV</h2><p>UV ท้องฟ้าโปร่ง ณ เที่ยงสุริยะ · กรุงเทพฯ สงขลา และเชียงใหม่</p></div>
      <Button variant="outline" onClick={refresh} disabled={busy}><RefreshCw aria-hidden="true" />{busy ? "กำลังโหลด…" : "โหลดข้อมูลใหม่"}</Button>
    </header>
    {error && <p className="uv-admin-feedback" role="alert">{error} · กดโหลดข้อมูลใหม่เพื่อตรวจสถานะล่าสุด</p>}
    {message && <p className="uv-admin-feedback" role="status">{message}</p>}
    {!data && !error && <p role="status">กำลังอ่านสถานะโมเดล…</p>}
    {data && <>
      <dl className="uv-admin-status">
        <div><dt>รุ่นใช้งาน</dt><dd>{data.active ?? "ยังไม่มีรุ่นใน registry"}</dd></div>
        <div><dt>สถานะ retrain</dt><dd>{statuses[data.pipeline?.status ?? ""] ?? "ยังไม่มีบันทึก pipeline"}</dd><dd className="uv-admin-meta">ตรวจล่าสุด {timestamp(data.pipeline?.at)}</dd></div>
        <div><dt>ติดตามความแม่นยำ</dt><dd>{statuses[data.monitoring?.status ?? ""] ?? "ยังไม่มีผลติดตาม"}</dd><dd className="uv-admin-meta">สร้าง forecast ล่าสุด {timestamp(data.forecast_generated_at)}</dd></div>
      </dl>
      {data.pipeline?.status === "not_ready" && <p className="uv-admin-note">ต้องมีข้อมูลใหม่หลังวันฝึกโมเดลเดิมอย่างน้อย 15 วัน{earliest ? ` โดยข้อมูลต้องครบถึง ${earliest} เป็นอย่างน้อย` : ""} ระบบจะลองใหม่ตามรอบเมื่อบริการฝึกทำงานอยู่</p>}
      {data.pipeline?.status === "failed" && <p className="uv-admin-note">Pipeline ทำงานไม่สำเร็จ ผู้ดูแลควรตรวจ log ของบริการ uv-training ก่อนรอบถัดไป</p>}
      {data.monitoring?.status === "alert" && <div role="alert"><p>พบข้อควรตรวจสอบจาก monitoring</p><ul>{[...data.monitoring.alerts, ...data.monitoring.label_corrections].map((alert, index) => <li key={index}>{alert}</li>)}</ul></div>}
      <div className="uv-admin-table-wrap" tabIndex={0} role="region" aria-label="วันที่ข้อมูลแต่ละเมือง">
        <table><caption>ข้อมูลของรุ่นปัจจุบัน</caption><thead><tr><th scope="col">เมือง</th><th scope="col">ฝึกพารามิเตอร์ถึง</th><th scope="col">ข้อมูลที่ใช้ forecast ถึง</th></tr></thead><tbody>
          {Object.entries(cities).map(([city, label]) => <tr key={city}><th scope="row">{label}</th><td>{data.active_manifest?.trained_through[city] ?? "ยังไม่มีข้อมูล"}</td><td>{data.data_dates[city] ?? "ยังไม่มีข้อมูล"}</td></tr>)}
        </tbody></table>
      </div>
      <h3>Candidate ล่าสุด</h3>
      {!candidate ? <p className="uv-admin-note">ยังไม่มี candidate ให้ตรวจ ระบบจะเก็บรุ่นใหม่หลังมีข้อมูลเพียงพอและฝึกสำเร็จ</p> : <>
        <p className="uv-admin-version">{candidate.version}</p>
        <p>{candidate.can_promote ? "ผ่านเกณฑ์และพร้อมให้ผู้ดูแลตรวจอนุมัติ" : candidate.issue}</p>
        {candidate.gate && <>
          <p className="uv-admin-meta">เทียบกับ {candidate.gate.base_version} · MAE หน่วย UV ยิ่งต่ำยิ่งดี · ทุกเมืองและทั้งสองระยะต้องผ่าน</p>
          <div className="uv-admin-table-wrap" tabIndex={0} role="region" aria-label="เปรียบเทียบคุณภาพ candidate">
            <table><caption>ผลเปรียบเทียบบนชุดทดสอบเดียวกัน</caption><thead><tr>
              <th scope="col">เมือง / ระยะ</th><th scope="col">คู่ข้อมูล</th><th scope="col">MAE ใหม่</th><th scope="col">MAE เดิม</th><th scope="col">MAE ค่าล่าสุดซ้ำ</th><th scope="col">Bias ใหม่</th><th scope="col">พลาด ≥8 ใหม่ / เดิม</th><th scope="col">พลาด ≥11 ใหม่ / เดิม</th><th scope="col">ผล</th>
            </tr></thead><tbody>{Object.entries(candidate.gate.cities).flatMap(([city, horizons]) => Object.entries(horizons).map(([horizon, scores]) => <tr key={`${city}/${horizon}`}>
              <th scope="row">{cities[city] ?? city} / {horizon === "h1" ? "1 วัน" : "2 วัน"}</th><td>{scores.candidate.n}</td><td>{decimal(scores.candidate.mae)}</td><td>{decimal(scores.incumbent.mae)}</td><td>{decimal(scores.persistence.mae)}</td><td>{decimal(scores.candidate.bias)}</td><td>{scores.candidate.undercalls["8"]} / {scores.incumbent.undercalls["8"]}</td><td>{scores.candidate.undercalls["11"]} / {scores.incumbent.undercalls["11"]}</td><td>{scores.passed ? "ผ่าน" : "ไม่ผ่าน"}</td>
            </tr>))}</tbody></table>
          </div>
          <p className="uv-admin-meta">พลาดระดับสูง = ค่าจริงถึงระดับนั้น แต่โมเดลทำนายต่ำกว่า · Bias บวกหมายถึงทำนายสูงกว่าค่าจริง</p>
        </>}
        {candidate.evaluation && <details><summary>รายละเอียดความคลาดเคลื่อนล่วงหน้า 2 วัน</summary><ul>{Object.entries(candidate.evaluation.cities).map(([city, value]) => <li key={city}>{cities[city] ?? city}: คลาดเคลื่อน P90 {decimal(value.p90_absolute_error)} · สูงสุด {decimal(value.max_absolute_error)} UV</li>)}</ul></details>}
        {candidate.tracking && <p className="uv-admin-meta uv-admin-version">MLflow run: {candidate.tracking.run_id}</p>}
        <Button disabled={busy || Boolean(error) || !candidate.can_promote} onClick={() => deploy("promote", candidate.version)}><ShieldCheck aria-hidden="true" />อนุมัติใช้ candidate นี้</Button>
      </>}
      <div className="uv-admin-rollback"><div><h3>ย้อนกลับรุ่นก่อนหน้า</h3><p className="uv-admin-version">{data.previous ?? "ยังไม่มีรุ่นก่อนหน้าให้ย้อนกลับ"}</p></div><Button variant="outline" disabled={busy || Boolean(error) || !data.previous || !data.active} onClick={() => data.previous && deploy("rollback", data.previous)}><Undo2 aria-hidden="true" />ย้อนกลับรุ่นก่อนหน้า</Button></div>
      <details><summary>ประวัติการเปลี่ยนรุ่น ({data.history.length})</summary><ol className="uv-admin-history">{data.history.toReversed().map((entry, index) => <li key={`${entry.at}/${index}`}><strong>{entry.action === "bootstrap" ? "นำรุ่นเดิมเข้า registry" : entry.action === "promote" ? "อนุมัติใช้" : "ย้อนกลับ"}</strong> · {timestamp(entry.at)}<br /><span className="uv-admin-version">{entry.from ?? "ยังไม่มีรุ่น"} → {entry.to}</span><br />บัญชีผู้ดำเนินการ: {entry.actor || "ไม่มีบันทึก"}</li>)}</ol></details>
      <p className="uv-admin-note">การฝึกตามรอบไม่เปลี่ยนรุ่นใช้งานเอง ระบบตรวจ gate และความครบถ้วนซ้ำก่อนอนุมัติ พร้อมบันทึกบัญชีแอดมินและเวลา บัญชีที่ใช้ร่วมกันระบุได้เฉพาะบัญชี ไม่ใช่บุคคล</p>
    </>}
  </section>;
}
