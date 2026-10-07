"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";
import { RefreshCw, Play, ShieldCheck, Undo2, ExternalLink } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import "./uv-model-panel.css";
import "./wrinkle-model-panel.css";

type Metrics = Record<string, number>;
type Run = {
  id: string; status: string; dataset_uri: string; mlflow_run_id: string | null;
  epochs: number | null; epoch: number | null; loss: number | null; base_version: string | null;
  error: string | null; actor: string | null;
  evaluation: { candidate: Metrics; baseline: Metrics } | null;
  gate: { passed: boolean; reasons: string[] } | null;
};
type Dataset = { uri: string; name: string; subjects: number; counts: Record<string, number>; expires_at: string | null };
type ReviewTask = { id: string; label_studio_task_id: number; split: "train" | "validation" | "test" };
type Overview = {
  active: string; pending: { version: string } | null; error: string | null;
  loaded?: { version: string; at: string };
  history: { from: string; to: string; actor: string; action: string; at: string }[];
  datasets: Dataset[]; runs: Run[]; review_tasks: ReviewTask[];
};
const statuses: Record<string, string> = {
  queued: "รอคิว", running: "กำลังทำงาน", failed: "ไม่สำเร็จ", ready: "ชุดข้อมูลพร้อม",
  awaiting_approval: "รอตรวจและอนุมัติ", awaiting_model_package: "รอแพ็กเกจโมเดล",
};
const labelVersion = (version: string) => version === "initial" ? "รุ่นเริ่มต้น" : version;

async function request(body?: object): Promise<Overview> {
  const response = await fetch("/api/admin/wrinkle", {
    method: body ? "POST" : "GET", cache: "no-store",
    headers: body ? { "Content-Type": "application/json" } : undefined,
    body: body ? JSON.stringify(body) : undefined,
  });
  const result = await response.json();
  if (!response.ok) throw new Error(typeof result.detail === "string" ? result.detail : "อ่านสถานะ Wrinkle ไม่สำเร็จ");
  return result;
}

export function WrinkleModelPanel() {
  const [data, setData] = useState<Overview | null>(null);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  const [dataset, setDataset] = useState("");
  const [annotations, setAnnotations] = useState<Record<string, string>>({});
  const refresh = useCallback(async () => {
    try { setData(await request()); setError(""); }
    catch (reason) { setError(reason instanceof Error ? reason.message : "โหลดสถานะไม่สำเร็จ"); }
  }, []);
  useEffect(() => {
    let cancelled = false;
    request().then(result => { if (!cancelled) setData(result); })
      .catch(reason => { if (!cancelled) setError(reason instanceof Error ? reason.message : "โหลดสถานะไม่สำเร็จ"); });
    return () => { cancelled = true; };
  }, []);
  const working = Boolean(data?.pending || data?.runs.some(run => ["queued", "running"].includes(run.status)));
  useEffect(() => {
    if (!working || error) return;
    const timer = window.setInterval(() => void refresh(), 5000);
    return () => window.clearInterval(timer);
  }, [working, error, refresh]);

  async function perform(body: object, notice: string) {
    setBusy(true); setError(""); setMessage("");
    try { await request(body); setMessage(notice); await refresh(); }
    catch (reason) { setError(reason instanceof Error ? reason.message : "ทำรายการไม่สำเร็จ"); }
    finally { setBusy(false); }
  }
  async function retrain(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const epochs = Number(new FormData(event.currentTarget).get("epochs"));
    if (!data || !dataset) return;
    if (!window.confirm(`ฝึกโมเดลจาก ${labelVersion(data.active)}\nชุดข้อมูล: ${dataset.split("@")[0]}\nจำนวน ${epochs} epochs?`)) return;
    await perform({ action: "retrain", dataset_uri: dataset, epochs, expected_active: data.active }, "ส่งงานฝึกแล้ว ติดตามสถานะได้ด้านล่าง");
  }
  function activate(action: "promote" | "rollback", version: string) {
    if (!data || !window.confirm(`${action === "promote" ? "อนุมัติใช้" : "ย้อนกลับไปใช้"} ${labelVersion(version)}?\nรุ่นใหม่ใช้คะแนนทดลองจนกว่าจะมี confidence policy ที่ผ่านการปรับเทียบ`)) return;
    void perform({ action, version, expected_active: data.active }, "ส่งงานตรวจและเปลี่ยนรุ่นแล้ว รอตรวจการโหลดของ worker");
  }
  async function exportDataset(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!data) return;
    const selections = data.review_tasks.filter(task => annotations[task.id]).map(task => ({
      task_id: task.id, annotation_id: Number(annotations[task.id]), split: task.split,
    }));
    await perform({ action: "export", selections, reviewed: true }, "ส่งงานสร้างชุดข้อมูลแล้ว ตรวจสถานะการ export ด้านล่าง");
  }
  const disabled = busy || working || Boolean(error);
  const previous = data?.history.at(-1)?.from;
  return <section className="uv-admin-panel wrinkle-admin-panel" aria-labelledby="wrinkle-admin-heading" aria-busy={busy}>
    <header className="uv-admin-header"><div><h2 id="wrinkle-admin-heading">จัดการ Wrinkle AI</h2><p>ฝึกจากชุดข้อมูลที่อนุมัติ ตรวจผล แล้วเลือกเปิดใช้รุ่นใหม่</p></div><Button variant="outline" disabled={busy} onClick={() => void refresh()}><RefreshCw aria-hidden="true" />โหลดสถานะใหม่</Button></header>
    {error && <p className="uv-admin-feedback" role="alert">{error} · โหลดสถานะใหม่เพื่อลองอีกครั้ง</p>}
    {message && <p className="uv-admin-feedback" role="status">{message}</p>}
    {!data && !error && <p role="status">กำลังอ่านสถานะโมเดล…</p>}
    {data && <>
      <dl className="uv-admin-status"><div><dt>รุ่นที่เลือกใช้งาน</dt><dd>{labelVersion(data.active)}</dd></div><div><dt>การโหลดของ inference worker ล่าสุด</dt><dd>{data.loaded ? labelVersion(data.loaded.version) : "ยังไม่มีบันทึกการโหลด"}</dd></div><div><dt>การเปลี่ยนรุ่น</dt><dd>{data.pending ? "กำลังตรวจ checkpoint ก่อนเปลี่ยนรุ่น" : "พร้อมรับคำสั่ง"}</dd></div></dl>
      {data.error && <p role="alert" className="uv-admin-feedback">{data.error}</p>}
      <p className="uv-admin-note">รุ่นที่ฝึกใหม่แสดงคะแนนทดลองและงดคำแนะนำจนกว่าจะมี confidence policy ที่ผ่านการปรับเทียบสำหรับ checkpoint นั้น การฝึกสำเร็จจะไม่เปิดใช้เอง</p>
      <h3>สั่ง Retrain</h3>
      {!data.datasets.length ? <p className="uv-admin-note">ยังไม่มีชุดข้อมูลที่อนุมัติ สร้างจากป้ายกำกับที่ตรวจแล้วด้านล่าง หรือเตรียมชุดข้อมูลภายนอกตามคู่มือ</p> : <form className="wrinkle-training-form" onSubmit={retrain}>
        <label>ชุดข้อมูลที่อนุมัติ<select value={dataset} onChange={event => setDataset(event.target.value)} required disabled={disabled}><option value="">เลือกชุดข้อมูล</option>{data.datasets.map(item => <option key={item.uri} value={item.uri}>{item.name} · {item.subjects} บุคคล · train {item.counts.train} / validation {item.counts.validation} / test {item.counts.test}</option>)}</select></label>
        <label>จำนวน epochs<Input name="epochs" type="number" min={1} max={20} defaultValue={1} required disabled={disabled} /></label>
        <Button type="submit" disabled={disabled || !dataset}><Play aria-hidden="true" />สั่ง Retrain</Button>
      </form>}
      <h3>งานฝึกและผลเปรียบเทียบ</h3>
      {!data.runs.length && <p className="uv-admin-note">ยังไม่มีงานฝึกหรือ export ชุดข้อมูล</p>}
      {data.runs.map(run => <details key={run.id} className="wrinkle-run" open={["queued", "running"].includes(run.status)}><summary>{statuses[run.status] ?? run.status} · {run.id}{run.epochs ? ` · epoch ${run.epoch ?? 0}/${run.epochs}` : ""}</summary>
        <p className="uv-admin-meta">ชุดข้อมูล: {run.dataset_uri}<br />ผู้สั่งงาน: {run.actor ?? "ไม่มีบันทึก"}{run.mlflow_run_id && <><br />MLflow run: {run.mlflow_run_id}</>}</p>
        {run.mlflow_run_id && <Button variant="outline" nativeButton={false} render={<a href={`http://localhost:5000/#/experiments/0/runs/${encodeURIComponent(run.mlflow_run_id)}`} target="_blank" rel="noopener noreferrer" aria-label={`ดูผลใน MLflow ของงาน ${run.id} (เปิดแท็บใหม่)`} />}><ExternalLink aria-hidden="true" />ดูผลใน MLflow</Button>}
        {run.error && <p role="alert">{run.error}</p>}
        {run.loss != null && <p>Loss ล่าสุด: {run.loss.toFixed(4)}</p>}
        {run.evaluation && <div className="uv-admin-table-wrap" tabIndex={0} role="region" aria-label="เปรียบเทียบผลโมเดลริ้วรอย"><table><caption>เทียบบนชุดข้อมูลเดียวกัน · ค่ายิ่งสูงยิ่งดี</caption><thead><tr><th scope="col">ตัวชี้วัด</th><th scope="col">รุ่นเดิม</th><th scope="col">Candidate</th></tr></thead><tbody>{Object.entries(run.evaluation.candidate).map(([key, value]) => <tr key={key}><th scope="row">{key}</th><td>{run.evaluation!.baseline[key]?.toFixed(3) ?? "ไม่มีข้อมูล"}</td><td>{value.toFixed(3)}</td></tr>)}</tbody></table></div>}
        {run.gate && <p>{run.gate.passed ? "ผ่านเกณฑ์เปรียบเทียบ" : `ไม่ผ่านเกณฑ์: ${run.gate.reasons.join("; ")}`}</p>}
        {run.status === "awaiting_approval" && <Button disabled={disabled || !run.gate?.passed || run.base_version !== data.active || run.id === data.active} onClick={() => activate("promote", run.id)}><ShieldCheck aria-hidden="true" />อนุมัติใช้ Candidate</Button>}
      </details>)}
      <div className="uv-admin-rollback"><div><h3>ย้อนกลับรุ่นก่อนหน้า</h3><p className="uv-admin-version">{previous ? labelVersion(previous) : "ยังไม่มีรุ่นก่อนหน้า"}</p></div><Button variant="outline" disabled={disabled || !previous} onClick={() => previous && activate("rollback", previous)}><Undo2 aria-hidden="true" />ย้อนกลับรุ่นก่อนหน้า</Button></div>
      <details><summary>สร้างชุดข้อมูลจากภาพที่ตรวจแล้ว</summary><p>ตรวจ mask ใน Label Studio แล้วกรอก Annotation ID ที่อนุมัติ (คนละค่ากับ Task ID) ระบบล็อก split ตามบัญชีข้ามทุกชุดข้อมูล ต้องเลือกให้ครบ train/validation/test ใช้ได้เฉพาะภาพที่ส่งหลังให้ consent ฝึกโมเดลและยังไม่ครบ 30 วัน</p>
        {!data.review_tasks.length ? <p className="uv-admin-note">ยังไม่มีภาพที่มี consent ฝึกและส่งไปตรวจแล้ว</p> : <form onSubmit={exportDataset}>
          <div className="wrinkle-review-tasks">{data.review_tasks.map(task => <label key={task.id}>Task {task.label_studio_task_id} · {task.split}<Input type="number" min={1} step={1} placeholder="Annotation ID ที่ตรวจแล้ว" value={annotations[task.id] ?? ""} disabled={disabled} onChange={event => setAnnotations(current => ({ ...current, [task.id]: event.target.value }))} /></label>)}</div>
          <label className="wrinkle-review-consent"><input type="checkbox" required disabled={disabled} />ฉันตรวจและอนุมัติ mask ที่เลือกให้ใช้ฝึกและประเมินโมเดลแล้ว</label>
          <Button type="submit" disabled={disabled || !Object.values(annotations).some(Boolean)}>สร้างชุดข้อมูลที่อนุมัติ</Button>
        </form>}
      </details>
      <details><summary>ประวัติการเปลี่ยนรุ่น ({data.history.length})</summary><ol className="uv-admin-history">{data.history.toReversed().map((item, index) => <li key={`${item.at}/${index}`}>{item.action} · {new Date(item.at).toLocaleString("th-TH")}<br />{labelVersion(item.from)} → {labelVersion(item.to)}<br />ผู้ดำเนินการ: {item.actor}</li>)}</ol></details>
    </>}
  </section>;
}
