"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { WorkspaceShell } from "@/components/workspace-shell";

type Profile = { display_name: string; email: string; profile: Record<string, unknown> | null };

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
        {profile.profile ? <><h2>ข้อมูลโปรไฟล์ที่บันทึกไว้</h2><dl className="profile-answers">{Object.entries(profile.profile).map(([key, value]) => <div key={key}><dt>{labels[key] ?? key}</dt><dd>{displayValue(value)}</dd></div>)}</dl><Link href="/onboarding/health">แก้ไขโปรไฟล์</Link></> : <div className="empty-state"><p>ยังไม่มีข้อมูลโปรไฟล์</p><Link className="primary-button" href="/onboarding/health">เริ่มกรอกข้อมูล →</Link></div>}</>}
    </section>
  </WorkspaceShell>;
}
