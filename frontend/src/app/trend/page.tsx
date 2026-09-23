/* Full page navigation reinitializes the prototype scripts. */
/* eslint-disable @next/next/no-html-link-for-pages */
import type { Metadata } from "next";
import Image from "next/image";

export const metadata: Metadata = { title: "แนวโน้ม — Aphrodize" };

export default function Page() {
  return (
    <>
      <div className="simple-page"><main className="page-frame"><header className="page-header"><a className="page-brand" href="/"><Image width={40} height={40} src="/assets/aphrodize-contour-a.svg" alt="" />Aphrodize</a><nav className="page-nav"><a href="/">ภาพรวม</a><a href="/capture">วิเคราะห์ภาพ</a><a className="active" href="/trend">แนวโน้ม</a></nav></header><section className="page-content"><p className="eyebrow">HISTORY</p><h1>แนวโน้มของคุณ</h1><p>แสดงเฉพาะ observations จากภาพที่ผ่าน capture protocol และ quality gate</p><div className="trend-empty"><div className="trend-icon">⌁</div><h2>เริ่มติดตามแนวโน้มได้แล้ว</h2><p>มีภาพที่ผ่าน quality gate 1 ครั้ง อีก 1 ครั้งจะแสดงแนวโน้มเปรียบเทียบให้</p><div className="trend-line"></div><a className="primary-button" href="/capture">ถ่ายภาพครั้งถัดไป →</a></div></section></main></div>
    </>
  );
}



