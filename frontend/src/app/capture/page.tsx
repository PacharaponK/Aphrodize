"use client";

import Link from "next/link";
import { ArrowRight, Camera, Check, ImagePlus, ScanFace, ShieldCheck, Sun, UserRound } from "lucide-react";
import "./capture.css";
import { startTransition, useEffect, useRef, useState } from "react";
import AnalysisResult from "./analysis-result";
import { WorkspaceShell } from "@/components/workspace-shell";
import { useLanguage } from "@/components/language-provider";

const MAX_BYTES = 10 * 1024 * 1024;
const TYPES = new Set(["image/jpeg", "image/png", "image/webp"]);

export default function CapturePage() {
  const { language } = useLanguage();
  const t = (th: string, en: string) => language === "en" ? en : th;
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [consent, setConsent] = useState(false);
  const [annotationConsent, setAnnotationConsent] = useState(false);
  const [trainingConsent, setTrainingConsent] = useState(false);
  const [savedConsents, setSavedConsents] = useState({ analysis: false, annotations: false, training: false });
  const [loadingConsents, setLoadingConsents] = useState(true);
  const [cameraOpen, setCameraOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const video = useRef<HTMLVideoElement>(null);
  const stream = useRef<MediaStream | null>(null);
  const previewRef = useRef<string | null>(null);
  const [requestedStage, setRequestedStage] = useState(1);
  const [hasAnalysis, setHasAnalysis] = useState(false);
  const [resultsReady, setResultsReady] = useState(false);
  const [analysisVersion, setAnalysisVersion] = useState(0);
  const stage = requestedStage === 3 && !resultsReady ? 2 : requestedStage;
  const resultView = useRef<HTMLDivElement>(null);
  const captureView = useRef<HTMLElement>(null);
  const stepsView = useRef<HTMLOListElement>(null);
  const previousStage = useRef(1);

  useEffect(() => {
    if (typeof window === "undefined") return;
    const syncResults = () => startTransition(() => {
      const next = window.location.hash === "#products" ? 3 : window.location.hash === "#results" ? 2 : 1;
      setRequestedStage(next);
      if (next > 1) setHasAnalysis(true);
    });
    syncResults();
    window.addEventListener("hashchange", syncResults);
    window.addEventListener("popstate", syncResults);
    return () => {
      window.removeEventListener("hashchange", syncResults);
      window.removeEventListener("popstate", syncResults);
    };
  }, []);

  useEffect(() => {
    if (previousStage.current === stage) return;
    previousStage.current = stage;
    const view = stage === 1 ? captureView.current : resultView.current;
    view?.focus({ preventScroll: true });
    stepsView.current?.scrollIntoView({ block: "start", behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches ? "instant" : "smooth" });
  }, [stage]);

  function goToStage(next: number) {
    stopCamera();
    const hash = next === 3 ? "#products" : next === 2 ? "#results" : "";
    window.history.pushState(window.history.state, "", window.location.pathname + window.location.search + hash);
    setRequestedStage(next);
  }

  useEffect(() => {
    let active = true;
    fetch("/api/analysis?consents=1", { cache: "no-store" })
      .then(async (response) => {
        if (!response.ok) throw new Error("Could not load consent");
        const data = await response.json();
        if (!active) return;
        const saved = { analysis: data.analysis === true, annotations: data.annotations === true, training: data.training === true };
        setSavedConsents(saved);
        setConsent(saved.analysis);
        setAnnotationConsent(saved.annotations);
        setTrainingConsent(saved.training);
      })
      .catch(() => { /* Leave consent unchecked if its saved status cannot be verified. */ })
      .finally(() => { if (active) setLoadingConsents(false); });
    return () => { active = false; };
  }, []);

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
    if (!TYPES.has(next.type)) return setError(t("กรุณาเลือกภาพ JPEG, PNG หรือ WebP", "Choose a JPEG, PNG, or WebP image."));
    if (next.size > MAX_BYTES) return setError(t("ภาพต้องมีขนาดไม่เกิน 10 MB", "Image size must be 10 MB or less."));
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
      setError(t("เบราว์เซอร์นี้ไม่รองรับกล้อง กรุณาเลือกไฟล์ภาพแทน", "This browser does not support the camera. Choose an image file instead."));
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
      setError(t("เปิดกล้องไม่ได้ กรุณาอนุญาตการใช้กล้องหรือเลือกไฟล์ภาพแทน", "Could not open the camera. Allow camera access or choose an image file instead."));
    }
  }

  async function capturePhoto() {
    const source = video.current;
    // Avoid sending a frame that is too small for the AI quality gate.
    if (!source || source.videoWidth < 512 || source.videoHeight < 512) {
      setError(t("ภาพจากกล้องต้องมีความกว้างและสูงอย่างน้อย 512 พิกเซล", "Camera images must be at least 512 × 512 pixels."));
      return;
    }
    // Copy the current frame into a canvas before encoding a JPEG file.
    const canvas = document.createElement("canvas");
    canvas.width = source.videoWidth;
    canvas.height = source.videoHeight;
    canvas.getContext("2d")?.drawImage(source, 0, 0);
    const blob = await new Promise<Blob | null>((resolve) => canvas.toBlob(resolve, "image/jpeg", 0.92));
    if (!blob) return setError(t("บันทึกภาพจากกล้องไม่สำเร็จ", "Could not save the camera image."));
    // Reuse the same validation and preview path as a selected file.
    chooseImage(new File([blob], "capture.jpg", { type: "image/jpeg" }));
    stopCamera();
  }

  // Send analysis consent with every image; review consent is an optional second choice.
  async function submit() {
    // The required checkbox gates analysis; review consent remains optional.
    if (!file || !consent) return setError(t("เลือกภาพและยอมรับการวิเคราะห์ก่อนดำเนินการ", "Choose an image and consent to analysis before continuing."));
    setBusy(true);
    setError("");
    // FormData carries the image and the two consent decisions to the Next.js route.
    const form = new FormData();
    form.set("image", file);
    form.set("consent", "yes");
    if (annotationConsent) form.set("annotation_consent", "yes");
    if (trainingConsent && annotationConsent) form.set("training_consent", "yes");
    try {
      // The route returns after queueing analysis, before inference finishes.
      const response = await fetch("/api/analysis", { method: "POST", body: form });
      if (!response.ok) {
        const body = await response.json().catch(() => null);
        throw new Error(typeof body?.detail === "string" ? body.detail : t("ส่งภาพไม่สำเร็จ", "Could not submit the image."));
      }
      // Show and poll the result in this page using the signed browser cookie.
      stopCamera();
      setSavedConsents({ analysis: true, annotations: annotationConsent, training: trainingConsent && annotationConsent });
      setBusy(false);
      setResultsReady(false);
      setAnalysisVersion((current) => current + 1);
      setHasAnalysis(true);
      goToStage(2);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : t("ส่งภาพไม่สำเร็จ", "Could not submit the image."));
      setBusy(false);
    }
  }

  async function revokeConsent(scope: "analysis" | "annotations" | "training") {
    setBusy(true);
    setError("");
    setNotice("");
    try {
      const response = await fetch(`/api/analysis?scope=${scope}`, { method: "DELETE" });
      if (!response.ok) throw new Error(t("ถอนความยินยอมไม่สำเร็จ กรุณาลองอีกครั้ง", "Could not revoke consent. Please try again."));
      if (scope === "analysis") setConsent(false);
      else if (scope === "training") setTrainingConsent(false);
      else { setAnnotationConsent(false); setTrainingConsent(false); }
      setSavedConsents((current) => ({ ...current, [scope]: false, ...(scope === "annotations" ? { training: false } : {}) }));
      setNotice(scope === "analysis"
        ? t("ถอนความยินยอมวิเคราะห์ภาพแล้ว ต้องยินยอมใหม่ก่อนวิเคราะห์ครั้งถัดไป", "Image-analysis consent withdrawn. Give consent again before your next analysis.")
        : scope === "training" ? t("ถอนความยินยอมฝึกโมเดลแล้ว", "Model-training consent withdrawn.") : t("ถอนความยินยอมตรวจป้ายกำกับภาพแล้ว", "Image-label review consent withdrawn."));
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : t("ถอนความยินยอมไม่สำเร็จ", "Could not revoke consent."));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="capture-page">
      <WorkspaceShell eyebrow="" title={t("วิเคราะห์ภาพใบหน้า", "Analyze your face image")}>
        <p className="capture-intro">{t("เตรียมภาพ ดูผลวิเคราะห์ แล้วเลือกดูผลิตภัณฑ์ที่แนะนำ", "Prepare your image, explore the analysis, then view recommended products.")}</p>
        <ol ref={stepsView} className="capture-steps" aria-label={t("ขั้นตอนการวิเคราะห์", "Analysis steps")}>
          {[t("เตรียมภาพ", "Prepare image"), t("ดูผลวิเคราะห์", "View results"), t("ผลิตภัณฑ์ที่แนะนำ", "Recommended products")].map((label, index) => (
            <li key={index} aria-current={stage === index + 1 ? "step" : undefined}>
              <button type="button" disabled={busy || (index === 1 && !hasAnalysis) || (index === 2 && !resultsReady)} onClick={() => goToStage(index + 1)}>
                <span>{(index === 0 && (file || resultsReady)) || (index === 1 && resultsReady) ? <Check size={16} aria-hidden="true" /> : index + 1}</span>{label}
              </button>
            </li>
          ))}
        </ol>
        <section hidden={stage !== 1} ref={captureView} tabIndex={-1} className="capture-studio" aria-labelledby="capture-title">
          <div className="capture-image-area">
            <h2 id="capture-title">{t("เริ่มจากภาพที่ชัดเจน", "Start with a clear image")}</h2>
            <p className="capture-description">{t("เลือกภาพใบหน้าหรือถ่ายภาพใหม่ เพื่อเตรียมส่งวิเคราะห์", "Choose a face image or take a new photo to prepare your analysis.")}</p>
            <div className={`capture-image-frame${preview || cameraOpen ? " has-image" : ""}`}>
              {cameraOpen ? (
                <video ref={video} autoPlay muted playsInline aria-label={t("ภาพจากกล้อง", "Camera preview")} />
              ) : preview ? (
                // Browser object URLs cannot be optimized by Next Image.
                // eslint-disable-next-line @next/next/no-img-element
                <img src={preview} alt={t("ภาพที่เลือกเพื่อวิเคราะห์", "Selected image for analysis")} />
              ) : (
                <div className="capture-empty">
                  <ScanFace size={64} strokeWidth={1.25} aria-hidden="true" />
                  <h3>{t("ภาพใบหน้าของคุณ", "Your face image")}</h3>
                  <p>{t("หน้าตรง เห็นใบหน้าชัดเจน", "Face forward, with your face clearly visible")}</p>
                  <small>JPEG, PNG, WebP · {t("ไม่เกิน 10 MB", "up to 10 MB")}</small>
                </div>
              )}
            </div>
            {file && <p className="capture-selected" role="status"><Check size={16} aria-hidden="true" /><span>{file.name}</span><small>{t("ยังไม่ได้ส่งภาพ", "Not uploaded yet")}</small></p>}
            <div className="capture-image-controls">
              <label className="secondary-button capture-file"><ImagePlus size={18} aria-hidden="true" />{preview ? t("เปลี่ยนภาพ", "Change image") : t("เลือกภาพ", "Choose image")}
                <input type="file" aria-label={t("เลือกภาพจากเครื่อง", "Choose an image file")} accept="image/jpeg,image/png,image/webp" disabled={busy} onChange={(event) => chooseImage(event.target.files?.[0] ?? null)} />
              </label>
              {!cameraOpen && <label className="secondary-button capture-file capture-phone"><Camera size={18} aria-hidden="true" />{t("ถ่ายภาพ", "Take a photo")}
                <input type="file" aria-label={t("ถ่ายภาพด้วยโทรศัพท์", "Take a phone photo")} accept="image/*" capture="user" disabled={busy} onChange={(event) => chooseImage(event.target.files?.[0] ?? null)} />
              </label>}
              {cameraOpen ? (
                <><button type="button" className="primary-button" disabled={busy} onClick={capturePhoto}><Camera size={18} aria-hidden="true" />{t("ใช้ภาพนี้", "Use this photo")}</button><button type="button" className="secondary-button" onClick={stopCamera}>{t("ปิดกล้อง", "Close camera")}</button></>
              ) : (
                <button type="button" className="secondary-button capture-webcam" disabled={busy} onClick={openCamera}><Camera size={18} aria-hidden="true" />{t("เปิดกล้อง", "Open camera")}</button>
              )}
            </div>
          <aside className="capture-tips" aria-labelledby="capture-tips-title">
            <h2 id="capture-tips-title">{t("เตรียมภาพให้พร้อม", "A little preparation")}</h2>
            <p>{t("ถ่ายในเงื่อนไขใกล้เคียงกันทุกครั้ง เพื่อให้เทียบภาพได้ดีขึ้น", "Use similar conditions each time for more comparable images.")}</p>
            <ul>
              <li><UserRound size={22} aria-hidden="true" /><div><strong>{t("หันหน้าตรง", "Face forward")}</strong><p>{t("เห็นใบหน้าเพียงหนึ่งคนในภาพ", "Keep just one person in the frame.")}</p></div></li>
              <li><Sun size={22} aria-hidden="true" /><div><strong>{t("ใช้แสงสม่ำเสมอ", "Find even lighting")}</strong><p>{t("ให้เห็นรายละเอียดชัดเจน ภาพไม่เบลอ", "Keep facial details clear and avoid blur.")}</p></div></li>
              <li><ScanFace size={22} aria-hidden="true" /><div><strong>{t("ไม่ใช้ฟิลเตอร์", "Skip the filters")}</strong><p>{t("ใช้ภาพอย่างน้อย 512 × 512 พิกเซล", "Use an image of at least 512 × 512 pixels.")}</p></div></li>
            </ul>
            <div className="capture-local-note"><ShieldCheck size={20} aria-hidden="true" /><p>{t("ภาพตัวอย่างอยู่ในเบราว์เซอร์จนกว่าคุณจะกดวิเคราะห์", "Your preview stays in this browser until you choose to analyze.")}</p></div>
          </aside>
          </div>
          <div className="capture-permissions">
            <div className="capture-permissions-heading"><ShieldCheck size={24} aria-hidden="true" /><h2>{t("ความยินยอมและข้อมูลของคุณ", "Your consent, your data")}</h2></div>
            <p className="capture-consent-copy">{loadingConsents ? t("กำลังตรวจสอบความยินยอม…", "Checking saved consent…") : t("ความยินยอมที่บันทึกไว้จะใช้ในการวิเคราะห์ครั้งถัดไปโดยไม่ต้องเลือกซ้ำ เอาเครื่องหมายออกเพื่อถอนความยินยอม", "Saved consent applies to future analyses without selecting it again. Uncheck a choice to withdraw consent.")}</p>
            <label className="capture-consent-row"><input type="checkbox" checked={consent} disabled={busy || loadingConsents} onChange={(event) => { if (!event.target.checked && savedConsents.analysis) void revokeConsent("analysis"); else setConsent(event.target.checked); }} />
              <span><span className="capture-consent-heading"><strong>{t("ยินยอมให้วิเคราะห์ภาพ", "Consent to image analysis")}</strong><small>{t("จำเป็น", "Required")}</small></span><span className="capture-consent-copy">{t("ฉันยินยอมให้วิเคราะห์ภาพใบหน้าเพื่อแสดงคะแนนทดลองและภาพ mask โดยภาพผลจะถูกลบภายใน 24 ชั่วโมง ผลนี้ยังไม่ผ่านการตรวจสอบทางคลินิก", "I consent to face-image analysis for experimental scores and a mask preview. Result images are deleted within 24 hours. This system has not been clinically validated.")}</span></span>
            </label>
            <label className="capture-consent-row"><input type="checkbox" checked={annotationConsent} disabled={busy || loadingConsents} onChange={(event) => { if (!event.target.checked && savedConsents.annotations) void revokeConsent("annotations"); else { setAnnotationConsent(event.target.checked); if (!event.target.checked) setTrainingConsent(false); } }} />
              <span><span className="capture-consent-heading"><strong>{t("อนุญาตให้ผู้ตรวจทบทวนป้ายกำกับภาพ", "Allow human image-label review")}</strong><small>{t("ไม่บังคับ", "Optional")}</small></span><span className="capture-consent-copy">{t("ฉันยินยอมเพิ่มเติมให้เก็บภาพใบหน้าที่จัดแนวแล้วเพื่อให้ผู้ตรวจแก้ป้ายกำกับริ้วรอยใน Label Studio โดยกำหนดลบหลัง 30 วัน และไม่นำไปฝึกโมเดลอัตโนมัติ", "I separately consent to retain an aligned face image for human wrinkle-label review in Label Studio. It will be deleted after 30 days and will not be used for automated model training.")}</span></span>
            </label>
              <label className="capture-consent-row"><input type="checkbox" checked={trainingConsent} disabled={busy || loadingConsents || !annotationConsent} onChange={(event) => { if (!event.target.checked && savedConsents.training) void revokeConsent("training"); else setTrainingConsent(event.target.checked); }} />
                <span><span className="capture-consent-heading"><strong>{t("อนุญาตให้นำภาพและป้ายกำกับที่ตรวจแล้วไปฝึกและประเมินโมเดลริ้วรอย", "Allow reviewed images and labels for wrinkle model training and evaluation")}</strong><small>{t("ไม่บังคับ", "Optional")}</small></span><span className="capture-consent-copy">{t("แยกจากการวิเคราะห์และการตรวจภาพ ผู้ดูแลต้องอนุมัติชุดข้อมูลก่อนสั่งฝึก เก็บข้อมูลฝึกไม่เกิน 30 วันจากวันส่งภาพ ถอนสิทธิ์ได้ทุกเมื่อ ระบบจะลบชุดข้อมูลและหยุดใช้รุ่นที่อาศัยข้อมูลนั้นเมื่อรับงานถัดไป แต่ไม่สามารถลบสิ่งที่โมเดลเรียนรู้แล้วออกจากน้ำหนักได้โดยตรง", "Separate from analysis and human review. An admin must approve the dataset before training. Training data is retained for at most 30 days from upload. You can withdraw at any time; datasets are deleted and affected versions are retired before the next analysis. Learned information cannot be directly erased from model weights.")}</span></span>
              </label>
            <details className="capture-privacy">
              <summary>{t("การเก็บภาพและถอนความยินยอม", "Image retention and consent withdrawal")}</summary>
              <p>{t("ภาพผลทั่วไปลบภายใน 24 ชั่วโมง หากเลือกให้ตรวจป้ายกำกับ ภาพที่จัดแนวแล้วจะถูกลบหลัง 30 วันหรือเมื่อถอนความยินยอม", "Standard result images are deleted within 24 hours. If you opt into label review, the aligned image is deleted after 30 days or when consent is withdrawn.")}</p>
              <button type="button" className="secondary-button" disabled={busy || loadingConsents} onClick={() => void revokeConsent("annotations")}>{t("ถอนความยินยอมตรวจป้ายกำกับภาพที่ส่งจากเบราว์เซอร์นี้", "Revoke image-label review consent for this browser")}</button>
              <button type="button" className="secondary-button" disabled={busy || loadingConsents} onClick={() => void revokeConsent("training")}>{t("ถอนความยินยอมฝึกโมเดล", "Revoke model-training consent")}</button>
            </details>
            {notice && <p className="capture-notice" role="status">{notice}</p>}
            {error && <p className="capture-error" role="alert">{error}</p>}
            <div className="capture-submit-area">
              <div><button type="button" className="primary-button" aria-describedby="capture-submit-hint" disabled={busy || !file || !consent} onClick={submit}>{busy ? t("กำลังส่งภาพ…", "Submitting image…") : t("วิเคราะห์ภาพ", "Analyze image")}<ArrowRight size={18} aria-hidden="true" /></button>
                <p id="capture-submit-hint">{!file || !consent ? t("เลือกภาพและให้ความยินยอมเพื่อเริ่ม", "Choose an image and give consent to begin.") : t("พร้อมส่งภาพเพื่อวิเคราะห์", "Ready to submit your image for analysis.")}</p>
              </div>
              <Link href="/#dashboard">{t("กลับหน้าภาพรวม", "Back to overview")}</Link>
            </div>
          </div>
        </section>
        {hasAnalysis && <div hidden={stage === 1} id={stage === 3 ? "products" : "results"} className="capture-results" ref={resultView} tabIndex={-1} aria-label={stage === 3 ? t("ผลิตภัณฑ์ที่แนะนำ", "Recommended products") : t("ผลวิเคราะห์ภาพ", "Image analysis results")}>
          <AnalysisResult key={analysisVersion} view={stage === 3 ? "products" : "results"} onReady={setResultsReady} onNewAnalysis={() => goToStage(1)} />
          <nav className="capture-stage-actions" aria-label={t("เปลี่ยนขั้นตอน", "Stage navigation")}>
            <button type="button" className="secondary-button" onClick={() => goToStage(stage === 3 ? 2 : 1)}>{stage === 3 ? t("กลับดูผลวิเคราะห์", "Back to results") : t("กลับไปเตรียมภาพ", "Back to image preparation")}</button>
            {stage === 2 && <button type="button" className="primary-button" disabled={!resultsReady} onClick={() => goToStage(3)}>{t("ดูผลิตภัณฑ์ที่แนะนำ", "View recommended products")}<ArrowRight size={18} aria-hidden="true" /></button>}
          </nav>
        </div>}
      </WorkspaceShell>
    </div>
  );
}
