import fs from "node:fs/promises";
import path from "node:path";
import { SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const root = path.resolve(process.cwd());
const dataPath = path.join(root, "data", "synthetic", "lifestyle_skin_dryness_timeseries_aug01_sep30_1220.csv");
const forecastPath = path.join(root, "data", "synthetic", "user001_arx_forecast_2026-09-26_to_2026-09-30.csv");
const outputDir = path.join(root, "outputs", "lifestyle-timeseries-aug01-sep30");
const workbookPath = path.join(outputDir, "lifestyle_timeseries_aug01_sep30_1220.xlsx");
const previewPath = path.join(outputDir, "forecast_eda_preview.png");
await fs.mkdir(path.dirname(dataPath), { recursive: true });
await fs.mkdir(outputDir, { recursive: true });

let seed = 20260926;
const random = () => ((seed = (seed * 1664525 + 1013904223) >>> 0) / 4294967296);
const clamp = (value, min, max) => Math.min(Math.max(value, min), max);
const randomInt = (min, max) => Math.floor(random() * (max - min + 1)) + min;
const normal = (mean = 0, sd = 1) => {
  const u = Math.max(random(), 1e-12);
  const v = Math.max(random(), 1e-12);
  return mean + Math.sqrt(-2 * Math.log(u)) * Math.cos(2 * Math.PI * v) * sd;
};
const mean = (items) => items.reduce((sum, item) => sum + item, 0) / items.length;
const isoDate = (date) => date.toISOString().slice(0, 10);
const dateAfter = (date, days) => {
  const next = new Date(date);
  next.setUTCDate(next.getUTCDate() + days);
  return next;
};
const csvCell = (value) => {
  const text = value ?? "";
  return /[",\n]/.test(String(text)) ? `"${String(text).replaceAll('"', '""')}"` : String(text);
};

const outdoorConfig = {
  1: { label: "less_than_1_hour", min: 0, max: 59, effect: 0.0 },
  2: { label: "1_to_2_hours", min: 60, max: 120, effect: 0.1 },
  3: { label: "3_to_4_hours", min: 180, max: 240, effect: 0.3 },
  4: { label: "4_hours_or_more", min: 241, max: 360, effect: 0.5 },
};

const headers = [
  "record_id", "user_id", "local_date", "timezone", "baseline_skin_type", "row_type", "data_origin",
  "sleep_record_status", "sleep_duration_hours", "sleep_duration_mins", "sleep_duration_total_minutes",
  "water_intake_ml", "thirst_score_0_10", "outdoor_exposure_choice", "outdoor_exposure_band",
  "outdoor_minutes_estimate", "routine_adherence", "skin_dryness_score_0_10", "skin_dryness_risk_band",
  "facial_oiliness_score_0_10", "skin_feeling_status", "forecast_model",
];

function drynessBand(score) {
  return score <= 3 ? "low" : score <= 6 ? "moderate" : "high";
}

function feeling(score, oiliness) {
  if (score >= 7 && oiliness >= 6) return "oily_dehydrated";
  if (score >= 8) return "very_dry";
  if (score >= 6) return "dry";
  if (score >= 4) return "mildly_dry";
  return "normal";
}

function thirstScore(sleepMinutes, waterMl, outdoorChoice) {
  const sleepDeficit = clamp((420 - sleepMinutes) / 240, 0, 1);
  const waterDeficit = clamp((2000 - waterMl) / 1300, 0, 1);
  return Number(clamp(1.4 + 3 * sleepDeficit + 4.2 * waterDeficit + 0.55 * (outdoorChoice - 1) + normal(0, 0.7), 0, 10).toFixed(1));
}

function simulatedDryness(sleepMinutes, waterMl, outdoorChoice, routine) {
  const lowSleep = sleepMinutes < 360;
  const goodSleep = sleepMinutes >= 420;
  const lowWater = waterMl < 1500;
  const goodWater = waterMl >= 2000;
  const outdoorEffect = outdoorConfig[outdoorChoice].effect;
  const routineEffect = routine === "yes" ? -0.25 : 0;
  let value;
  if (goodSleep && goodWater) value = clamp(1 + random() * 2 + outdoorEffect * 0.25 + routineEffect + normal(0, 0.18), 1, 3);
  else if (goodSleep && lowWater) value = clamp(4 + random() * 2 + outdoorEffect * 0.35 + routineEffect + normal(0, 0.22), 4, 6);
  else if (lowSleep && lowWater) value = clamp(7 + random() * 3 + outdoorEffect * 0.45 + routineEffect + normal(0, 0.25), 7, 10);
  else {
    const sleepDeficit = clamp((420 - sleepMinutes) / 240, 0, 1);
    const waterDeficit = clamp((2000 - waterMl) / 1300, 0, 1);
    value = clamp(2.4 + 2.2 * sleepDeficit + 2.3 * waterDeficit + 0.8 * sleepDeficit * waterDeficit + outdoorEffect + routineEffect + normal(0, 0.45), 2, 7);
  }
  return Number(value.toFixed(1));
}

function oilinessScore(dryness, thirst, lowSleep, lowWater, goodSleep, goodWater) {
  let value;
  if (goodSleep && goodWater && dryness <= 3) value = 2 + random() * 1.8 + normal(0, 0.25);
  else if (lowSleep && lowWater && dryness >= 7) value = 4 + 0.52 * dryness + 0.22 * thirst + normal(0, 0.55);
  else value = 2.4 + 0.35 * dryness + 0.16 * thirst + normal(0, 0.5);
  return Number(clamp(value, 1, 10).toFixed(1));
}

function makeRecord({ recordId, userId, date, rowType, origin, sleepMinutes, sleepRecorded, waterMl, outdoorChoice, routine, dryness, forecastModel = "none" }) {
  const effectiveSleep = sleepMinutes ?? 390;
  const thirst = thirstScore(effectiveSleep, waterMl, outdoorChoice);
  const lowSleep = effectiveSleep < 360;
  const lowWater = waterMl < 1500;
  const goodSleep = effectiveSleep >= 420;
  const goodWater = waterMl >= 2000;
  const oiliness = oilinessScore(dryness, thirst, lowSleep, lowWater, goodSleep, goodWater);
  const outdoor = outdoorConfig[outdoorChoice];
  return {
    record_id: recordId,
    user_id: userId,
    local_date: isoDate(date),
    timezone: "Asia/Bangkok",
    baseline_skin_type: "oily",
    row_type: rowType,
    data_origin: origin,
    sleep_record_status: sleepRecorded ? "recorded" : "no_record",
    sleep_duration_hours: sleepRecorded ? Math.floor(sleepMinutes / 60) : null,
    sleep_duration_mins: sleepRecorded ? sleepMinutes % 60 : null,
    sleep_duration_total_minutes: sleepRecorded ? sleepMinutes : null,
    water_intake_ml: waterMl,
    thirst_score_0_10: thirst,
    outdoor_exposure_choice: outdoorChoice,
    outdoor_exposure_band: outdoor.label,
    outdoor_minutes_estimate: randomInt(outdoor.min, outdoor.max),
    routine_adherence: routine,
    skin_dryness_score_0_10: dryness,
    skin_dryness_risk_band: drynessBand(dryness),
    facial_oiliness_score_0_10: oiliness,
    skin_feeling_status: feeling(dryness, oiliness),
    forecast_model: forecastModel,
  };
}

function weightedChoice() {
  const ticket = random();
  if (ticket < 0.40) return 1;
  if (ticket < 0.73) return 2;
  if (ticket < 0.90) return 3;
  return 4;
}

function sampleSleep() {
  const ticket = random();
  if (ticket < 0.47) return randomInt(420, 540);
  if (ticket < 0.75) return randomInt(360, 419);
  return randomInt(180, 359);
}

function sampleWater(sleepMinutes) {
  const lowSleep = sleepMinutes < 360;
  const goodSleep = sleepMinutes >= 420;
  const ticket = random();
  if ((lowSleep && ticket < 0.58) || (!goodSleep && !lowSleep && ticket < 0.38) || (goodSleep && ticket < 0.22)) return randomInt(700, 1499);
  if ((lowSleep && ticket < 0.85) || (!goodSleep && !lowSleep && ticket < 0.76) || (goodSleep && ticket < 0.58)) return randomInt(1500, 1999);
  return randomInt(2000, 3000);
}

// Solve a small ridge regression: ARX(1) = ARIMAX(1,0,0) without MA or seasonal terms.
function solveLinearSystem(matrix, vector) {
  const size = vector.length;
  const augmented = matrix.map((row, index) => [...row, vector[index]]);
  for (let pivot = 0; pivot < size; pivot += 1) {
    let best = pivot;
    for (let row = pivot + 1; row < size; row += 1) if (Math.abs(augmented[row][pivot]) > Math.abs(augmented[best][pivot])) best = row;
    [augmented[pivot], augmented[best]] = [augmented[best], augmented[pivot]];
    const divisor = augmented[pivot][pivot] || 1e-9;
    for (let col = pivot; col <= size; col += 1) augmented[pivot][col] /= divisor;
    for (let row = 0; row < size; row += 1) {
      if (row === pivot) continue;
      const factor = augmented[row][pivot];
      for (let col = pivot; col <= size; col += 1) augmented[row][col] -= factor * augmented[pivot][col];
    }
  }
  return augmented.map((row) => row[size]);
}

function fitArx(training) {
  const featureNames = ["sleep_minutes", "water_ml", "outdoor_choice"];
  const stats = Object.fromEntries(featureNames.map((name) => {
    const values = training.map((row) => row[name]);
    const avg = mean(values);
    const sd = Math.sqrt(mean(values.map((value) => (value - avg) ** 2))) || 1;
    return [name, { avg, sd }];
  }));
  const x = [];
  const y = [];
  for (let index = 1; index < training.length; index += 1) {
    const row = training[index];
    x.push([
      1,
      training[index - 1].dryness,
      (row.sleep_minutes - stats.sleep_minutes.avg) / stats.sleep_minutes.sd,
      (row.water_ml - stats.water_ml.avg) / stats.water_ml.sd,
      (row.outdoor_choice - stats.outdoor_choice.avg) / stats.outdoor_choice.sd,
    ]);
    y.push(row.dryness);
  }
  const columns = x[0].length;
  const xtx = Array.from({ length: columns }, () => Array(columns).fill(0));
  const xty = Array(columns).fill(0);
  for (let row = 0; row < x.length; row += 1) {
    for (let left = 0; left < columns; left += 1) {
      xty[left] += x[row][left] * y[row];
      for (let right = 0; right < columns; right += 1) xtx[left][right] += x[row][left] * x[row][right];
    }
  }
  for (let diagonal = 1; diagonal < columns; diagonal += 1) xtx[diagonal][diagonal] += 0.8;
  const coefficients = solveLinearSystem(xtx, xty);
  coefficients[1] = clamp(coefficients[1], -0.25, 0.70);
  return { featureNames, stats, coefficients };
}

function predictArx(model, previousDryness, sleepMinutes, waterMl, outdoorChoice) {
  const [intercept, lag, sleepWeight, waterWeight, outdoorWeight] = model.coefficients;
  const sleepZ = (sleepMinutes - model.stats.sleep_minutes.avg) / model.stats.sleep_minutes.sd;
  const waterZ = (waterMl - model.stats.water_ml.avg) / model.stats.water_ml.sd;
  const outdoorZ = (outdoorChoice - model.stats.outdoor_choice.avg) / model.stats.outdoor_choice.sd;
  return Number(clamp(intercept + lag * previousDryness + sleepWeight * sleepZ + waterWeight * waterZ + outdoorWeight * outdoorZ, 0, 10).toFixed(1));
}

// Fourteen entries from the supplied template. The original year contains a typo (20026),
// so the sequence is normalized to 2026-09-12 through 2026-09-25 for time-series use.
const userSample = {
  sleep: [222, 367, 123, null, 340, 468, 304, null, 316, 458, 441, 527, 470, 408],
  water: [1600, 1300, 1500, 1200, 1400, 1300, 1600, 1100, 1000, 1800, 1500, 1600, 1200, 1250],
  outdoor: [1, 1, 1, 1, 1, 1, 1, 1, 1, 4, 4, 4, 1, 1],
  dryness: [2, 4, 2, 3, 2.5, 4, 2, 3, 4, 3, 2, 2, 4, 3],
};
const imputedSleep = userSample.sleep.map((value, index, values) => {
  if (value !== null) return value;
  const previous = values[index - 1];
  const next = values[index + 1];
  return Math.round((previous + next) / 2);
});
const training = userSample.dryness.map((dryness, index) => ({
  dryness,
  sleep_minutes: imputedSleep[index],
  water_ml: userSample.water[index],
  outdoor_choice: userSample.outdoor[index],
}));
const arxModel = fitArx(training);
const records = [];
const datasetStartDate = new Date("2026-08-01T00:00:00.000Z");
const seedStartDate = new Date("2026-09-12T00:00:00.000Z");

// Backfill user_001 from 1 Aug to 11 Sep as explicitly synthetic history.
for (let day = 0; day < 42; day += 1) {
  const latentSleep = sampleSleep();
  const water = sampleWater(latentSleep);
  const outdoorChoice = weightedChoice();
  const routine = random() < 0.67 ? "yes" : "no";
  const dryness = simulatedDryness(latentSleep, water, outdoorChoice, routine);
  const watchWorn = random() >= 0.12;
  records.push(makeRecord({
    recordId: `BCK-001-${String(day + 1).padStart(2, "0")}`,
    userId: "synthetic_user_01",
    date: dateAfter(datasetStartDate, day),
    rowType: "synthetic_backfill",
    origin: "synthetic_rule_based_v3",
    sleepMinutes: latentSleep,
    sleepRecorded: watchWorn,
    waterMl: water,
    outdoorChoice,
    routine,
    dryness,
  }));
}

for (let day = 0; day < 14; day += 1) {
  const sleepMinutes = userSample.sleep[day];
  records.push(makeRecord({
    recordId: `OBS-001-${String(day + 1).padStart(2, "0")}`,
    userId: "synthetic_user_01",
    date: dateAfter(seedStartDate, day),
    rowType: "observed_seed",
    origin: "user_sample_normalized",
    sleepMinutes,
    sleepRecorded: sleepMinutes !== null,
    waterMl: userSample.water[day],
    outdoorChoice: userSample.outdoor[day],
    routine: day % 3 === 0 ? "no" : "yes",
    dryness: userSample.dryness[day],
  }));
}

let previousForecast = userSample.dryness.at(-1);
const forecastRows = [];
for (let day = 14; day < 19; day += 1) {
  const templateIndex = day % 14;
  const scenarioSleep = Math.round(clamp(imputedSleep[templateIndex] + normal(0, 24), 180, 540));
  const scenarioWater = Math.round(clamp(userSample.water[templateIndex] + normal(0, 150), 700, 2600));
  const scenarioOutdoor = random() < 0.74 ? userSample.outdoor[templateIndex] : weightedChoice();
  const forecastDryness = predictArx(arxModel, previousForecast, scenarioSleep, scenarioWater, scenarioOutdoor);
  const watchWorn = random() >= 0.12;
  const record = makeRecord({
    recordId: `FRC-001-${String(day - 13).padStart(2, "0")}`,
    userId: "synthetic_user_01",
    date: dateAfter(seedStartDate, day),
    rowType: "forecast_within_date_window",
    origin: "arx_forecast_with_synthetic_exog_scenario",
    sleepMinutes: scenarioSleep,
    sleepRecorded: watchWorn,
    waterMl: scenarioWater,
    outdoorChoice: scenarioOutdoor,
    routine: random() < 0.67 ? "yes" : "no",
    dryness: forecastDryness,
    forecastModel: "ARX(1)_ARIMAX(1,0,0)_demo",
  });
  record.sleep_minutes_model_input = scenarioSleep;
  record.sleep_was_imputed_for_model = watchWorn ? "no" : "yes";
  forecastRows.push(record);
  records.push(record);
  previousForecast = forecastDryness;
}

// 19 additional synthetic users × 61 days = 1,159 records. Together with user_001 = 1,220.
for (let userNumber = 2; userNumber <= 20; userNumber += 1) {
  for (let day = 0; day < 61; day += 1) {
    const latentSleep = sampleSleep();
    const water = sampleWater(latentSleep);
    const outdoorChoice = weightedChoice();
    const routine = random() < 0.67 ? "yes" : "no";
    const dryness = simulatedDryness(latentSleep, water, outdoorChoice, routine);
    const watchWorn = random() >= 0.12;
    records.push(makeRecord({
      recordId: `SYN-${String(userNumber).padStart(2, "0")}-${String(day + 1).padStart(2, "0")}`,
      userId: `synthetic_user_${String(userNumber).padStart(2, "0")}`,
      date: dateAfter(datasetStartDate, day),
      rowType: "synthetic_simulated",
      origin: "synthetic_rule_based_v2",
      sleepMinutes: latentSleep,
      sleepRecorded: watchWorn,
      waterMl: water,
      outdoorChoice,
      routine,
      dryness,
    }));
  }
}

const fullCsv = [headers, ...records.map((record) => headers.map((header) => record[header]))].map((row) => row.map(csvCell).join(",")).join("\n");
await fs.writeFile(dataPath, `${fullCsv}\n`, "utf8");

const forecastHeaders = [
  "user_id", "local_date", "forecast_week", "sleep_record_status", "sleep_duration_hours", "sleep_duration_mins",
  "sleep_minutes_model_input", "sleep_was_imputed_for_model", "water_intake_ml", "outdoor_exposure_choice",
  "outdoor_exposure_band", "forecast_skin_dryness_score_0_10", "forecast_model", "forecast_note",
];
const forecastCsvRows = forecastRows.map((record, index) => [
  record.user_id, record.local_date, Math.floor(index / 7) + 3, record.sleep_record_status,
  record.sleep_duration_hours, record.sleep_duration_mins, record.sleep_minutes_model_input,
  record.sleep_was_imputed_for_model, record.water_intake_ml, record.outdoor_exposure_choice,
  record.outdoor_exposure_band, record.skin_dryness_score_0_10, record.forecast_model,
  "Exploratory only: 14-day seed and synthetic future exogenous scenario.",
]);
await fs.writeFile(forecastPath, `${[forecastHeaders, ...forecastCsvRows].map((row) => row.map(csvCell).join(",")).join("\n")}\n`, "utf8");

const byType = ["synthetic_backfill", "observed_seed", "forecast_within_date_window", "synthetic_simulated"].map((type) => {
  const matching = records.filter((record) => record.row_type === type);
  return [type, matching.length, matching.filter((record) => record.sleep_record_status === "no_record").length, Number(mean(matching.map((record) => record.skin_dryness_score_0_10)).toFixed(2))];
});
const ruleGroups = [
  ["Adequate sleep + adequate water", (record) => record.sleep_duration_total_minutes >= 420 && record.water_intake_ml >= 2000, "1–3"],
  ["Adequate sleep + low water", (record) => record.sleep_duration_total_minutes >= 420 && record.water_intake_ml < 1500, "4–6"],
  ["Low sleep + low water", (record) => record.sleep_duration_total_minutes !== null && record.sleep_duration_total_minutes < 360 && record.water_intake_ml < 1500, "7–10"],
].map(([label, predicate, expected]) => {
  const matching = records.filter((record) => record.row_type === "synthetic_simulated" && predicate(record));
  return [label, matching.length, Number(mean(matching.map((record) => record.skin_dryness_score_0_10)).toFixed(2)), Math.min(...matching.map((record) => record.skin_dryness_score_0_10)), Math.max(...matching.map((record) => record.skin_dryness_score_0_10)), expected];
});

const workbook = Workbook.create();
const summarySheet = workbook.worksheets.add("EDA Summary");
const dataSheet = workbook.worksheets.add("Time Series Data");
const forecastSheet = workbook.worksheets.add("User001 Forecast");
const dictionarySheet = workbook.worksheets.add("Data Dictionary");
const sourcesSheet = workbook.worksheets.add("Sources and Limits");
for (const sheet of [summarySheet, dataSheet, forecastSheet, dictionarySheet, sourcesSheet]) sheet.showGridLines = false;

const bodyFont = { name: "Arial", size: 10, color: "#1F2937" };
const headerStyle = { fill: "#0F766E", font: { name: "Arial", size: 10, bold: true, color: "#FFFFFF" }, horizontalAlignment: "center", verticalAlignment: "center", wrapText: true };
const titleStyle = { font: { name: "Arial", size: 14, bold: true, color: "#1F2937" } };

summarySheet.getRange("A2").values = [["Lifestyle time-series dataset: 1 Aug–30 Sep, missing sleep and ARX forecast"]];
summarySheet.getRange("A2").format = titleStyle;
summarySheet.getRange("A4:B8").values = [
  ["Metric", "Value"],
  ["Total records", records.length],
  ["Synthetic users", 20],
  ["Time horizon per user", "61 days (1 Aug–30 Sep 2026)"],
  ["Sleep no_record rows", records.filter((record) => record.sleep_record_status === "no_record").length],
];
summarySheet.getRange("A4:B4").format = headerStyle;
summarySheet.getRange("A4:B8").format.font = bodyFont;
summarySheet.getRange("A11:D11").values = [["Row type", "Records", "Sleep no_record", "Mean dryness"]];
summarySheet.getRange("A11:D11").format = headerStyle;
summarySheet.getRange("A12:D15").values = byType;
summarySheet.getRange("A11:D15").format.font = bodyFont;
summarySheet.getRange("A17:F17").values = [["Synthetic condition", "Records", "Mean dryness", "Min", "Max", "Expected range"]];
summarySheet.getRange("A17:F17").format = headerStyle;
summarySheet.getRange("A18:F20").values = ruleGroups;
summarySheet.getRange("A17:F20").format.font = bodyFont;
summarySheet.getRange("A23").values = [["Forecast interpretation"]];
summarySheet.getRange("A23").format = { fill: "#E0F2FE", font: { name: "Arial", size: 10, bold: true, color: "#075985" } };
summarySheet.getRange("A24:F26").values = [
  ["Model", "ARX(1), equivalent to ARIMAX(1,0,0) without MA/seasonality", null, null, null, null],
  ["Training basis", "14 daily observations from the supplied sample; 2 missing sleep readings are linearly imputed for model input only.", null, null, null, null],
  ["Forecast horizon", "26–30 Sep 2026 (5 days), limited by the requested data window. Sleep/water/outdoor future inputs are synthetic scenarios, so this is exploratory only.", null, null, null, null],
];
for (let row = 24; row <= 26; row += 1) summarySheet.getRange(`B${row}:F${row}`).merge();
summarySheet.getRange("A24:F26").format = { font: { name: "Arial", size: 10, color: "#374151" }, wrapText: true, verticalAlignment: "top" };
summarySheet.getRange("A24:F26").format.rowHeight = 32;

const rowTypeChart = summarySheet.charts.add("bar", [summarySheet.getRange("A11:A15"), summarySheet.getRange("D11:D15")]);
rowTypeChart.title = "Mean dryness by data origin";
rowTypeChart.hasLegend = false;
rowTypeChart.setPosition("H4", "P16");
rowTypeChart.series.items[0].fill = "#2563EB";
const ruleChart = summarySheet.charts.add("bar", [summarySheet.getRange("A17:A20"), summarySheet.getRange("C17:C20")]);
ruleChart.title = "Synthetic rule calibration";
ruleChart.hasLegend = false;
ruleChart.setPosition("H18", "P30");
ruleChart.series.items[0].fill = "#D97706";

dataSheet.getRangeByIndexes(0, 0, records.length + 1, headers.length).values = [headers, ...records.map((record) => headers.map((header) => record[header]))];
dataSheet.getRangeByIndexes(0, 0, 1, headers.length).format = headerStyle;
dataSheet.getRangeByIndexes(1, 0, records.length, headers.length).format.font = bodyFont;
dataSheet.getRange(`C2:C${records.length + 1}`).format.numberFormat = "yyyy-mm-dd";
for (const column of ["M", "R", "T"]) dataSheet.getRange(`${column}2:${column}${records.length + 1}`).format.numberFormat = "0.0";
dataSheet.tables.add(`A1:V${records.length + 1}`, true, "LifestyleTimeseriesV2");
dataSheet.freezePanes.freezeRows(1);
dataSheet.getRange(`H2:H${records.length + 1}`).conditionalFormats.add("containsText", { text: "no_record", format: { fill: "#FEE2E2", font: { color: "#B91C1C", bold: true } } });
dataSheet.getRange(`R2:R${records.length + 1}`).conditionalFormats.add("colorScale", { colors: ["#DCFCE7", "#FDE68A", "#FCA5A5"], thresholds: ["min", { type: "percentile", value: 50 }, "max"] });

forecastSheet.getRange("A2").values = [["User 001 exploratory ARX forecast: 26–30 Sep 2026"]];
forecastSheet.getRange("A2").format = titleStyle;
forecastSheet.getRange("A4:N4").values = [forecastHeaders];
forecastSheet.getRange("A4:N4").format = headerStyle;
forecastSheet.getRangeByIndexes(4, 0, forecastCsvRows.length, forecastHeaders.length).values = forecastCsvRows;
forecastSheet.getRange(`A5:N${forecastCsvRows.length + 4}`).format.font = bodyFont;
forecastSheet.getRange(`B5:B${forecastCsvRows.length + 4}`).format.numberFormat = "yyyy-mm-dd";
forecastSheet.getRange(`L5:L${forecastCsvRows.length + 4}`).format.numberFormat = "0.0";
forecastSheet.tables.add(`A4:N${forecastCsvRows.length + 4}`, true, "User001Forecast");
forecastSheet.freezePanes.freezeRows(4);
const forecastChart = forecastSheet.charts.add("line", [forecastSheet.getRange(`B4:B${forecastCsvRows.length + 4}`), forecastSheet.getRange(`L4:L${forecastCsvRows.length + 4}`)]);
forecastChart.title = "Forecast skin dryness score (0–10)";
forecastChart.hasLegend = false;
forecastChart.setPosition("P4", "Z22");
forecastChart.series.items[0].line = { fill: "#D97706", style: "solid", width: 2 };

const dictionary = [
  ["Field", "Type / unit", "Meaning"],
  ["row_type", "category", "synthetic_backfill: Aug 1–Sep 11 for user_001; observed_seed: normalized user sample; forecast_within_date_window: model output; synthetic_simulated: rule-based synthetic rows."],
  ["sleep_record_status", "category", "recorded or no_record. Numeric sleep columns are blank when no_record."],
  ["sleep_duration_hours / sleep_duration_mins", "integer", "Separate input fields requested for daily sleep data."],
  ["sleep_duration_total_minutes", "minutes", "Derived total. Null when sleep is not recorded."],
  ["outdoor_exposure_choice", "ordinal 1–4", "1: <1 hour; 2: 1–2 hours; 3: 3–4 hours; 4: ≥4 hours."],
  ["outdoor_minutes_estimate", "minutes", "Representative numeric model feature. 121–179 minutes are excluded because no supplied choice covers 2–3 hours."],
  ["skin_dryness_score_0_10", "0–10", "Synthetic target/forecast score. It is not a clinical diagnostic score."],
  ["forecast_model", "text", "ARX(1) / ARIMAX(1,0,0) demonstration used only for user_001 future rows."],
  ["sleep_minutes_model_input", "minutes", "Forecast-only field in User001 Forecast; imputed scenario value when no watch sleep record exists."],
];
dictionarySheet.getRangeByIndexes(0, 0, dictionary.length, 3).values = dictionary;
dictionarySheet.getRange("A1:C1").format = headerStyle;
dictionarySheet.getRange(`A2:C${dictionary.length}`).format = { font: bodyFont, wrapText: true, verticalAlignment: "top" };

const sources = [
  ["Source or limitation", "Use in this workbook", "URL / detail"],
  ["User-provided 14-day template", "Seed for user_001 observed rows. Invalid 20026 date year was normalized to a consecutive 2026-09-12 to 2026-09-25 sequence. Aug 1–Sep 11 is explicit synthetic backfill.", "Attached user_daily_health_tracker_template.csv.xlsx"],
  ["User-provided scoring guide", "Synthetic calibration: adequate sleep + adequate water → 1–3; adequate sleep + low water → 4–6; low sleep + low water → 7–10.", "Conversation requirement"],
  ["Akdeniz et al. (2018)", "Direction only: evidence for drinking water and skin hydration is limited/weak; no clinical water threshold was inferred.", "https://pubmed.ncbi.nlm.nih.gov/29392767/"],
  ["Oyetakin-White et al. (2015)", "Direction only: poor sleep quality was associated with poorer skin barrier recovery in a small study.", "https://pubmed.ncbi.nlm.nih.gov/25266053/"],
  ["Forecast limitation", "Two weeks and two missing sleep readings do not support reliable seasonality or validation. ARX is exploratory; forecast is restricted to five days to respect the 1 Aug–30 Sep date window.", "Not medical advice or Zepp/Amazfit output"],
];
sourcesSheet.getRangeByIndexes(0, 0, sources.length, 3).values = sources;
sourcesSheet.getRange("A1:C1").format = headerStyle;
sourcesSheet.getRange(`A2:C${sources.length}`).format = { font: bodyFont, wrapText: true, verticalAlignment: "top" };

for (const sheet of [summarySheet, dataSheet, forecastSheet, dictionarySheet, sourcesSheet]) {
  const used = sheet.getUsedRange();
  used.format.autofitColumns();
  used.format.autofitRows();
}
summarySheet.getRange("A:A").format.columnWidth = 35;
summarySheet.getRange("B:F").format.columnWidth = 18;
dataSheet.getRange("A:A").format.columnWidth = 16;
dataSheet.getRange("B:B").format.columnWidth = 18;
dataSheet.getRange("C:C").format.columnWidth = 13;
dataSheet.getRange("F:G").format.columnWidth = 30;
dataSheet.getRange("H:H").format.columnWidth = 17;
dataSheet.getRange("O:O").format.columnWidth = 22;
dataSheet.getRange("U:U").format.columnWidth = 20;
forecastSheet.getRange("A:A").format.columnWidth = 18;
forecastSheet.getRange("B:B").format.columnWidth = 14;
forecastSheet.getRange("N:N").format.columnWidth = 70;
dictionarySheet.getRange("A:A").format.columnWidth = 35;
dictionarySheet.getRange("B:B").format.columnWidth = 22;
dictionarySheet.getRange("C:C").format.columnWidth = 95;
sourcesSheet.getRange("A:A").format.columnWidth = 32;
sourcesSheet.getRange("B:B").format.columnWidth = 95;
sourcesSheet.getRange("C:C").format.columnWidth = 70;

workbook.recalculate();
const preview = await workbook.render({ sheetName: "EDA Summary", range: "A1:P28", scale: 1.2, format: "png" });
await fs.writeFile(previewPath, new Uint8Array(await preview.arrayBuffer()));
const exported = await SpreadsheetFile.exportXlsx(workbook);
await exported.save(workbookPath);

console.log(JSON.stringify({ dataPath, forecastPath, workbookPath, previewPath, recordCount: records.length, noRecordCount: records.filter((record) => record.sleep_record_status === "no_record").length, arxCoefficients: arxModel.coefficients.map((value) => Number(value.toFixed(3))), rowTypeSummary: byType, ruleGroups }, null, 2));
