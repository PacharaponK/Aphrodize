import type { DailyHealthHistoryItem } from "./daily-health-types";

/** Select existing account records, never fill missing calendar days. */
export function selectHistoryDays(
  items: DailyHealthHistoryItem[],
  fromDate: string,
  toDate: string,
  selectedDate = "",
): DailyHealthHistoryItem[] {
  if (selectedDate && (selectedDate < fromDate || selectedDate > toDate)) return [];
  const sorted = items
    .filter((item) => item.local_date >= fromDate && item.local_date <= toDate)
    .sort((a, b) => b.local_date.localeCompare(a.local_date));
  return selectedDate
    ? sorted.filter((item) => item.local_date === selectedDate)
    : sorted.slice(0, 3);
}
