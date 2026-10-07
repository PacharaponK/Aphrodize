import { pageMetadata } from "@/lib/page-metadata";

export const metadata = pageMetadata(
  "จัดการผลิตภัณฑ์",
  "จัดการข้อมูลผลิตภัณฑ์ดูแลผิว ตรวจทานฉลาก ส่วนผสม ราคา แหล่งอ้างอิง และสถานะการเผยแพร่ในแคตตาล็อก Aphrodize",
  "/admin",
  false,
  "th_TH",
);

export default function Layout({ children }: { children: React.ReactNode }) {
  return children;
}
