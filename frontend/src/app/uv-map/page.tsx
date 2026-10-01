import type { Metadata } from "next";
import Link from "next/link";
import { UvMapExplorer } from "@/components/uv/uv-map-explorer";

export const metadata: Metadata = {
  title: "แผนที่ UV ประเทศไทย — Aphrodize",
  description: "สำรวจ UV ท้องฟ้าโปร่งรายจังหวัด สำหรับวันนี้และพรุ่งนี้",
};

export default function UvMapPage() {
  return <main className="uv-map-page" lang="th">
    <header className="uv-map-header">
      <Link href="/">กลับไปหน้าภาพรวม</Link>
      <h1>แผนที่ UV ประเทศไทย</h1>
      <p>วางแผนกลางแจ้งด้วยค่า UV ท้องฟ้าโปร่ง เลือกจังหวัดเพื่อดูรายละเอียดของวันนี้หรือพรุ่งนี้</p>
    </header>
    <UvMapExplorer />
  </main>;
}
