"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { WorkspaceShell } from "@/components/workspace-shell";

const MAX_BYTES = 10 * 1024 * 1024;
const TYPES = new Set(["image/jpeg", "image/png", "image/webp"]);

export default function CapturePage() {
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [consent, setConsent] = useState(false);
  const [annotationConsent, setAnnotationConsent] = useState(false);
  const [cameraOpen, setCameraOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const video = useRef<HTMLVideoElement>(null);
  const stream = useRef<MediaStream | null>(null);
  const previewRef = useRef<string | null>(null);
  const router = useRouter();

  useEffect(() => () => { if (previewRef.current) URL.revokeObjectURL(previewRef.current); }, []);

  useEffect(() => {
    if (cameraOpen && video.current && stream.current) video.current.srcObject = stream.current;
  }, [cameraOpen]);

  useEffect(() => () => stream.current?.getTracks().forEach((track) => track.stop()), []);

  function chooseImage(next: File | null) {
    // Clear the previous selection error before validating the new file.
    setError("");
    if (!next) return;
    // Reject unsupported formats and oversized files in the browser.
    if (!TYPES.has(next.type)) return setError("กรุณาเลือกภาพ JPEG, PNG หรือ WebP");
    if (next.size > MAX_BYTES) return setError("ภาพต้องมีขนาดไม่เกิน 10 MB");
    // Release the old object URL so repeated selections do not retain blobs.
    if (previewRef.current) URL.revokeObjectURL(previewRef.current);
    // Show a local preview without uploading the image yet.
    previewRef.current = URL.createObjectURL(next);
    setPreview(previewRef.current);
    setFile(next);
  }

  function stopCamera() {
    // Stop all camera tracks before hiding the live video element.
    stream.current?.getTracks().forEach((track) => track.stop());
    stream.current = null;
    setCameraOpen(false);
  }

  async function openCamera() {
    setError("");
    if (!navigator.mediaDevices?.getUserMedia) {
      setError("เบราว์เซอร์นี้ไม่รองรับกล้อง กรุณาเลือกไฟล์ภาพแทน");
      return;
    }
    try {
      // Ask for a front-facing video stream; audio is never requested.
      stream.current = await navigator.mediaDevices.getUserMedia({
        audio: false,
        video: { facingMode: "user", width: { ideal: 1280 }, height: { ideal: 1280 } },
      });
      setCameraOpen(true);
    } catch {
      setError("เปิดกล้องไม่ได้ กรุณาอนุญาตการใช้กล้องหรือเลือกไฟล์ภาพแทน");
    }
  }

  async function capturePhoto() {
    const source = video.current;
    // Avoid sending a frame that is too small for the AI quality gate.
    if (!source || source.videoWidth < 512 || source.videoHeight < 512) {
      setError("ภาพจากกล้องต้องมีความกว้างและสูงอย่างน้อย 512 พิกเซล");
      return;
    }
    // Copy the current frame into a canvas before encoding a JPEG file.
    const canvas = document.createElement("canvas");
    canvas.width = source.videoWidth;
    canvas.height = source.videoHeight;
    canvas.getContext("2d")?.drawImage(source, 0, 0);
    const blob = await new Promise<Blob | null>((resolve) => canvas.toBlob(resolve, "image/jpeg", 0.92));
    if (!blob) return setError("บันทึกภาพจากกล้องไม่สำเร็จ");
    // Reuse the same validation and preview path as a selected file.
    chooseImage(new File([blob], "capture.jpg", { type: "image/jpeg" }));
    stopCamera();
  }

  // Send analysis consent with every image; review consent is an optional second choice.
  async function submit() {
    // The required checkbox gates analysis; review consent remains optional.
    if (!file || !consent) return setError("เลือกภาพและยอมรับการวิเคราะห์ก่อนดำเนินการ");
    setBusy(true);
    setError("");
    // FormData carries the image and the two consent decisions to the Next.js route.
    const form = new FormData();
    form.set("image", file);
    form.set("consent", "yes");
    if (annotationConsent) form.set("annotation_consent", "yes");
    try {
      // The route returns after queueing analysis, before inference finishes.
      const response = await fetch("/api/analysis", { method: "POST", body: form });
      if (!response.ok) {
        const body = await response.json().catch(() => null);
        throw new Error(typeof body?.detail === "string" ? body.detail : "ส่งภาพไม่สำเร็จ");
      }
      // The result page polls the status using the signed browser cookie.
      router.push("/result-detail");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "ส่งภาพไม่สำเร็จ");
      setBusy(false);
    }
  }

  async function revokeAnnotationConsent() {
    setBusy(true);
    setError("");
    setNotice("");
    try {
      // The DELETE route revokes review consent for users tracked by this browser.
      const response = await fetch("/api/analysis", { method: "DELETE" });
      if (!response.ok) throw new Error("ถอนความยินยอมไม่สำเร็จ กรุณาลองอีกครั้ง");
      setAnnotationConsent(false);
      setNotice("ถอนความยินยอมสำหรับภาพที่ส่งจากเบราว์เซอร์นี้แล้ว");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "ถอนความยินยอมไม่สำเร็จ");
    } finally {
      setBusy(false);
    }
  }

  return (
    <WorkspaceShell active="capture" eyebrow="IMAGE ANALYSIS" title="วิเคราะห์ภาพ" detail="ขั้นตอน 1 จาก 2 · เตรียมภาพ">
        <div className="capture-layout">
        <section className="page-content capture-panel" aria-labelledby="capture-title">
          <p className="eyebrow">เริ่มวิเคราะห์</p>
          <h2 id="capture-title">แนบภาพหรือถ่ายภาพใบหน้า</h2>
          <p className="capture-intro">เลือกภาพที่เห็นใบหน้าชัดเจน หรือเปิดกล้องเพื่อถ่ายภาพใหม่</p>
          <div className="upload-box capture-preview">
            {/* Show live video first, a selected-file preview second, or the empty prompt. */}
            {cameraOpen ? (
              <video ref={video} autoPlay muted playsInline aria-label="ภาพจากกล้อง" />
            ) : preview ? (
              // Browser object URLs cannot be optimized by Next Image.
              // eslint-disable-next-line @next/next/no-img-element
              <img src={preview} alt="ภาพที่เลือกเพื่อวิเคราะห์" />
            ) : (
              <div><div className="upload-icon">⌁</div><h3>เลือกภาพหรือเปิดกล้อง</h3><p>JPEG, PNG, WebP · ไม่เกิน 10 MB</p></div>
            )}
          </div>
          <div className="capture-controls">
            {/* Both file inputs end at chooseImage, so they share validation. */}
            <label className="secondary-button capture-file">เลือกภาพจากเครื่อง
              <input type="file" accept="image/jpeg,image/png,image/webp" onChange={(event) => chooseImage(event.target.files?.[0] ?? null)} />
            </label>
            <label className="secondary-button capture-file">ถ่ายด้วยโทรศัพท์
              <input type="file" accept="image/*" capture="user" onChange={(event) => chooseImage(event.target.files?.[0] ?? null)} />
            </label>
            {cameraOpen ? (
              <><button type="button" className="primary-button" onClick={capturePhoto}>ใช้ภาพจากกล้อง</button><button type="button" className="secondary-button" onClick={stopCamera}>ปิดกล้อง</button></>
            ) : (
              <button type="button" className="secondary-button" onClick={openCamera}>เปิดเว็บแคม</button>
            )}
          </div>
          {/* Analysis consent is required before the submit button can be used. */}
          <label className="capture-consent"><input type="checkbox" checked={consent} onChange={(event) => setConsent(event.target.checked)} />
            <span>ฉันยินยอมให้วิเคราะห์ภาพใบหน้าเพื่อแสดงคะแนนทดลองและภาพ mask โดยภาพผลจะถูกลบภายใน 24 ชั่วโมง ผลนี้ยังไม่ผ่านการตรวจสอบทางคลินิก</span>
          </label>
          {/* Human review is optional and has a separate 30-day retention window. */}
          <label className="capture-consent"><input type="checkbox" checked={annotationConsent} onChange={(event) => setAnnotationConsent(event.target.checked)} />
            <span>ฉันยินยอมเพิ่มเติมให้เก็บภาพใบหน้าที่จัดแนวแล้วเพื่อให้ผู้ตรวจแก้ป้ายกำกับริ้วรอยใน Label Studio โดยกำหนดลบหลัง 30 วัน และไม่นำไปฝึกโมเดลอัตโนมัติ</span>
          </label>
          {/* Revocation applies to review consents tracked by this browser. */}
          <button type="button" className="secondary-button" disabled={busy} onClick={revokeAnnotationConsent}>ถอนความยินยอมตรวจป้ายกำกับภาพที่ส่งจากเบราว์เซอร์นี้</button>
          {notice && <p role="status">{notice}</p>}
          {error && <p className="capture-error" role="alert">{error}</p>}
          <div className="page-actions"><button type="button" className="primary-button" disabled={busy || !file || !consent} onClick={submit}>{busy ? "กำลังส่งภาพ…" : "วิเคราะห์ภาพ →"}</button><Link className="secondary-button" href="/">กลับหน้าภาพรวม</Link></div>
        </section>
        <aside className="capture-guide" aria-label="คำแนะนำก่อนวิเคราะห์">
          <p className="eyebrow">ภาพที่เหมาะสม</p>
          <h2>ถ่ายภาพให้เทียบผลได้ดีขึ้น</h2>
          <ul>
            <li><strong>01</strong><span>หันหน้าตรงและเห็นใบหน้าเพียงหนึ่งคน</span></li>
            <li><strong>02</strong><span>ใช้แสงสม่ำเสมอ ภาพไม่เบลอ</span></li>
            <li><strong>03</strong><span>ไม่ใช้ฟิลเตอร์ และให้ภาพมีขนาดอย่างน้อย 512 × 512 พิกเซล</span></li>
          </ul>
          <div className="capture-guide-note"><strong>ข้อมูลของคุณ</strong><p>ภาพผลทั่วไปลบภายใน 24 ชั่วโมง หากเลือกให้ตรวจป้ายกำกับ ภาพที่จัดแนวแล้วจะถูกลบหลัง 30 วันหรือเมื่อถอนความยินยอม</p></div>
        </aside>
        </div>
    </WorkspaceShell>
  );
}
