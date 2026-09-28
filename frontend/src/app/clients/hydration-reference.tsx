import type { HydrationCalculation } from "@/lib/daily-health-types";

export default function HydrationReference({ hydration }: { hydration?: HydrationCalculation }) {
  if (!hydration) return null;
  if (hydration.range_status === "missing_weight") {
    return <p>เพิ่มน้ำหนักในโปรไฟล์เพื่อคำนวณ Thirst score</p>;
  }
  if (hydration.range_status === "unsupported_age") {
    return <p>สูตรน้ำตามน้ำหนักนี้อ้างอิงผู้ใหญ่ จึงยังไม่คำนวณสำหรับช่วงวัยที่เลือก</p>;
  }
  return (
    <details className="score-method-details">
      <summary>Thirst score · สูตรน้ำตามน้ำหนัก</summary>
      <div className="score-method-content">
        <p>ช่วงอ้างอิง {hydration.reference_lower_ml?.toLocaleString("th-TH")}–{hydration.reference_upper_ml?.toLocaleString("th-TH")} มล./วัน (น้ำหนัก × 30–35)</p>
        <code>score = round(10 × max(0, 1 − น้ำที่บันทึก ÷ (น้ำหนัก × 30)), 1)</code>
        <p>คะแนนสูงหมายถึงยอดน้ำที่บันทึกยังต่ำกว่าฐานอ้างอิงมาก; เป็นคะแนนของแอป ไม่ใช่การวัดความกระหายหรือภาวะขาดน้ำ ช่วงนี้อ้างอิงของเหลวรวมจากเครื่องดื่มและอาหารสำหรับผู้ใหญ่ และค่า ×35 ไม่ใช่เพดานความปลอดภัย</p>
        <a href={hydration.reference_url} target="_blank" rel="noreferrer">NICE CG32: ช่วงประมาณของเหลวรวม 30–35 ml/kg</a>
      </div>
    </details>
  );
}
