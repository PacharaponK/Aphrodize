import { pageMetadata } from "@/lib/page-metadata";
import Link from "next/link";
import { UvMapExplorer } from "@/components/uv/uv-map-explorer";

export const metadata = pageMetadata(
  "แผนที่ UV",
  "สำรวจประมาณการ UV ตอนเที่ยงภายใต้ท้องฟ้าโปร่งรายจังหวัด สำหรับวันนี้และพรุ่งนี้ เพื่อวางแผนกิจกรรมกลางแจ้งและการป้องกันแดด",
  "/uv-map",
  true,
  "th_TH",
);

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
