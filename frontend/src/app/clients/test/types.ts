export type ScorePrediction = { value: number | null; status: "predicted" | "not_available" };

export type PredictionResponse = {
  local_date: string;
  model_status: string;
  input: {
    sleep_duration_total_minutes: number;
    water_intake_ml: number;
    outdoor_exposure_choice: number;
  };
  predictions: {
    thirst_score_0_10: ScorePrediction;
    skin_dryness_score_0_10: ScorePrediction;
  };
  model?: { model_id?: string; family?: string };
  guidance: string[];
  warnings: string[];
};

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
