"use client";

/* eslint-disable @next/next/no-html-link-for-pages */
import Image from "next/image";
import { useRef, useState } from "react";

export default function Page() {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [stream, setStream] = useState<MediaStream | null>(null);
  const [message, setMessage] = useState("");

  async function openCamera() {
    try {
      const nextStream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: "user" }, audio: false });
      setStream(nextStream);
      setMessage("จัดใบหน้าให้อยู่กึ่งกลาง แล้วกดถ่ายภาพ");
      requestAnimationFrame(() => { if (videoRef.current) videoRef.current.srcObject = nextStream; });
    } catch {
      setMessage("เปิดกล้องไม่ได้ กรุณาอนุญาตกล้อง หรือเลือกภาพแทน (ต้องใช้ HTTPS หรือ localhost)");
    }
  }

  function takePhoto() {
    const video = videoRef.current;
    if (!video?.videoWidth) return;
    const canvas = document.createElement("canvas");
    canvas.width = video.videoWidth; canvas.height = video.videoHeight;
    canvas.getContext("2d")?.drawImage(video, 0, 0);
    setPreview(canvas.toDataURL("image/jpeg", 0.92));
    stream?.getTracks().forEach((track) => track.stop());
    setStream(null); setMessage("ตรวจสอบภาพแล้วกด “ใช้ภาพนี้” เพื่อดูผลตัวอย่าง");
  }

  function selectPhoto(file?: File) {
    if (!file) return;
    if (file.size > 10 * 1024 * 1024) { setMessage("ไฟล์มีขนาดเกิน 10 MiB กรุณาเลือกภาพที่เล็กกว่า"); return; }
    setPreview(URL.createObjectURL(file));
    setMessage("ตรวจสอบภาพแล้วกด “ใช้ภาพนี้” เพื่อดูผลตัวอย่าง");
  }

  return (
    <div className="simple-page"><main className="page-frame"><header className="page-header"><a className="page-brand" href="/"><Image width={40} height={40} src="/assets/aphrodize-contour-a.svg" alt="" />Aphrodize</a><nav className="page-nav"><a href="/">ภาพรวม</a><a className="active" href="/capture">วิเคราะห์ภาพ</a><a href="/trend">แนวโน้ม</a></nav></header><section className="page-content"><p className="eyebrow">NEW ANALYSIS</p><h1>ถ่ายภาพให้เทียบกันได้</h1><p>รักษาระยะ มุม และแสงให้ใกล้เคียงภาพก่อนหน้า เพื่อให้ผลติดตามมีความหมาย</p><div className="step-row"><span className="step">1 · Consent</span><span className="step">2 · Skin profile</span><span className="step active">3 · Capture</span></div><div className="upload-box" style={{ overflow: "hidden" }}>{preview ? <Image src={preview} alt="ภาพที่เลือก" width={1280} height={720} style={{ width: "100%", height: "100%", maxHeight: 360, objectFit: "cover", borderRadius: 13 }} unoptimized /> : stream ? <video ref={videoRef} autoPlay muted playsInline style={{ width: "100%", maxHeight: 360, objectFit: "cover", borderRadius: 13 }} /> : <div><div className="upload-icon">⌁</div><h2>หน้าสด · หน้าตรง · แสงกระจาย</h2><p>ไม่ใช้ beauty filter · สีหน้าเป็นกลาง · ภาพไม่เบลอ</p></div>}</div><p className="metadata" role="status">{message}</p><div className="page-actions">{stream ? <button className="primary-button" type="button" onClick={takePhoto}>ถ่ายภาพ</button> : preview ? <a className="primary-button" href="/result-detail">ใช้ภาพนี้ →</a> : <button className="primary-button" type="button" onClick={openCamera}>เปิดกล้อง</button>} {!preview && !stream && <label className="secondary-button" htmlFor="image-input">เลือกภาพ<input id="image-input" type="file" hidden accept="image/jpeg,image/png,image/webp" capture="user" onChange={(event) => selectPhoto(event.target.files?.[0])} /></label>}<a className="secondary-button" href="/">กลับหน้าภาพรวม</a></div><p className="metadata">ภาพนี้ใช้แสดงผลตัวอย่างใน prototype · ผลจริงต้องผ่าน quality gate ก่อนบันทึกเป็นแนวโน้ม</p></section></main></div>
  );
}



