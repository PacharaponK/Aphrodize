"use client";

import { useLanguage } from "./language-provider";

export const ALLERGY_INGREDIENTS = [
  ["fragrance", "น้ำหอม (Fragrance / Parfum)", "Fragrance / Parfum"],
  ["methylisothiazolinone", "Methylisothiazolinone (MIT)", "Methylisothiazolinone (MIT)"],
  ["methylchloroisothiazolinone", "Methylchloroisothiazolinone (CMIT)", "Methylchloroisothiazolinone (CMIT)"],
  ["formaldehyde", "ฟอร์มาลดีไฮด์ / สารปล่อยฟอร์มาลดีไฮด์", "Formaldehyde / formaldehyde releasers"],
  ["latex", "ยางธรรมชาติ (Latex)", "Natural rubber (Latex)"],
  ["nickel", "นิกเกิล (Nickel)", "Nickel"],
  ["other", "สารอื่น / ยังไม่ทราบสาร", "Other / ingredient unknown"],
] as const;

export function AllergyIngredients({ values, onChange, disabled = false }: {
  values: string[];
  onChange: (values: string[]) => void;
  disabled?: boolean;
}) {
  const { language } = useLanguage();
  return <fieldset className="allergy-ingredients" disabled={disabled}>
    <legend>{language === "th" ? "สารที่คุณเคยแพ้ (เลือกได้หลายข้อ)" : "Reported allergens (select all that apply)"}</legend>
    {ALLERGY_INGREDIENTS.map(([value, th, en]) => <label key={value}>
      <input type="checkbox" name="allergy_ingredients" value={value} checked={values.includes(value)}
        onChange={(event) => onChange(event.target.checked ? [...values, value] : values.filter((item) => item !== value))} />
      <span>{language === "th" ? th : en}</span>
    </label>)}
    <p>{language === "th" ? "บันทึกเฉพาะประวัติที่คุณทราบ ระบบยังงดแนะนำสินค้ารายชิ้นเมื่อมีประวัติแพ้" : "Record only your known history. Named products remain withheld when an allergy is reported."}</p>
  </fieldset>;
}
