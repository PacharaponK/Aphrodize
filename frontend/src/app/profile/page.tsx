/* Full page navigation reinitializes the prototype scripts. */
/* eslint-disable @next/next/no-html-link-for-pages */
import type { Metadata } from "next";
import Image from "next/image";

export const metadata: Metadata = { title: "Skin profile — Aphrodize" };

export default function Page() {
  return (
    <>
      <div className="simple-page"><main className="page-frame"><header className="page-header"><a className="page-brand" href="/"><Image width={40} height={40} src="/assets/aphrodize-contour-a.svg" alt="" />Aphrodize</a><nav className="page-nav"><a href="/">ภาพรวม</a><a href="/capture">วิเคราะห์ภาพ</a><a href="/trend">แนวโน้ม</a><a className="active" href="/profile">Skin profile</a></nav></header><section className="page-content" id="privacy"><p className="eyebrow">SELF-REPORTED PROFILE</p><h1>Skin profile ของคุณ</h1><p>ข้อมูลในหน้านี้มาจากสิ่งที่คุณรายงาน ไม่ใช่ผลตรวจจากภาพ</p><article className="recommendation-card"><h2>ผิวแห้ง · ระคายง่าย</h2><p>UV exposure: สูง · Sunscreen: ใช้ไม่สม่ำเสมอ</p><div className="rule-box"><h3>Consent และข้อมูล</h3><p>Consent version 1.0 · คุณสามารถเปลี่ยนหรือถอน consent และขอลบภาพ/mask/ผลวิเคราะห์ได้</p><a className="secondary-button" href="/">กลับหน้าภาพรวม</a></div></article></section></main></div>
    </>
  );
}



