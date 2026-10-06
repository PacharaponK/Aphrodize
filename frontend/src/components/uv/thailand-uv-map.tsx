"use client";

import { useId, useRef, useState, type CSSProperties, type PointerEvent } from "react";
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
  { id: "low", name: "ต่ำ", name_en: "Low", range: "0–<3", color: "#65a86b" },
  { id: "moderate", name: "ปานกลาง", name_en: "Moderate", range: "3–<6", color: "#f0cc57" },
  { id: "high", name: "สูง", name_en: "High", range: "6–<8", color: "#ee9347" },
  { id: "very_high", name: "สูงมาก", name_en: "Very high", range: "8–<11", color: "#d95861" },
  { id: "extreme", name: "สูงสุดขีด", name_en: "Extreme", range: "11+", color: "#9762ac" },
] as const;

export const provinceOptions = [...shapes].sort((a, b) => a.name.localeCompare(b.name, "th"));

export function boundedMapOrientation(rotation: number, tilt: number) {
  return { rotation: Math.max(-30, Math.min(30, rotation)), tilt: Math.max(-12, Math.min(18, tilt)) };
}

export function ThailandUvMap({
  provinces, selectedProvinceId, onSelectProvince, provinceIds, missionView = false, language = "th",
}: {
  provinces: UvProvince[];
  selectedProvinceId: string;
  onSelectProvince: (provinceId: string) => void;
  provinceIds?: string[];
  missionView?: boolean;
  language?: "th" | "en";
}) {
  const t = (th: string, en: string) => language === "en" ? en : th;
  const provinceName = (shape: typeof shapes[number]) => language === "en" ? shape.name_en : shape.name;
  const descriptionId = useId();
  const [previewId, setPreviewId] = useState<string | null>(null);
  const [flat, setFlat] = useState(false);
  const [zoom, setZoom] = useState(1);
  const stageRef = useRef<HTMLDivElement>(null);
  const orientation = useRef({ rotation: 0, tilt: 0 });
  const drag = useRef<{ id: number; x: number; y: number; rotation: number; tilt: number } | null>(null);
  function orient(rotation: number, tilt: number) {
    orientation.current = boundedMapOrientation(rotation, tilt);
    const stage = stageRef.current;
    if (!stage) return;
    stage.style.setProperty("--uv-rotation-offset", `${orientation.current.rotation}deg`);
    stage.style.setProperty("--uv-tilt-offset", `${orientation.current.tilt}deg`);
    stage.dataset.oriented = "true";
  }
  function endDrag(event: PointerEvent<HTMLDivElement>) {
    if (drag.current?.id !== event.pointerId) return;
    drag.current = null;
    event.currentTarget.dataset.dragging = "false";
    if (event.currentTarget.hasPointerCapture(event.pointerId)) event.currentTarget.releasePointerCapture(event.pointerId);
  }
  const records = new Map(provinces.map((province) => [province.id, province]));
  const visibleShapes = provinceIds ? shapes.filter((shape) => provinceIds.includes(shape.id)) : shapes;
  const preview = shapes.find((shape) => shape.id === (previewId ?? selectedProvinceId));
  const previewRecord = preview ? records.get(preview.id) : null;
  function label(id: string, name: string) {
    const record = records.get(id);
    return `${name}: ${record?.status === "available" && record.uv_index != null ? `UV ${record.uv_index.toFixed(1)}` : t("ไม่มีข้อมูลที่พร้อมใช้", "No available data")}${record?.source === "local_model" ? t(" · โมเดลของเรา", " · Our model") : ""}`;
  }
  const focus = shapes.find((shape) => shape.id === selectedProvinceId);
  const width = 720 / zoom;
  const height = 1240 / zoom;
  const centerX = focus ? (focus.longitude - 97) * 80 : 360;
  const centerY = focus ? (21 - focus.latitude) * 80 : 620;
  const viewBox = zoom === 1 ? "0 0 720 1240" : `${Math.max(0, Math.min(720 - width, centerX - width / 2))} ${Math.max(0, Math.min(1240 - height, centerY - height / 2))} ${width} ${height}`;
  return <div className={`thailand-uv-map${missionView ? " uv-mission-map" : ""}`} data-flat={flat}>
    {missionView && <details className="uv-map-view-options">
      <summary>{t("ปรับมุมมองแผนที่", "View controls")}</summary>
      <div className="uv-map-view-controls" role="group" aria-label={t("มุมมองแผนที่", "Map view")}>
        <button type="button" aria-pressed={flat} onClick={() => setFlat(!flat)}>{flat ? t("มุมมองแบน", "Flat view") : t("มุมมองเอียง 2.5D", "Tilted 2.5D view")}</button>
        <button type="button" aria-label={t("ซูมเข้าจังหวัดที่เลือก", "Zoom into selected province")} disabled={zoom >= 2} onClick={() => setZoom(Math.min(2, zoom + .5))}>{t("ซูมเข้า", "Zoom in")}</button>
        <button type="button" disabled={zoom === 1} onClick={() => setZoom(1)}>{t("ดูทั้งประเทศ", "Whole country")}</button>
        <button type="button" disabled={flat} onClick={() => orient(orientation.current.rotation - 8, orientation.current.tilt)}>{t("หมุนซ้าย", "Rotate left")}</button>
        <button type="button" disabled={flat} onClick={() => orient(orientation.current.rotation + 8, orientation.current.tilt)}>{t("หมุนขวา", "Rotate right")}</button>
        <button type="button" disabled={flat} onClick={() => orient(orientation.current.rotation, orientation.current.tilt + 6)}>{t("เพิ่มความเอียง", "Increase tilt")}</button>
        <button type="button" disabled={flat} onClick={() => orient(orientation.current.rotation, orientation.current.tilt - 6)}>{t("ลดความเอียง", "Decrease tilt")}</button>
        <button type="button" onClick={() => { orient(0, 0); if (stageRef.current) stageRef.current.dataset.oriented = "false"; setZoom(1); setFlat(false); }}>{t("รีเซ็ตมุมมอง", "Reset view")}</button>
      </div>
      <p className="uv-map-caption">{t("ความสูงเป็นเอฟเฟกต์มุมมอง ไม่ใช่ภูมิประเทศหรือระดับ UV · ซูมเข้าที่จังหวัดที่เลือก", "Depth is a view effect, not terrain or UV magnitude. Zoom centers on the selected province.")}</p>
      <p className="uv-map-caption">{t("กดเมาส์ขวาค้างแล้วลากเพื่อหมุนหรือปรับความเอียง · มือถือและคีย์บอร์ดใช้ปุ่มมุมมอง · รีเซ็ตมุมมองคืนมุมมองและซูมเริ่มต้น", "Hold the right mouse button and drag to rotate or tilt. Use the view buttons on mobile or with a keyboard. Reset restores the default angle and zoom.")}</p>
    </details>}
    <p className="uv-map-preview" aria-hidden="true">
      {preview ? label(preview.id, provinceName(preview)) : t("เลือกจังหวัดบนแผนที่เพื่อดูรายละเอียด", "Select a province for details")}
      {previewRecord?.status === "available" && previewRecord.level && <span>{UV_LEVELS.find((level) => level.id === previewRecord.level)?.[language === "en" ? "name_en" : "name"]}</span>}
    </p>
    <div className="uv-map-stage" ref={stageRef}
      style={{ "--uv-rotation-offset": "0deg", "--uv-tilt-offset": "0deg" } as CSSProperties}
      onContextMenu={(event) => { if (missionView) event.preventDefault(); }}
      onPointerDown={(event) => {
        if (!missionView || flat || event.pointerType !== "mouse" || event.button !== 2) return;
        event.preventDefault();
        drag.current = { id: event.pointerId, x: event.clientX, y: event.clientY, ...orientation.current };
        event.currentTarget.dataset.dragging = "true";
        event.currentTarget.setPointerCapture(event.pointerId);
      }}
      onPointerMove={(event) => {
        const start = drag.current;
        if (!start || start.id !== event.pointerId) return;
        if (!(event.buttons & 2) || flat) { endDrag(event); return; }
        orient(start.rotation + (event.clientX - start.x) * .12, start.tilt - (event.clientY - start.y) * .1);
      }}
      onPointerUp={endDrag} onPointerCancel={endDrag}
      onLostPointerCapture={() => { drag.current = null; if (stageRef.current) stageRef.current.dataset.dragging = "false"; }}>
    <svg viewBox={missionView ? viewBox : "0 0 720 1240"} role="group" aria-label={t(`แผนที่ UV ประเทศไทย ${visibleShapes.length} พื้นที่`, `Thailand UV map, ${visibleShapes.length} areas`)} aria-describedby={descriptionId}>
      {missionView && <g className="uv-map-depth" aria-hidden="true" transform="translate(0 14)">
        {shapes.map((shape) => <path key={shape.id} d={shape.path} fillRule="evenodd" />)}
      </g>}
      {provinceIds && <g className="uv-map-context" aria-hidden="true">
        {shapes.map((shape) => <path key={shape.id} d={shape.path} fillRule="evenodd" />)}
      </g>}
      {visibleShapes.map((shape) => {
        const record = records.get(shape.id);
        const available = record?.status === "available" && record.uv_index != null;
        const fill = available ? UV_LEVELS.find((level) => level.id === record.level)?.color : undefined;
        return <path key={shape.id} d={shape.path} fill={fill ?? "var(--uv-map-missing)"} fillRule="evenodd"
          role="button" tabIndex={0} aria-label={label(shape.id, provinceName(shape))}
          aria-pressed={selectedProvinceId === shape.id} data-model={record?.source === "local_model"}
          onClick={() => onSelectProvince(shape.id)}
          onKeyDown={(event) => {
            if (event.key === "Enter" || event.key === " ") { event.preventDefault(); onSelectProvince(shape.id); }
          }}
          onMouseEnter={() => setPreviewId(shape.id)} onMouseLeave={() => setPreviewId(null)}
          onFocus={() => setPreviewId(shape.id)} onBlur={() => setPreviewId(null)}>
          <title>{label(shape.id, provinceName(shape))}</title>
        </path>;
      })}
      {visibleShapes.filter((p) => records.get(p.id)?.source === "local_model").map((p) => <circle key={p.id}
        cx={(p.longitude - 97) * 80} cy={(21 - p.latitude) * 80} r="6" className="uv-model-point" aria-hidden="true" />)}
    </svg>
    </div>
    <p id={descriptionId} className="uv-map-caption">{t("คลิกหรือแตะจังหวัด · ใช้ Enter หรือ Space เพื่อเลือก", "Click or tap a province, or select with Enter or Space.")}{provinceIds && t(" · แสดงเฉพาะพื้นที่ที่โมเดลรองรับ", " Only model-supported areas are shown.")}{missionView && t(" · ปุ่มหมุนและซูมอยู่ในปรับมุมมองแผนที่", " Rotation and zoom are in View controls.")}</p>
  </div>;
}
