"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { WorkspaceShell } from "@/components/workspace-shell";

type ProfileValues = {
  sex: string;
  age_group: string;
  skin_type: string;
  wellness_goal: string;
  sunscreen_frequency: string;
  menstrual_tracking: string;
};
type Profile = { display_name: string; email: string; profile: ProfileValues | null };

const labels: Record<string, string> = {
  sex: "เพศ", age_group: "ช่วงอายุ", sunscreen_frequency: "การทาครีมกันแดด",
  skin_type: "สภาพผิว", menstrual_tracking: "การติดตามรอบเดือน", wellness_goal: "เป้าหมายการติดตาม",
};

function displayValue(value: unknown): string {
  if (value === "not_applicable") return "ไม่เกี่ยวข้อง";
  if (value === "prefer_not_to_say") return "ไม่สะดวกระบุ";
  return String(value ?? "-").replaceAll("_", " ");
}

export default function ProfilePage() {
  const [profile, setProfile] = useState<Profile | null>(null);
  const [message, setMessage] = useState("กำลังโหลดข้อมูลโปรไฟล์…");

  useEffect(() => {
    fetch("/api/profile", { cache: "no-store" })
      .then(async (response) => {
        const body = await response.json().catch(() => null);
        if (!response.ok) throw new Error(body?.detail ?? "ไม่สามารถโหลดข้อมูลโปรไฟล์ได้");
        setProfile(body);
        setMessage("");
      })
      .catch((error: Error) => setMessage(error.message));
  }, []);

  return <WorkspaceShell active="profile" eyebrow="SKIN PROFILE" title="โปรไฟล์ผิวของคุณ">
    <section className="workspace-panel profile-panel">
      {message && <p className="form-message" role="status">{message}</p>}
      {profile && <><article className="profile-account"><h2>{profile.display_name}</h2><p>{profile.email}</p></article>
        {profile.profile ? <><h2>ข้อมูลสุขภาพที่บันทึกไว้</h2><dl className="profile-answers">{Object.entries(profile.profile).map(([key, value]) => <div key={key}><dt>{labels[key] ?? key}</dt><dd>{displayValue(value)}</dd></div>)}</dl><Link className="secondary-button" href="/onboarding/health?edit=full">แก้ไขข้อมูลสุขภาพ →</Link></> : <div className="empty-state"><p>ยังไม่มีข้อมูลสุขภาพเบื้องต้น</p><Link className="primary-button" href="/onboarding/health">เริ่มตอบคำถาม →</Link></div>}</>}
    </section>
  </WorkspaceShell>;
}
