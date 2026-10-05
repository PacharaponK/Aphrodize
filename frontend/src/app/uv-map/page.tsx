import { pageMetadata } from "@/lib/page-metadata";
import { UvMapExplorer, UvMapHeader } from "@/components/uv/uv-map-explorer";

export const metadata = pageMetadata(
  "แผนที่ UV",
  "สำรวจประมาณการ UV ตอนเที่ยงภายใต้ท้องฟ้าโปร่งรายจังหวัด สำหรับวันนี้และพรุ่งนี้ เพื่อวางแผนกิจกรรมกลางแจ้งและการป้องกันแดด",
  "/uv-map",
  true,
  "th_TH",
);

export default function UvMapPage() {
  return <main className="uv-map-page">
    <UvMapHeader />
    <UvMapExplorer />
  </main>;
}
