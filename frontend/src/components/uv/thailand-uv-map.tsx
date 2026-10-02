"use client";

import { useId, useState } from "react";
import shapes from "../../../public/assets/uv-map-provinces.json";
import "./uv-map.css";

export type UvProvince = {
  id: string;
  name: string;
  name_en: string;
  latitude: number;
  longitude: number;
  source: "local_model" | "open_meteo";
  source_url: string;
  aggregation: "solar_noon" | "daily_maximum";
  date: string;
  uv_index: number | null;
  level: string | null;
  status: "available" | "stale" | "unavailable";
  generated_at: string | null;
  data_date: string | null;
  model_version: string | null;
  value_kind: string;
};

export const UV_LEVELS = [
  { id: "low", name: "ต่ำ", range: "0–<3", color: "#65a86b" },
  { id: "moderate", name: "ปานกลาง", range: "3–<6", color: "#f0cc57" },
  { id: "high", name: "สูง", range: "6–<8", color: "#ee9347" },
  { id: "very_high", name: "สูงมาก", range: "8–<11", color: "#d95861" },
  { id: "extreme", name: "สูงสุดขีด", range: "11+", color: "#9762ac" },
] as const;

export const provinceOptions = [...shapes].sort((a, b) => a.name.localeCompare(b.name, "th"));

export function ThailandUvMap({
  provinces, selectedProvinceId, onSelectProvince, provinceIds,
}: {
  provinces: UvProvince[];
  selectedProvinceId: string;
  onSelectProvince: (provinceId: string) => void;
  provinceIds?: string[];
}) {
  const descriptionId = useId();
  const [previewId, setPreviewId] = useState<string | null>(null);
  const records = new Map(provinces.map((province) => [province.id, province]));
  const visibleShapes = provinceIds ? shapes.filter((shape) => provinceIds.includes(shape.id)) : shapes;
  const preview = shapes.find((shape) => shape.id === (previewId ?? selectedProvinceId));
  const previewRecord = preview ? records.get(preview.id) : null;
  function label(id: string, name: string) {
    const record = records.get(id);
    return `${name}: ${record?.uv_index != null ? `UV ${record.uv_index.toFixed(1)}` : "ไม่มีข้อมูลที่พร้อมใช้"}${record?.source === "local_model" ? " · โมเดลของเรา" : ""}`;
  }
  return <div className="thailand-uv-map">
    <p className="uv-map-preview" aria-hidden="true">
      {preview ? label(preview.id, preview.name) : "เลือกจังหวัดบนแผนที่เพื่อดูรายละเอียด"}
      {previewRecord?.level && <span>{UV_LEVELS.find((level) => level.id === previewRecord.level)?.name}</span>}
    </p>
    <svg viewBox="0 0 720 1240" role="group" aria-label={`แผนที่ UV ประเทศไทย ${visibleShapes.length} พื้นที่`} aria-describedby={descriptionId}>
      {provinceIds && <g className="uv-map-context" aria-hidden="true">
        {shapes.map((shape) => <path key={shape.id} d={shape.path} fillRule="evenodd" />)}
      </g>}
      {visibleShapes.map((shape) => {
        const record = records.get(shape.id);
        const available = record?.status === "available" && record.uv_index != null;
        const fill = available ? UV_LEVELS.find((level) => level.id === record.level)?.color : undefined;
        return <path key={shape.id} d={shape.path} fill={fill ?? "var(--uv-map-missing)"} fillRule="evenodd"
          role="button" tabIndex={0} aria-label={label(shape.id, shape.name)}
          aria-pressed={selectedProvinceId === shape.id} data-model={record?.source === "local_model"}
          onClick={() => onSelectProvince(shape.id)}
          onKeyDown={(event) => {
            if (event.key === "Enter" || event.key === " ") { event.preventDefault(); onSelectProvince(shape.id); }
          }}
          onMouseEnter={() => setPreviewId(shape.id)} onMouseLeave={() => setPreviewId(null)}
          onFocus={() => setPreviewId(shape.id)} onBlur={() => setPreviewId(null)}>
          <title>{label(shape.id, shape.name)}</title>
        </path>;
      })}
      {visibleShapes.filter((p) => records.get(p.id)?.source === "local_model").map((p) => <circle key={p.id}
        cx={(p.longitude - 97) * 80} cy={(21 - p.latitude) * 80} r="6" className="uv-model-point" aria-hidden="true" />)}
    </svg>
    <p id={descriptionId} className="uv-map-caption">คลิกหรือแตะจังหวัด · ใช้ Enter หรือ Space เพื่อเลือก{provinceIds && " · แสดงเฉพาะพื้นที่ที่โมเดลรองรับ"}</p>
  </div>;
}
