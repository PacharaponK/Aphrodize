/* Full page navigation reinitializes the prototype scripts. */
/* eslint-disable @next/next/no-html-link-for-pages */
import type { Metadata } from "next";
import Image from "next/image";

export const metadata: Metadata = { title: "คำแนะนำ — Aphrodize" };

export default function Page() {
  return (
    <>
      <div className="simple-page"><main className="page-frame"><header className="page-header"><a className="page-brand" href="/"><Image width={40} height={40} src="/assets/aphrodize-contour-a.svg" alt="" />Aphrodize</a><nav className="page-nav"><a className="active" href="/">ภาพรวม</a><a href="/capture">วิเคราะห์ภาพ</a><a href="/trend">แนวโน้ม</a></nav></header><section className="page-content"><p className="eyebrow">คำแนะนำจากกฎ</p><h1>คำแนะนำที่ผ่าน safety check</h1><p>คำแนะนำนี้เป็นข้อมูลประกอบ ไม่ใช่การรักษาหรือการยืนยันสาเหตุ</p><article className="recommendation-card"><span className="status moderate">ข้อมูลประกอบ</span><h2>ดูแลเกราะป้องกันผิวและป้องกันแดด</h2><p>หมวดผลิตภัณฑ์: moisturizer และ broad-spectrum sunscreen SPF 30+</p><div className="rule-box"><h3>เหตุผลและแหล่งข้อมูล</h3><p>ผลภาพ: periocular wrinkle score ผ่าน confidence threshold</p><p>คุณรายงาน: ผิวแห้ง, UV exposure สูง และใช้ sunscreen ไม่สม่ำเสมอ</p><p className="metadata">Rule R-UV-001 · version 1.0 · ไม่ยืนยันว่า UV เป็นสาเหตุ</p></div></article><div className="page-actions"><a className="secondary-button" href="/result-detail">กลับผลรายบริเวณ</a><a className="primary-button" href="/capture">ถ่ายภาพครั้งถัดไป →</a></div></section></main></div>
    </>
  );
}



