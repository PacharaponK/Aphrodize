import type { PredictionResponse } from "@/lib/daily-health-types";

export type { PredictionResponse };

export type PredictionTestValues = {
  localDate: string;
  sleepHours: string;
  sleepMinutes: string;
  waterIntakeMl: string;
  outdoorChoice: string;
};

export type PredictionActionState = {
  result: PredictionResponse | null;
  error: string;
  values: PredictionTestValues;
};
