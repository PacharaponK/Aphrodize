import fs from "node:fs/promises";
import path from "node:path";
import { SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const projectRoot = path.resolve(process.cwd());
const csvPath = path.join(projectRoot, "data", "synthetic", "lifestyle_skin_dryness_synthetic_1000.csv");
const outputDir = path.join(projectRoot, "outputs", "lifestyle-skin-dryness-synthetic-1000");
const xlsxPath = path.join(outputDir, "lifestyle_skin_dryness_synthetic_1000.xlsx");
const previewPath = path.join(outputDir, "eda_preview.png");

await fs.mkdir(path.dirname(csvPath), { recursive: true });
await fs.mkdir(outputDir, { recursive: true });

// Deterministic pseudo-random generator so this synthetic dataset is reproducible.
let seed = 20260925;
function random() {
  seed = (seed * 1664525 + 1013904223) >>> 0;
  return seed / 4294967296;
}

function normal(mean = 0, standardDeviation = 1) {
  const u = Math.max(random(), 1e-12);
  const v = Math.max(random(), 1e-12);
  return mean + Math.sqrt(-2 * Math.log(u)) * Math.cos(2 * Math.PI * v) * standardDeviation;
}

function clamp(value, min, max) {
  return Math.min(Math.max(value, min), max);
}

function integerInRange(min, max) {
  return Math.floor(random() * (max - min + 1)) + min;
}

function pick(items) {
  return items[Math.floor(random() * items.length)];
}

function weightedPick(items) {
  const totalWeight = items.reduce((sum, item) => sum + item.weight, 0);
  let cursor = random() * totalWeight;
  for (const item of items) {
    cursor -= item.weight;
    if (cursor <= 0) return item.value;
  }
  return items.at(-1).value;
}

function isoDate(date) {
  return date.toISOString().slice(0, 10);
}

function average(values) {
  return values.reduce((sum, value) => sum + value, 0) / values.length;
}

function correlation(left, right) {
  const leftMean = average(left);
  const rightMean = average(right);
  let numerator = 0;
  let leftSumSquares = 0;
  let rightSumSquares = 0;
  for (let index = 0; index < left.length; index += 1) {
    const leftDelta = left[index] - leftMean;
    const rightDelta = right[index] - rightMean;
    numerator += leftDelta * rightDelta;
    leftSumSquares += leftDelta ** 2;
    rightSumSquares += rightDelta ** 2;
  }
  return numerator / Math.sqrt(leftSumSquares * rightSumSquares);
}

const outdoorChoices = {
  1: { label: "less_than_1_hour", minMinutes: 0, maxMinutes: 59, drynessEffect: 0.0 },
  2: { label: "1_to_2_hours", minMinutes: 60, maxMinutes: 120, drynessEffect: 0.1 },
  3: { label: "3_to_4_hours", minMinutes: 180, maxMinutes: 240, drynessEffect: 0.3 },
  4: { label: "4_hours_or_more", minMinutes: 241, maxMinutes: 360, drynessEffect: 0.5 },
};

function sampleSleepMinutes() {
  const sleepBand = weightedPick([
    { value: "adequate", weight: 0.47 },
    { value: "moderate", weight: 0.28 },
    { value: "low", weight: 0.25 },
  ]);
  if (sleepBand === "adequate") return integerInRange(420, 540);
  if (sleepBand === "moderate") return integerInRange(360, 419);
  return integerInRange(180, 359);
}

function sampleWaterIntake(sleepMinutes) {
  const lowSleep = sleepMinutes < 360;
  const adequateSleep = sleepMinutes >= 420;
  const group = lowSleep
    ? weightedPick([{ value: "low", weight: 0.58 }, { value: "mid", weight: 0.27 }, { value: "adequate", weight: 0.15 }])
    : adequateSleep
      ? weightedPick([{ value: "low", weight: 0.22 }, { value: "mid", weight: 0.36 }, { value: "adequate", weight: 0.42 }])
      : weightedPick([{ value: "low", weight: 0.38 }, { value: "mid", weight: 0.38 }, { value: "adequate", weight: 0.24 }]);

  if (group === "low") return integerInRange(700, 1499);
  if (group === "mid") return integerInRange(1500, 1999);
  return integerInRange(2000, 3000);
}

function drynessRiskBand(score) {
  if (score <= 3) return "low";
  if (score <= 6) return "moderate";
  return "high";
}

function skinFeeling(score, oiliness) {
  if (score >= 7 && oiliness >= 6) return "oily_dehydrated";
  if (score >= 8) return "very_dry";
  if (score >= 6) return "dry";
  if (score >= 4) return "mildly_dry";
  return "normal";
}

function csvCell(value) {
  const text = String(value ?? "");
  return /[",\n]/.test(text) ? `"${text.replaceAll('"', '""')}"` : text;
}

const headers = [
  "record_id",
  "user_id",
  "local_date",
  "timezone",
  "baseline_skin_type",
  "sleep_duration_hours",
  "sleep_duration_mins",
  "sleep_duration_total_minutes",
  "water_intake_ml",
  "thirst_score_0_10",
  "outdoor_exposure_choice",
  "outdoor_exposure_band",
  "outdoor_minutes_estimate",
  "routine_adherence",
  "skin_dryness_score_0_10",
  "skin_dryness_risk_band",
  "facial_oiliness_score_0_10",
  "skin_feeling_status",
  "data_origin",
];

const records = [];
const startDate = new Date("2026-01-01T00:00:00.000Z");
for (let recordIndex = 0; recordIndex < 1000; recordIndex += 1) {
  const userNumber = (recordIndex % 20) + 1;
  const dayIndex = Math.floor(recordIndex / 20);
  const localDate = new Date(startDate);
  localDate.setUTCDate(startDate.getUTCDate() + dayIndex);

  const sleepMinutes = sampleSleepMinutes();
  const sleepHours = Math.floor(sleepMinutes / 60);
  const sleepRemainderMinutes = sleepMinutes % 60;
  const waterIntake = sampleWaterIntake(sleepMinutes);
  const outdoorChoice = weightedPick([
    { value: 1, weight: 0.40 },
    { value: 2, weight: 0.33 },
    { value: 3, weight: 0.17 },
    { value: 4, weight: 0.10 },
  ]);
  const outdoor = outdoorChoices[outdoorChoice];
  const outdoorMinutes = integerInRange(outdoor.minMinutes, outdoor.maxMinutes);
  const routineAdherence = random() < 0.67 ? "yes" : "no";

  const lowSleep = sleepMinutes < 360;
  const adequateSleep = sleepMinutes >= 420;
  const lowWater = waterIntake < 1500;
  const adequateWater = waterIntake >= 2000;
  const sleepDeficit = clamp((420 - sleepMinutes) / 240, 0, 1);
  const waterDeficit = clamp((2000 - waterIntake) / 1300, 0, 1);
  const routineEffect = routineAdherence === "yes" ? -0.25 : 0;
  let dryness;

  // User-defined calibration bands. These are synthetic design rules, not clinical thresholds.
  if (adequateSleep && adequateWater) {
    dryness = 1 + random() * 2 + outdoor.drynessEffect * 0.25 + routineEffect + normal(0, 0.18);
    dryness = clamp(dryness, 1, 3);
  } else if (adequateSleep && lowWater) {
    dryness = 4 + random() * 2 + outdoor.drynessEffect * 0.35 + routineEffect + normal(0, 0.22);
    dryness = clamp(dryness, 4, 6);
  } else if (lowSleep && lowWater) {
    dryness = 7 + random() * 3 + outdoor.drynessEffect * 0.45 + routineEffect + normal(0, 0.25);
    dryness = clamp(dryness, 7, 10);
  } else {
    dryness = 2.4 + 2.2 * sleepDeficit + 2.3 * waterDeficit + 0.8 * sleepDeficit * waterDeficit + outdoor.drynessEffect + routineEffect + normal(0, 0.45);
    dryness = clamp(dryness, 2, 7);
  }
  dryness = Number(dryness.toFixed(1));

  let thirst = 1.4 + 3.0 * sleepDeficit + 4.2 * waterDeficit + 0.55 * (outdoorChoice - 1) + normal(0, 0.7);
  thirst = Number(clamp(thirst, 0, 10).toFixed(1));

  let oiliness;
  if (adequateSleep && adequateWater && dryness <= 3) {
    oiliness = 2.0 + random() * 1.8 + normal(0, 0.25);
  } else if (lowSleep && lowWater && dryness >= 7) {
    oiliness = 4.0 + 0.52 * dryness + 0.22 * thirst + normal(0, 0.55);
  } else {
    oiliness = 2.4 + 0.35 * dryness + 0.16 * thirst + normal(0, 0.5);
  }
  oiliness = Number(clamp(oiliness, 1, 10).toFixed(1));

  records.push({
    record_id: `SYN-${String(recordIndex + 1).padStart(4, "0")}`,
    user_id: `synthetic_user_${String(userNumber).padStart(2, "0")}`,
    local_date: isoDate(localDate),
    timezone: "Asia/Bangkok",
    baseline_skin_type: "oily",
    sleep_duration_hours: sleepHours,
    sleep_duration_mins: sleepRemainderMinutes,
    sleep_duration_total_minutes: sleepMinutes,
    water_intake_ml: waterIntake,
    thirst_score_0_10: thirst,
    outdoor_exposure_choice: outdoorChoice,
    outdoor_exposure_band: outdoor.label,
    outdoor_minutes_estimate: outdoorMinutes,
    routine_adherence: routineAdherence,
    skin_dryness_score_0_10: dryness,
    skin_dryness_risk_band: drynessRiskBand(dryness),
    facial_oiliness_score_0_10: oiliness,
    skin_feeling_status: skinFeeling(dryness, oiliness),
    data_origin: "synthetic_rule_based_v1",
  });
}

const csvText = [headers, ...records.map((record) => headers.map((header) => record[header]))]
  .map((row) => row.map(csvCell).join(","))
  .join("\n");
await fs.writeFile(csvPath, `${csvText}\n`, "utf8");

function summarize(groupRecords) {
  const drynessValues = groupRecords.map((record) => record.skin_dryness_score_0_10);
  return {
    count: groupRecords.length,
    mean: Number(average(drynessValues).toFixed(2)),
    min: Number(Math.min(...drynessValues).toFixed(1)),
    max: Number(Math.max(...drynessValues).toFixed(1)),
  };
}

const groups = [
  { label: "Adequate sleep + adequate water", predicate: (record) => record.sleep_duration_total_minutes >= 420 && record.water_intake_ml >= 2000, expected: "1–3" },
  { label: "Adequate sleep + low water", predicate: (record) => record.sleep_duration_total_minutes >= 420 && record.water_intake_ml < 1500, expected: "4–6" },
  { label: "Low sleep + adequate water", predicate: (record) => record.sleep_duration_total_minutes < 360 && record.water_intake_ml >= 2000, expected: "2–7" },
  { label: "Low sleep + low water", predicate: (record) => record.sleep_duration_total_minutes < 360 && record.water_intake_ml < 1500, expected: "7–10" },
];

const groupSummary = groups.map((group) => {
  const matchingRecords = records.filter(group.predicate);
  const summary = summarize(matchingRecords);
  return [group.label, summary.count, summary.mean, summary.min, summary.max, group.expected];
});

const outdoorSummary = [1, 2, 3, 4].map((choice) => {
  const matchingRecords = records.filter((record) => record.outdoor_exposure_choice === choice);
  return [choice, outdoorChoices[choice].label, matchingRecords.length, Number(average(matchingRecords.map((record) => record.skin_dryness_score_0_10)).toFixed(2)), Number(average(matchingRecords.map((record) => record.thirst_score_0_10)).toFixed(2))];
});

const metricValues = {
  sleep_duration_total_minutes: records.map((record) => record.sleep_duration_total_minutes),
  water_intake_ml: records.map((record) => record.water_intake_ml),
  thirst_score_0_10: records.map((record) => record.thirst_score_0_10),
  skin_dryness_score_0_10: records.map((record) => record.skin_dryness_score_0_10),
  facial_oiliness_score_0_10: records.map((record) => record.facial_oiliness_score_0_10),
};
const correlationMetrics = Object.keys(metricValues);
const correlationRows = correlationMetrics.map((rowMetric) => [
  rowMetric,
  ...correlationMetrics.map((columnMetric) => Number(correlation(metricValues[rowMetric], metricValues[columnMetric]).toFixed(2))),
]);

const workbook = Workbook.create();
const summarySheet = workbook.worksheets.add("EDA Summary");
const dataSheet = workbook.worksheets.add("Synthetic Data");
const dictionarySheet = workbook.worksheets.add("Data Dictionary");
const sourcesSheet = workbook.worksheets.add("Sources and Rules");
for (const sheet of [summarySheet, dataSheet, dictionarySheet, sourcesSheet]) {
  sheet.showGridLines = false;
}

const titleStyle = { font: { name: "Arial", size: 14, bold: true, color: "#1F2937" } };
const headerStyle = { fill: "#0F766E", font: { name: "Arial", size: 10, bold: true, color: "#FFFFFF" }, horizontalAlignment: "center", verticalAlignment: "center", wrapText: true };
const bodyFont = { name: "Arial", size: 10, color: "#1F2937" };

summarySheet.getRange("A2").values = [["Synthetic lifestyle and skin dryness dataset: EDA"]];
summarySheet.getRange("A2").format = titleStyle;
summarySheet.getRange("A4:B7").values = [
  ["Metric", "Value"],
  ["Records", records.length],
  ["Mean skin dryness score (0–10)", Number(average(records.map((record) => record.skin_dryness_score_0_10)).toFixed(2))],
  ["High dryness records (score ≥ 7)", records.filter((record) => record.skin_dryness_score_0_10 >= 7).length],
];
summarySheet.getRange("A4:B4").format = headerStyle;
summarySheet.getRange("A4:B7").format.font = bodyFont;
summarySheet.getRange("A4:B7").format.borders = { preset: "outside", style: "thin", color: "#D1D5DB" };
summarySheet.getRange("A10:F10").values = [["Sleep and water condition", "Records", "Mean dryness", "Min dryness", "Max dryness", "Synthetic expected range"]];
summarySheet.getRange("A10:F10").format = headerStyle;
summarySheet.getRange("A11:F14").values = groupSummary;
summarySheet.getRange("A10:F14").format.font = bodyFont;
summarySheet.getRange("A10:F14").format.borders = { preset: "outside", style: "thin", color: "#D1D5DB" };
summarySheet.getRange("A17:E17").values = [["Outdoor choice", "Outdoor band", "Records", "Mean dryness", "Mean thirst"]];
summarySheet.getRange("A17:E17").format = headerStyle;
summarySheet.getRange("A18:E21").values = outdoorSummary;
summarySheet.getRange("A17:E21").format.font = bodyFont;
summarySheet.getRange("A17:E21").format.borders = { preset: "outside", style: "thin", color: "#D1D5DB" };
summarySheet.getRange("A24:F24").values = [["Correlation", ...correlationMetrics]];
summarySheet.getRange("A24:F24").format = headerStyle;
summarySheet.getRange("A25:F29").values = correlationRows;
summarySheet.getRange("A24:F29").format.font = bodyFont;
summarySheet.getRange("A24:F29").format.borders = { preset: "outside", style: "thin", color: "#D1D5DB" };
summarySheet.getRange("C11:E14").format.numberFormat = "0.00";
summarySheet.getRange("D18:E21").format.numberFormat = "0.00";
summarySheet.getRange("B25:F29").format.numberFormat = "0.00";
summarySheet.getRange("A32").values = [["Interpretation: the designed rules should show 1–3 dryness when sleep and water are adequate, 4–6 when water is low despite adequate sleep, and 7–10 when both are low. This is synthetic data for prototyping, not a clinical prediction model."]];
summarySheet.getRange("A32:F32").merge();
summarySheet.getRange("A32").format = { font: { name: "Arial", size: 10, italic: true, color: "#4B5563" }, wrapText: true, verticalAlignment: "center" };
summarySheet.getRange("A32:F32").format.rowHeight = 42;

const conditionChart = summarySheet.charts.add("bar", [summarySheet.getRange("A10:A14"), summarySheet.getRange("C10:C14")]);
conditionChart.title = "Mean dryness by sleep and water condition";
conditionChart.hasLegend = false;
conditionChart.setPosition("H4", "P17");
conditionChart.series.items[0].fill = "#D97706";
const outdoorChart = summarySheet.charts.add("bar", [summarySheet.getRange("B17:B21"), summarySheet.getRange("D17:D21")]);
outdoorChart.title = "Mean dryness by outdoor band";
outdoorChart.hasLegend = false;
outdoorChart.setPosition("H19", "P32");
outdoorChart.series.items[0].fill = "#2563EB";

dataSheet.getRangeByIndexes(0, 0, records.length + 1, headers.length).values = [
  headers,
  ...records.map((record) => headers.map((header) => record[header])),
];
dataSheet.getRangeByIndexes(0, 0, 1, headers.length).format = headerStyle;
dataSheet.getRangeByIndexes(1, 0, records.length, headers.length).format.font = bodyFont;
dataSheet.getRange(`C2:C${records.length + 1}`).format.numberFormat = "yyyy-mm-dd";
dataSheet.getRange(`J2:J${records.length + 1}`).format.numberFormat = "0.0";
dataSheet.getRange(`O2:O${records.length + 1}`).format.numberFormat = "0.0";
dataSheet.getRange(`Q2:Q${records.length + 1}`).format.numberFormat = "0.0";
dataSheet.tables.add(`A1:S${records.length + 1}`, true, "SyntheticLifestyleData");
dataSheet.freezePanes.freezeRows(1);
dataSheet.getRange(`O2:O${records.length + 1}`).conditionalFormats.add("colorScale", { colors: ["#DCFCE7", "#FDE68A", "#FCA5A5"], thresholds: ["min", { type: "percentile", value: 50 }, "max"] });

const dictionaryRows = [
  ["Field", "Type / unit", "Meaning"],
  ["record_id", "text", "Synthetic record identifier."],
  ["user_id", "text", "20 synthetic users; 50 days each."],
  ["local_date", "date", "Daily observation date."],
  ["timezone", "text", "Asia/Bangkok in this prototype."],
  ["baseline_skin_type", "category", "All records use oily to model the requested persona."],
  ["sleep_duration_hours", "integer hours", "Whole-hour part of the sleep duration."],
  ["sleep_duration_mins", "integer minutes", "Remaining-minute part; combine with hours for calculations."],
  ["sleep_duration_total_minutes", "minutes", "Derived: hours × 60 + minutes."],
  ["water_intake_ml", "mL", "Self-reported drinking water amount; synthetic."],
  ["thirst_score_0_10", "0–10", "Synthetic self-reported desire for water, increased by water shortfall, short sleep and outdoor band."],
  ["outdoor_exposure_choice", "ordinal 1–4", "1: <1 hour; 2: 1–2 hours; 3: 3–4 hours; 4: ≥4 hours."],
  ["outdoor_exposure_band", "category", "Readable label for the four user choices."],
  ["outdoor_minutes_estimate", "minutes", "Representative minute value inside the selected choice. No values are generated for 121–179 minutes because the supplied choices omit 2–3 hours."],
  ["routine_adherence", "yes/no", "Synthetic skin-care routine completion."],
  ["skin_dryness_score_0_10", "0–10", "Synthetic model target; not a clinical diagnostic score."],
  ["skin_dryness_risk_band", "category", "low: 0–3; moderate: 4–6; high: 7–10 for prototype display."],
  ["facial_oiliness_score_0_10", "0–10", "Synthetic self-reported oiliness for an oily-skin baseline."],
  ["skin_feeling_status", "category", "normal, mildly_dry, dry, very_dry, or oily_dehydrated."],
  ["data_origin", "text", "Always synthetic_rule_based_v1 in this file."],
];
dictionarySheet.getRangeByIndexes(0, 0, dictionaryRows.length, 3).values = dictionaryRows;
dictionarySheet.getRange("A1:C1").format = headerStyle;
dictionarySheet.getRange(`A2:C${dictionaryRows.length}`).format.font = bodyFont;
dictionarySheet.getRange(`A1:C${dictionaryRows.length}`).format.borders = { preset: "outside", style: "thin", color: "#D1D5DB" };
dictionarySheet.getRange(`C1:C${dictionaryRows.length}`).format.wrapText = true;
dictionarySheet.freezePanes.freezeRows(1);

const sourceRows = [
  ["Source or rule", "How it is used", "URL / identifier"],
  ["User-provided scoring guide", "Primary synthetic calibration: adequate sleep + adequate water → dryness 1–3; adequate sleep + low water → 4–6; low sleep + low water → 7–10.", "Conversation requirement"],
  ["Akdeniz et al. (2018)", "Evidence about increased fluid intake and skin hydration is limited/weak overall; used only as directional context, not to set clinical thresholds.", "https://pubmed.ncbi.nlm.nih.gov/29392767/"],
  ["Oyetakin-White et al. (2015)", "Poor sleep quality was associated with diminished skin-barrier recovery in a small observational study; used as directional context for the sleep feature.", "https://pubmed.ncbi.nlm.nih.gov/25266053/"],
  ["Permatasari et al. (2013)", "UV exposure can affect epidermal barrier function; outdoor choice is retained as a weak proxy only, not a measure of UV dose or sunscreen use.", "https://pubmed.ncbi.nlm.nih.gov/24137176/"],
  ["EFSA Dietary Reference Values", "Provides broad total-water context. It includes water from food and beverages, so it is not used as a personal drinking-water prescription or a model label.", "https://www.efsa.europa.eu/sites/default/files/2017_09_DRVs_summary_report.pdf"],
  ["Important limitation", "This dataset is simulated for prototype/EDA work. It must not be presented as clinical evidence, used for medical decisions, or described as Zepp/Amazfit output.", "Synthetic dataset"],
];
sourcesSheet.getRangeByIndexes(0, 0, sourceRows.length, 3).values = sourceRows;
sourcesSheet.getRange("A1:C1").format = headerStyle;
sourcesSheet.getRange(`A2:C${sourceRows.length}`).format.font = bodyFont;
sourcesSheet.getRange(`A1:C${sourceRows.length}`).format.borders = { preset: "outside", style: "thin", color: "#D1D5DB" };
sourcesSheet.getRange(`A1:C${sourceRows.length}`).format.wrapText = true;
sourcesSheet.getRange(`A2:C${sourceRows.length}`).format.verticalAlignment = "top";

for (const sheet of [summarySheet, dataSheet, dictionarySheet, sourcesSheet]) {
  const used = sheet.getUsedRange();
  used.format.autofitColumns();
  used.format.autofitRows();
}
summarySheet.getRange("A1:P35").format.font = bodyFont;
summarySheet.getRange("A2").format = titleStyle;
summarySheet.getRange("A:A").format.columnWidth = 34;
summarySheet.getRange("B:F").format.columnWidth = 16;
summarySheet.getRange("H:P").format.columnWidth = 12;
dataSheet.getRange("A:A").format.columnWidth = 14;
dataSheet.getRange("B:B").format.columnWidth = 18;
dataSheet.getRange("C:C").format.columnWidth = 13;
dataSheet.getRange("D:D").format.columnWidth = 14;
dataSheet.getRange("E:E").format.columnWidth = 18;
dataSheet.getRange("L:L").format.columnWidth = 22;
dataSheet.getRange("R:R").format.columnWidth = 18;
dictionarySheet.getRange("A:A").format.columnWidth = 32;
dictionarySheet.getRange("B:B").format.columnWidth = 18;
dictionarySheet.getRange("C:C").format.columnWidth = 95;
sourcesSheet.getRange("A:A").format.columnWidth = 30;
sourcesSheet.getRange("B:B").format.columnWidth = 90;
sourcesSheet.getRange("C:C").format.columnWidth = 70;

workbook.recalculate();
const preview = await workbook.render({ sheetName: "EDA Summary", range: "A1:P33", scale: 1.2, format: "png" });
await fs.writeFile(previewPath, new Uint8Array(await preview.arrayBuffer()));
const xlsx = await SpreadsheetFile.exportXlsx(workbook);
await xlsx.save(xlsxPath);

console.log(JSON.stringify({ csvPath, xlsxPath, previewPath, recordCount: records.length, groupSummary, outdoorSummary }, null, 2));
