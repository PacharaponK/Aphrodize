"use client";

import { useEffect, useId, useState } from "react";
import Image from "next/image";
import { useLanguage } from "../language-provider";

type Sunscreen = {
  brand: string; name: string; spf: number; broad_spectrum: boolean;
  water_resistant_minutes: number | null; source_url: string; target_skin_types: string[];
  image_url?: string | null;
  variant?: string; market?: string | null; suitable_for_sensitive_skin?: boolean;
};

type Skin = "unknown" | "normal" | "dry" | "oily" | "combination" | "sensitive";
type Activity = "daily" | "outdoor" | "sports" | "swimming";

export function suitableSunscreens(products: Sunscreen[], uv: number, skin: Skin = "unknown", activity: Activity = "daily") {
  const needsWaterResistance = activity === "sports" || activity === "swimming";
  const eligible = products.filter((p) => p.broad_spectrum && p.spf >= 30
    && (skin === "unknown" || (skin === "sensitive" ? p.suitable_for_sensitive_skin === true || p.target_skin_types?.includes("sensitive") : p.target_skin_types?.includes(skin) || p.target_skin_types?.includes("all")))
    && (!needsWaterResistance || p.water_resistant_minutes === 40 || p.water_resistant_minutes === 80));
  const preferred = uv >= 8 ? eligible.filter((p) => p.spf >= 50) : eligible;
  return (preferred.length ? preferred : eligible).slice(0, 5);
}

export function UvSunscreens({ provinceName, uv }: { provinceName: string; uv: number | null }) {
  const { language } = useLanguage();
  const t = (th: string, en: string) => language === "en" ? en : th;
  const [catalog, setCatalog] = useState<Sunscreen[] | null>(null);
  const [error, setError] = useState(false);
  const [attempt, setAttempt] = useState(0);
  const [skin, setSkin] = useState<Skin>("unknown");
  const [activity, setActivity] = useState<Activity>("daily");
  const filterId = useId();
  useEffect(() => {
    const controller = new AbortController();
    fetch("/api/uv/products", { cache: "no-store", signal: controller.signal })
      .then(async (response) => {
        const payload = await response.json();
        if (!response.ok || !Array.isArray(payload)) throw new Error("catalog_unavailable");
        return payload as Sunscreen[];
      })
      .then((payload) => { if (!controller.signal.aborted) setCatalog(payload); })
      .catch(() => { if (!controller.signal.aborted) setError(true); });
    return () => controller.abort();
  }, [attempt]);
  const products = catalog && uv !== null ? suitableSunscreens(catalog, uv, skin, activity) : [];
  const needsWaterResistance = activity === "sports" || activity === "swimming";
  const skinNames: Record<string, string> = language === "en"
    ? { all: "all skin types", normal: "normal", dry: "dry", oily: "oily", combination: "combination", sensitive: "sensitive" }
    : { all: "ทุกสภาพผิว", normal: "ผิวธรรมดา", dry: "ผิวแห้ง", oily: "ผิวมัน", combination: "ผิวผสม", sensitive: "ผิวบอบบาง" };
  const activities: Record<Activity, string> = language === "en"
    ? { daily: "Everyday use", outdoor: "Travel / time outdoors", sports: "Sports / sweating", swimming: "Swimming / water activities" }
    : { daily: "ใช้ประจำวัน", outdoor: "เดินทาง / อยู่กลางแจ้ง", sports: "เล่นกีฬา / เหงื่อออก", swimming: "ว่ายน้ำ / กิจกรรมทางน้ำ" };
  return <section className="uv-map-sunscreens" aria-label={t(`กันแดดสำหรับ${provinceName}`, `Sunscreens for ${provinceName}`)}>
    <div className="uv-sunscreen-filters">
      <label htmlFor={`${filterId}-skin`}>{t("สภาพผิวของคุณ", "Your skin type")}
        <select id={`${filterId}-skin`} value={skin} onChange={(event) => setSkin(event.target.value as Skin)}>
          <option value="unknown">{t("ยังไม่ระบุ / ไม่แน่ใจ", "Not specified / unsure")}</option>
          {(["normal", "dry", "oily", "combination", "sensitive"] as const).map((value) => <option key={value} value={value}>{skinNames[value]}</option>)}
        </select>
      </label>
      <label htmlFor={`${filterId}-activity`}>{t("กิจกรรมของคุณ", "Your activity")}
        <select id={`${filterId}-activity`} value={activity} onChange={(event) => setActivity(event.target.value as Activity)}>
          {Object.entries(activities).map(([value, label]) => <option key={value} value={value}>{label}</option>)}
        </select>
      </label>
    </div>
    <p className="uv-sunscreen-preference-note">{t("ใช้ตัวเลือกที่คุณระบุเพื่อคัดสินค้าในครั้งนี้ ไม่บันทึกลงโปรไฟล์", "These choices filter this visit’s products and are not saved to your profile.")}</p>
    <h3>{t("คุณสมบัติที่ควรเลือก", "What to look for")}</h3>
    <p>{t("ป้องกัน UVA/UVB และ SPF 30 ขึ้นไป", "UVA/UVB protection and SPF 30+")}{skin !== "unknown" && t(` · ข้อมูลผลิตภัณฑ์ระบุเหมาะกับ${skinNames[skin]}`, ` · Product information suitable for ${skinNames[skin]} skin`)}</p>
    {needsWaterResistance && <p>{t("กิจกรรมนี้ควรเลือกสูตรที่ยืนยันการทนน้ำ 40 หรือ 80 นาทีตามฉลาก ทาซ้ำตามช่วงเวลาที่ระบุขณะว่ายน้ำหรือเหงื่อออก และทันทีหลังเช็ดตัว", "For this activity, choose verified 40- or 80-minute water resistance. Reapply at the label’s interval while swimming or sweating and immediately after towel drying.")}</p>}
    {activity === "outdoor" && <p>{t("วางแผนพักในร่ม ใช้หมวกและเสื้อผ้าป้องกันแดด โดยเฉพาะช่วงเที่ยง หากเหงื่อออกให้เลือกกิจกรรมเล่นกีฬาเพื่อคัดสูตรทนน้ำ", "Plan shade breaks and use a hat and protective clothing, especially around midday. If sweating, select Sports to filter water-resistant formulas.")}</p>}
    {skin === "sensitive" && <p>{t("คำว่าเหมาะกับทุกสภาพผิวไม่ยืนยันว่าเหมาะกับผิวบอบบาง หน้านี้จะแสดงเฉพาะสินค้าที่มีข้อมูลตรวจทานด้านนี้โดยตรง ตรวจส่วนผสมที่คุณเคยแพ้และฉลากก่อนใช้", "An all-skin-types label does not confirm suitability for sensitive skin. Only products explicitly reviewed for this are shown. Check your known allergens and the current label before use.")}</p>}
    {uv === null ? <p>{t("รอค่า UV ที่พร้อมใช้ก่อนแนะนำผลิตภัณฑ์สำหรับจังหวัดและวันที่ที่เลือก", "An available UV reading is needed to recommend products for this province and day.")}</p> : <>
      <p>{uv >= 8
        ? t("UV สูงมากขึ้นไป: หน้านี้เลือกแสดง SPF 50 ขึ้นไปก่อน หากไม่มีจะแสดง SPF 30 ขึ้นไปที่ผ่านเกณฑ์พื้นฐาน", "Very high or extreme UV: this page prefers SPF 50+ options, falling back to eligible SPF 30+ products.")
        : t("เลือกจากกันแดดป้องกัน UVA/UVB ที่มี SPF 30 ขึ้นไปตามฉลาก เหมาะสำหรับใช้ร่วมกับการป้องกันแดดตามระดับ UV ที่เลือก", "Select label-verified UVA/UVB protection with SPF 30+, alongside protection appropriate to the selected UV level.")}</p>
      <h3>{t("ผลิตภัณฑ์ที่ตรงกับตัวเลือก", "Products matching your choices")}</h3>
      {catalog !== null && !error && <p role="status">{t(`พบ ${products.length} ตัว · ${skin === "unknown" ? "ยังไม่ระบุสภาพผิว" : skinNames[skin]} · ${activities[activity]}`, `${products.length} matches · ${skin === "unknown" ? "skin unspecified" : skinNames[skin]} · ${activities[activity]}`)}</p>}
      {error ? <div role="alert"><p>{t("โหลดรายการกันแดดไม่สำเร็จ", "Could not load sunscreens.")}</p><button type="button" onClick={() => { setError(false); setCatalog(null); setAttempt((value) => value + 1); }}>{t("ลองโหลดกันแดดอีกครั้ง", "Retry sunscreens")}</button></div>
        : catalog === null ? <p role="status">{t("กำลังโหลดกันแดดที่ผ่านการตรวจทาน…", "Loading reviewed sunscreens…")}</p>
        : products.length === 0 ? <p className="uv-sunscreen-empty">{t("ยังไม่มีกันแดดที่ผ่านการตรวจทานและมีข้อมูลครบตรงกับสภาพผิวและกิจกรรมนี้ เลือกตามคุณสมบัติด้านบน หรือลองเปลี่ยนตัวเลือกให้ตรงกับการใช้งานจริง", "No reviewed sunscreen has complete label information matching this skin type and activity. Use the criteria above, or adjust your choices to match your actual use.")}</p>
        : <ul>{products.map((product) => <li key={product.source_url}>
          <div className="uv-sunscreen-media">
            {product.image_url && <Image src={product.image_url} alt={`${product.brand} ${product.name}`} width={160} height={160} unoptimized referrerPolicy="no-referrer" onError={(event) => { event.currentTarget.hidden = true; }} />}
            <span className="uv-sunscreen-image-placeholder">{t("ไม่มีภาพสินค้า", "No product image")}</span>
          </div>
          <div className="uv-sunscreen-product-body">
          <h4>{product.brand} {product.name}</h4>
          {(product.variant || product.market) && <p>{[product.variant, product.market ? t(`สูตรตลาด ${product.market}`, `Market: ${product.market}`) : ""].filter(Boolean).join(" · ")}</p>}
          <p><strong>SPF {product.spf}</strong> · {t("ป้องกัน UVA/UVB", "UVA/UVB protection")}</p>
          <p>{t("เหตุผลที่แนะนำ: ผ่านเกณฑ์ broad-spectrum SPF 30 ขึ้นไป", "Why it fits: meets the broad-spectrum SPF 30+ baseline")}{uv >= 8 && product.spf >= 50 && t(" และอยู่ในกลุ่ม SPF 50 ขึ้นไปที่หน้านี้เลือกแสดงก่อนสำหรับ UV สูงมาก", " and matches this page’s SPF 50+ preference for very high UV")}</p>
          {skin !== "unknown" && <p>{t(`เหมาะกับตัวเลือก${skinNames[skin]}ตามข้อมูลผลิตภัณฑ์${skin !== "sensitive" && product.target_skin_types.includes("all") ? " (ระบุทุกสภาพผิว)" : ""}`, `Matches your ${skinNames[skin]} skin choice per product information${skin !== "sensitive" && product.target_skin_types.includes("all") ? " (labeled for all skin types)" : ""}`)}</p>}
          {needsWaterResistance && <p>{t(`ตรงกับกิจกรรม${activities[activity]}: มีข้อมูลทนน้ำ ${product.water_resistant_minutes} นาที`, `Matches ${activities[activity]}: verified ${product.water_resistant_minutes}-minute water resistance`)}</p>}
          {product.target_skin_types?.length > 0 && <p>{t("สภาพผิวตามข้อมูลผลิตภัณฑ์: ", "Label skin types: ")}{product.target_skin_types.map((skin) => skinNames[skin] ?? skin).join(language === "en" ? ", " : " / ")}</p>}
          <p>{product.water_resistant_minutes
            ? t(`ทนน้ำ ${product.water_resistant_minutes} นาทีตามฉลาก; ทาซ้ำหลังว่ายน้ำ เหงื่อออก หรือเช็ดตัวตามฉลาก`, `Water resistant for ${product.water_resistant_minutes} minutes per label; follow reapplication instructions after swimming, sweating or towel drying.`)
            : t("ไม่มีข้อมูลยืนยันการทนน้ำ หากว่ายน้ำหรือเหงื่อออกให้เลือกสูตรที่ระบุทนน้ำบนฉลาก", "Water resistance is unverified. For swimming or sweating, choose a formula labeled water resistant.")}</p>
          <a href={product.source_url} target="_blank" rel="noopener noreferrer">{t("ดูข้อมูลจากผู้ผลิต ↗", "View manufacturer details ↗")}</a>
          </div>
        </li>)}</ul>}
      <p>{t("คัดจาก UV จังหวัด/วันที่ สภาพผิวและกิจกรรมที่คุณระบุ กับข้อมูลผลิตภัณฑ์ ไม่ใช่การวินิจฉัยหรือรับประกันว่าไม่แพ้ ทาซ้ำอย่างน้อยทุก 2 ชั่วโมงขณะอยู่กลางแจ้ง และตามฉลากหลังว่ายน้ำ เหงื่อออก หรือเช็ดตัว ใช้ร่มเงา เสื้อผ้า และหมวกร่วมด้วย", "Matches use the province/day’s UV, your reported skin and activity, and product information. They are not a diagnosis or allergy guarantee. Reapply at least every two hours outdoors and per label after swimming, sweating or towel drying. Use shade, clothing and a hat.")}</p>
      <a href="https://www.aad.org/public/everyday-care/sun-protection/shade-clothing-sunscreen/how-to-select-sunscreen" target="_blank" rel="noopener noreferrer">{t("แนวทางเลือกกันแดดจาก AAD ↗", "AAD sunscreen selection guidance ↗")}</a>
    </>}
  </section>;
}
