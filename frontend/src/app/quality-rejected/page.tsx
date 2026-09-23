/* Full page navigation reinitializes the prototype scripts. */
/* eslint-disable @next/next/no-html-link-for-pages */
import type { Metadata } from "next";
import Image from "next/image";

export const metadata: Metadata = { title: "ภาพยังไม่ผ่าน — Aphrodize" };

export default function Page() {
  return (
    <>
      <div className="simple-page"><main className="page-frame"><header className="page-header"><a className="page-brand" href="/"><Image width={40} height={40} src="/assets/aphrodize-contour-a.svg" alt="" />Aphrodize</a><nav className="page-nav"><a href="/">ภาพรวม</a><a className="active" href="/capture">วิเคราะห์ภาพ</a><a href="/trend">แนวโน้ม</a></nav></header><section className="page-content quality-panel"><div className="quality-symbol">!</div><p className="eyebrow">QUALITY GATE</p><h1>ภาพนี้ยังใช้เปรียบเทียบไม่ได้</h1><p>จึงไม่นำไปคำนวณผลหรือแนวโน้ม เพื่อไม่ให้ความต่างของภาพถูกตีความว่าเป็นความเปลี่ยนแปลงของผิว</p><ul className="quality-list"><li>แสงน้อยเกินไป</li><li>ภาพอาจเบลอ</li></ul><p className="metadata">ลองหันหน้าเข้าหาแสงนุ่มที่สม่ำเสมอ และวางกล้องให้นิ่ง</p><div className="page-actions"><a className="primary-button" href="/capture">ถ่ายภาพใหม่ →</a><a className="secondary-button" href="/">กลับหน้าภาพรวม</a></div></section></main></div>
    </>
  );
}



