"use client";

import Image from "next/image";
import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";
import { ThemeToggle } from "@/components/theme-toggle";
import { Archive, ArrowLeft, ExternalLink, LockKeyhole, LogOut, Package, Pencil, Plus, Search, Send, ShieldCheck } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import "./products.css";

type Product = {
  id: string;
  brand: string;
  name: string;
  variant: string;
  category: string;
  price_satang: number | null;
  ingredients_label: string;
  ingredients_inci: string[];
  warnings_label: string;
  target_skin_types: string[];
  concerns: string[];
  source_url: string | null;
  status: "draft" | "published" | "archived";
  reviewed_at: string | null;
};

const skinTypes = [
  ["dry", "ผิวแห้ง"], ["normal", "ผิวปกติ"], ["combination", "ผิวผสม"],
  ["oily", "ผิวมัน"], ["all", "ทุกประเภทผิวตามแหล่งข้อมูล"],
] as const;
const statuses = { draft: "รอตรวจ", published: "เผยแพร่", archived: "เก็บเข้าคลัง" };
const categories: Record<string, string> = {
  sunscreen: "กันแดด", moisturizer: "มอยส์เจอไรเซอร์", cleanser: "คลีนเซอร์",
  treatment: "บำรุงเฉพาะทาง", other: "อื่น ๆ",
};

async function requestProducts(method: "GET" | "POST" | "PUT" | "PATCH", body?: object) {
  const response = await fetch("/api/admin/products", {
    method,
    headers: body ? { "Content-Type": "application/json" } : undefined,
    body: body ? JSON.stringify(body) : undefined,
    cache: "no-store",
  });
  const result = await response.json().catch(() => null);
  if (!response.ok) {
    const detail = result?.detail;
    throw new Error(typeof detail === "string" ? detail : "ทำรายการไม่สำเร็จ กรุณาตรวจข้อมูลอีกครั้ง");
  }
  return result;
}

export default function AdminProductsPage() {
  const [access, setAccess] = useState<"loading" | "login" | "ready" | "unconfigured">("loading");
  const [items, setItems] = useState<Product[]>([]);
  const [selected, setSelected] = useState<Product | null>(null);
  const [formVersion, setFormVersion] = useState(0);
  const [search, setSearch] = useState("");
  const [filter, setFilter] = useState("all");
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);

  async function loadProducts() {
    setItems(await requestProducts("GET") as Product[]);
  }

  useEffect(() => {
    fetch("/api/admin/session", { cache: "no-store" }).then((response) => response.json()).then(async (session) => {
      if (!session.configured) return setAccess("unconfigured");
      if (!session.authenticated) return setAccess("login");
      setAccess("ready");
      await loadProducts();
    }).catch(() => setMessage("เชื่อมต่อระบบแอดมินไม่ได้"));
  }, []);

  async function login(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setMessage("");
    const form = new FormData(event.currentTarget);
    try {
      const response = await fetch("/api/admin/session", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username: form.get("username"), password: form.get("password") }),
      });
      const result = await response.json();
      if (!response.ok) throw new Error(result.detail ?? "เข้าสู่ระบบไม่สำเร็จ");
      setAccess("ready");
      await loadProducts();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "เข้าสู่ระบบไม่สำเร็จ");
    } finally {
      setBusy(false);
    }
  }

  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setMessage("");
    const form = new FormData(event.currentTarget);
    const price = String(form.get("price_thb") ?? "").trim();
    if (price && !/^\d{1,7}(\.\d{1,2})?$/.test(price)) {
      setMessage("กรุณากรอกราคาเป็นบาท ทศนิยมไม่เกิน 2 ตำแหน่ง");
      setBusy(false);
      return;
    }
    const [baht, satang = ""] = price.split(".");
    const payload = {
      ...(selected ? { id: selected.id } : {}),
      brand: String(form.get("brand") ?? ""), name: String(form.get("name") ?? ""),
      variant: String(form.get("variant") ?? ""), category: String(form.get("category") ?? ""),
      price_satang: price ? Number(baht) * 100 + Number(satang.padEnd(2, "0")) : null,
      ingredients_label: String(form.get("ingredients_label") ?? ""),
      ingredients_inci: String(form.get("ingredients_inci") ?? "").split("\n").map((item) => item.trim()).filter(Boolean),
      warnings_label: String(form.get("warnings_label") ?? ""),
      target_skin_types: form.getAll("target_skin_types").map(String),
      concerns: String(form.get("concerns") ?? "").split("\n").map((item) => item.trim()).filter(Boolean),
      source_url: String(form.get("source_url") ?? "").trim() || null,
    };
    try {
      await requestProducts(selected ? "PUT" : "POST", payload);
      setSelected(null);
      setFormVersion((value) => value + 1);
      await loadProducts();
      setMessage("บันทึกสินค้าแล้ว สินค้าต้องผ่านการตรวจทานก่อนเผยแพร่");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "บันทึกไม่สำเร็จ");
    } finally {
      setBusy(false);
    }
  }

  async function changeStatus(item: Product, status: Product["status"]) {
    setBusy(true);
    setMessage("");
    try {
      await requestProducts("PATCH", { id: item.id, status });
      await loadProducts();
      setMessage(`เปลี่ยนสถานะ ${item.name} เป็น ${statuses[status]} แล้ว`);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "เปลี่ยนสถานะไม่สำเร็จ");
    } finally {
      setBusy(false);
    }
  }

  async function logout() {
    try {
      const response = await fetch("/api/admin/session", { method: "DELETE" });
      if (!response.ok) throw new Error("ออกจากระบบไม่สำเร็จ");
      setItems([]);
      setAccess("login");
    } catch {
      setMessage("ออกจากระบบไม่สำเร็จ กรุณาลองอีกครั้ง");
    }
  }

  const shown = items.filter((item) =>
    (filter === "all" || item.status === filter) &&
    `${item.brand} ${item.name} ${item.category}`.toLocaleLowerCase().includes(search.toLocaleLowerCase())
  );

  return <main className="admin-products-page">
    <div className="admin-products-container">
      <header className="admin-products-header">
        <div className="admin-products-brand"><Image width={34} height={34} className="admin-brand-mark" src="/assets/aphrodize-logo.svg" alt="" unoptimized /><span>APHRODIZE <strong>STUDIO</strong></span></div>
        <div className="admin-header-actions"><ThemeToggle /><Link href="/" className="admin-back-link"><ArrowLeft size={16} /> กลับหน้าแรก</Link>{access === "ready" && <Button type="button" variant="outline" size="lg" onClick={logout}><LogOut /> ออกจากระบบ</Button>}</div>
      </header>

      {access === "ready" ? <div className="admin-page-intro"><div><p className="eyebrow">PRODUCT CATALOG / ADMIN WORKSPACE</p><h1>จัดการผลิตภัณฑ์</h1><p>บันทึกข้อมูลและตรวจทานก่อนเผยแพร่ เพื่อให้ข้อมูลผลิตภัณฑ์มีแหล่งอ้างอิงชัดเจน</p></div><Button type="button" size="lg" onClick={() => { setSelected(null); setFormVersion((value) => value + 1); document.getElementById("product-editor-heading")?.scrollIntoView({ behavior: "smooth" }); }}><Plus /> เพิ่มผลิตภัณฑ์</Button></div> : null}

      {message && <div className="admin-products-message" role="status" aria-live="polite">{message}</div>}
      {access === "loading" && <Card className="admin-state-card" role="status"><Package size={24} /><p>กำลังตรวจสิทธิ์แอดมิน…</p></Card>}
      {access === "unconfigured" && <Card className="admin-state-card" role="alert"><LockKeyhole size={26} /><h1>ยังไม่พร้อมใช้งาน</h1><p>ตรวจสอบ ADMIN_USERNAME และ ADMIN_PASSWORD ใน backend และ frontend โดยรหัสผ่านต้องมีอย่างน้อย 8 ตัวอักษร</p></Card>}
      {access === "login" && <div className="admin-login-layout">
        <div className="admin-login-intro"><Badge className="admin-intro-badge"><ShieldCheck size={14} /> พื้นที่สำหรับผู้ดูแล</Badge><h1>ข้อมูลผลิตภัณฑ์<br /><span>ที่ตรวจสอบได้</span></h1><p>จัดระเบียบส่วนผสม กลุ่มผิว และแหล่งข้อมูลในที่เดียว ก่อนนำข้อมูลไปใช้กับการแนะนำผลิตภัณฑ์</p><div className="admin-login-note"><Package size={20} /><span>แคตตาล็อกนี้แยกจากบัญชีผู้ใช้ทั่วไป</span></div></div>
        <Card className="admin-login-card"><div className="admin-login-icon"><LockKeyhole size={24} /></div><p className="eyebrow">ADMIN ACCESS</p><h2>เข้าสู่ระบบแอดมิน</h2><p className="admin-card-description">ใช้ชื่อผู้ใช้และรหัสผ่านแอดมินที่ตั้งไว้ในระบบ</p><form onSubmit={login}><label htmlFor="admin-username">ชื่อผู้ใช้<Input id="admin-username" name="username" autoComplete="username" placeholder="ชื่อผู้ใช้แอดมิน" required /></label><label htmlFor="admin-password">รหัสผ่าน<Input id="admin-password" name="password" type="password" autoComplete="current-password" placeholder="รหัสผ่านแอดมิน" required /></label><Button type="submit" size="lg" disabled={busy}>{busy ? "กำลังเข้าสู่ระบบ…" : "เข้าสู่ระบบ"}</Button></form><p className="admin-login-footnote"><ShieldCheck size={14} /> สำหรับผู้ดูแลระบบเท่านั้น</p></Card>
      </div>}

      {access === "ready" && <>
        <div className="admin-summary" aria-label="ภาพรวมผลิตภัณฑ์">{([ ["ทั้งหมด", items.length, "all"], ["รอตรวจ", items.filter((item) => item.status === "draft").length, "draft"], ["เผยแพร่", items.filter((item) => item.status === "published").length, "published"], ["เก็บเข้าคลัง", items.filter((item) => item.status === "archived").length, "archived"] ] as const).map(([label, count, status]) => <Card key={status} className={`admin-summary-card ${status}`}><span>{label}</span><strong>{count}</strong></Card>)}</div>
        <div className="admin-products-layout">
          <section aria-label="รายการผลิตภัณฑ์"><Card className="admin-products-list"><div className="admin-products-heading"><div><p className="eyebrow">CATALOG</p><h2>รายการผลิตภัณฑ์</h2><p>เลือกสินค้าเพื่อแก้ไขข้อมูลหรือเปลี่ยนสถานะ</p></div><Badge className="admin-count-badge">{shown.length} รายการ</Badge></div><div className="admin-products-filters"><div className="admin-search"><Search size={18} aria-hidden="true" /><Input aria-label="ค้นหาสินค้า" placeholder="ค้นหาชื่อ แบรนด์ หรือหมวดสินค้า" value={search} onChange={(event) => setSearch(event.target.value)} /></div><select className="admin-select" aria-label="กรองสถานะ" value={filter} onChange={(event) => setFilter(event.target.value)}><option value="all">ทุกสถานะ</option><option value="draft">รอตรวจ</option><option value="published">เผยแพร่</option><option value="archived">เก็บเข้าคลัง</option></select></div>
            {shown.length === 0 && <div className="admin-empty"><Package size={28} /><h3>{items.length === 0 ? "ยังไม่มีผลิตภัณฑ์" : "ไม่พบผลิตภัณฑ์"}</h3><p>{items.length === 0 ? "เริ่มเพิ่มผลิตภัณฑ์แรกได้จากฟอร์มด้านขวา" : "ลองเปลี่ยนคำค้นหาหรือตัวกรองสถานะ"}</p></div>}
            <div className="admin-product-rows">{shown.map((item) => <article key={item.id} className={`admin-product-row ${selected?.id === item.id ? "selected" : ""}`}><div className="admin-product-avatar" aria-hidden="true"><Package size={20} /></div><div className="admin-product-details"><div className="admin-product-title"><strong>{item.name}</strong><Badge className={`admin-product-status ${item.status}`}>{statuses[item.status]}</Badge></div><p>{item.brand}{item.variant && ` · ${item.variant}`}</p><div className="admin-product-meta"><span>{categories[item.category] ?? item.category}</span><span aria-hidden="true">·</span><span>{item.price_satang === null ? "ยังไม่ระบุราคา" : `${(item.price_satang / 100).toLocaleString("th-TH")} บาท`}</span></div><div className="admin-product-actions"><Button type="button" variant="outline" size="sm" disabled={busy} onClick={() => { setSelected(item); document.getElementById("product-editor-heading")?.scrollIntoView({ behavior: "smooth" }); }}><Pencil /> แก้ไข</Button>{item.status !== "published" && <Button type="button" variant="outline" size="sm" disabled={busy} onClick={() => changeStatus(item, "published")}><Send /> เผยแพร่</Button>}{item.status !== "archived" && <Button type="button" variant="ghost" size="sm" disabled={busy} onClick={() => changeStatus(item, "archived")}><Archive /> เก็บเข้าคลัง</Button>}</div></div></article>)}</div>
          </Card></section>
          <aside><Card className="admin-products-editor"><div className="admin-editor-heading"><div className="admin-editor-icon"><Pencil size={20} /></div><div><p className="eyebrow">PRODUCT DETAILS</p><h2 id="product-editor-heading">{selected ? "แก้ไขผลิตภัณฑ์" : "เพิ่มผลิตภัณฑ์"}</h2></div></div><p className="admin-editor-description">{selected ? `กำลังแก้ไข ${selected.brand} · ${selected.name}` : "กรอกข้อมูลจากฉลากและแหล่งอ้างอิงที่ตรวจสอบได้"}</p><form key={`${selected?.id ?? "new"}-${formVersion}`} onSubmit={save}>
            <div className="admin-form-section"><h3>ข้อมูลทั่วไป</h3><div className="admin-form-grid"><label>แบรนด์ <span>*</span><Input name="brand" required maxLength={120} placeholder="ชื่อแบรนด์" defaultValue={selected?.brand ?? ""} /></label><label>ชื่อสินค้า <span>*</span><Input name="name" required maxLength={200} placeholder="ชื่อผลิตภัณฑ์" defaultValue={selected?.name ?? ""} /></label><label>รุ่น / ขนาด<Input name="variant" maxLength={120} placeholder="เช่น 50 ml" defaultValue={selected?.variant ?? ""} /></label><label>หมวดสินค้า <span>*</span><select className="admin-select" name="category" required defaultValue={selected?.category ?? ""}><option value="" disabled>เลือกหมวดสินค้า</option><option value="sunscreen">กันแดด</option><option value="moisturizer">มอยส์เจอไรเซอร์</option><option value="cleanser">คลีนเซอร์</option><option value="treatment">ผลิตภัณฑ์บำรุงเฉพาะทาง</option><option value="other">อื่น ๆ</option></select></label><label className="admin-full-width">ราคา (บาท)<Input name="price_thb" type="number" min="0" max="1000000" step="0.01" placeholder="0.00" defaultValue={selected?.price_satang == null ? "" : (selected.price_satang / 100).toFixed(2)} /></label></div></div>
            <div className="admin-form-section"><h3>ส่วนผสมและคำเตือน</h3><label>ส่วนผสมตามฉลาก<Textarea name="ingredients_label" maxLength={10000} rows={3} placeholder="คัดลอกรายการส่วนผสมตามฉลาก" defaultValue={selected?.ingredients_label ?? ""} /></label><label>ชื่อส่วนผสม INCI ที่ตรวจทานแล้ว<Textarea name="ingredients_inci" rows={3} placeholder="หนึ่งรายการต่อบรรทัด" defaultValue={selected?.ingredients_inci.join("\n") ?? ""} /><small>หนึ่งรายการต่อบรรทัด</small></label><label>คำเตือนบนฉลาก<Textarea name="warnings_label" rows={2} placeholder="ระบุคำเตือน ถ้ามี" defaultValue={selected?.warnings_label ?? ""} /></label></div>
            <div className="admin-form-section"><h3>ข้อมูลสำหรับการจัดกลุ่ม</h3><fieldset><legend>ประเภทผิวที่แหล่งข้อมูลระบุ</legend><div className="admin-skin-types">{skinTypes.map(([value, label]) => <label key={value} className="admin-checkbox"><input type="checkbox" name="target_skin_types" value={value} defaultChecked={selected?.target_skin_types.includes(value)} />{label}</label>)}</div></fieldset><label>ปัญหาผิวที่ระบุ<Textarea name="concerns" rows={2} placeholder="หนึ่งรายการต่อบรรทัด" defaultValue={selected?.concerns.join("\n") ?? ""} /></label></div>
            <div className="admin-form-section"><h3>แหล่งข้อมูล</h3><label>URL แหล่งข้อมูล<div className="admin-source-input"><ExternalLink size={16} aria-hidden="true" /><Input name="source_url" type="url" maxLength={1000} placeholder="https://..." defaultValue={selected?.source_url ?? ""} /></div></label><p className="admin-review-note"><ShieldCheck size={16} /> ประเภทผิวเป็นข้อมูลจากแหล่งอ้างอิง ไม่ได้รับรองว่าทุกคนจะไม่ระคายเคือง</p></div>
            <div className="admin-form-actions">{selected && <Button type="button" variant="outline" onClick={() => setSelected(null)}>ยกเลิกการแก้ไข</Button>}<Button type="submit" size="lg" disabled={busy}>{busy ? "กำลังบันทึก…" : "บันทึกเป็นฉบับรอตรวจ"}</Button></div>
          </form></Card></aside>
        </div>
      </>}
    </div>
  </main>;
}
