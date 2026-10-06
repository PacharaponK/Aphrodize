type EvidenceKind = "recorded" | "calculated" | "estimate" | "forecast";

const labels: Record<EvidenceKind, { th: string; en: string }> = {
  recorded: { th: "จากบันทึก", en: "Recorded" },
  calculated: { th: "คำนวณจากบันทึก", en: "Calculated" },
  estimate: { th: "ค่าประมาณจากโมเดล", en: "Model estimate" },
  forecast: { th: "ค่าคาดการณ์", en: "Forecast" },
};

export function EvidenceLabel({ kind, language }: { kind: EvidenceKind; language: string }) {
  return <span className="evidence-label" data-evidence={kind}>{labels[kind][language === "th" ? "th" : "en"]}</span>;
}
