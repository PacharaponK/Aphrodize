import Link from "next/link";
import { ArrowUpRight, Database, FlaskConical, FolderOpen, Gauge, House, PencilRuler, Server, Store } from "lucide-react";
import { pageMetadata } from "@/lib/page-metadata";
import "./portal.css";

export const dynamic = "force-dynamic";
export const metadata = pageMetadata("Services portal", "รวมทางเข้า Label Studio, MinIO, MLflow, Grafana และเครื่องมือจัดการของ Aphrodize", "/portal", false, "th_TH");

function serviceUrl(value: string | undefined) {
  if (!value) return undefined;
  try {
    const url = new URL(value);
    return ["https:", "http:"].includes(url.protocol) && !url.username && !url.password ? url.href : undefined;
  } catch {
    return undefined;
  }
}

export default function PortalPage() {
  const services = [
    { name: "Aphrodize", description: "ภาพรวม วิเคราะห์ภาพ และบันทึกสุขภาพรายวัน", href: "/", Icon: House },
    { name: "Label Studio", description: "ตรวจทานภาพและวาด annotation สำหรับชุดข้อมูล", href: "/label-studio/", Icon: PencilRuler },
    { name: "MinIO Console", description: "จัดการ buckets ภาพ และไฟล์ artifacts", href: serviceUrl(process.env.PORTAL_MINIO_URL), Icon: FolderOpen, unavailable: "ยังไม่ได้ตั้งค่าทางเข้า Console" },
    { name: "MLflow", description: "ดู experiments, training runs และ model artifacts", href: serviceUrl(process.env.PORTAL_MLFLOW_URL), Icon: FlaskConical, unavailable: "ยังไม่ได้เปิดทางเข้า MLflow บน VM" },
    { name: "Grafana", description: "ดูสถานะระบบ metrics, logs และการแจ้งเตือน", href: "/grafana/", Icon: Gauge },
    { name: "Product admin", description: "ตรวจทานและจัดการแคตตาล็อกผลิตภัณฑ์", href: "/admin", Icon: Store },
  ];

  return (
    <main className="service-portal" lang="th">
      <header className="portal-intro">
        <h1>Services portal</h1>
        <p>เครื่องมือของ Aphrodize รวมไว้ในที่เดียว เลือกบริการที่ต้องการเข้าใช้งาน</p>
      </header>

      <section aria-labelledby="portal-tools-heading">
        <h2 id="portal-tools-heading">ทางเข้าใช้งาน</h2>
        <p className="portal-help">แต่ละบริการใช้บัญชีของตัวเอง ลิงก์ที่เปิดได้ยังไม่ได้หมายความว่าบริการออนไลน์อยู่</p>
        <ul className="portal-services">
          {services.map(({ name, description, href, Icon, unavailable }) => (
            <li className="portal-service" key={name}>
              <Icon className="portal-service-icon" size={24} aria-hidden="true" />
              <div className="portal-service-copy"><h3>{name}</h3><p>{description}</p></div>
              {href ? (
                href.startsWith("/") && !["/label-studio/", "/grafana/"].includes(href) ? (
                  <Link className="portal-open" href={href}>เปิด {name}<ArrowUpRight size={18} aria-hidden="true" /></Link>
                ) : (
                  <a className="portal-open" href={href}>เปิด {name}<ArrowUpRight size={18} aria-hidden="true" /></a>
                )
              ) : <span className="portal-unavailable">{unavailable}</span>}
            </li>
          ))}
        </ul>
      </section>

      <section className="portal-infrastructure" aria-labelledby="portal-infra-heading">
        <h2 id="portal-infra-heading"><Server size={22} aria-hidden="true" /> บริการเบื้องหลัง</h2>
        <p>บริการเหล่านี้ทำงานให้แอปและเครื่องมือด้านบน ใช้ Grafana ดูภาพรวม หรือเชื่อมต่อผ่านเครื่องมือของผู้ดูแลระบบ</p>
        <details>
          <summary>ดูบริการและวิธีเชื่อมต่อ</summary>
          <dl className="portal-infra-list">
            <div><dt><Database size={18} aria-hidden="true" /> PostgreSQL</dt><dd>ฐานข้อมูล · ใช้ database client ผ่าน SSH tunnel ที่พอร์ต 5432</dd></div>
            <div><dt>Redis</dt><dd>คิวและ cache · ใช้ Redis client ผ่าน SSH tunnel ที่พอร์ต 6379</dd></div>
            <div><dt>MinIO API</dt><dd>S3 API · ใช้ S3 client ผ่าน SSH tunnel ที่พอร์ต 9000; หน้าเว็บจัดการอยู่ที่ MinIO Console</dd></div>
            <div><dt>Prometheus</dt><dd>Metrics · ดูผ่าน Grafana หรือ SSH tunnel ที่พอร์ต 9090</dd></div>
            <div><dt>Loki</dt><dd>Logs · เปิด Grafana แล้วเลือก Explore และ Loki</dd></div>
            <div><dt>Alloy / exporters</dt><dd>เก็บ logs, host metrics และผลตรวจ endpoints · ดูผ่าน Grafana</dd></div>
            <div><dt>API / workers</dt><dd>ให้บริการแอปและประมวลผลงาน · ดูสถานะและ logs ผ่าน Grafana</dd></div>
            <div><dt>Caddy</dt><dd>HTTPS และ routing · ดูสถานะและ logs ผ่าน Grafana</dd></div>
          </dl>
          <p className="portal-help">ตัวอย่างเปิด Prometheus จากคอมพิวเตอร์ของคุณ:</p>
          <pre><code>ssh -N -L 9090:127.0.0.1:9090 aphrodize@172.30.81.237</code></pre>
          <p className="portal-help">เมื่อเชื่อมต่อ SSH แล้ว เปิด <a href="http://localhost:9090">http://localhost:9090</a> ในเบราว์เซอร์บนเครื่องเดียวกัน</p>
        </details>
      </section>
    </main>
  );
}
