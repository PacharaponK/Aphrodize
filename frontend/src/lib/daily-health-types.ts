export type AttentionLevel = "low" | "moderate" | "high" | null;

export type ScorePrediction = {
  value: number | null;
  status: "predicted" | "calculated" | "experimental_out_of_domain" | "not_available";
  method?: string | null;
  target_date?: string | null;
};

export type HydrationCalculation = {
  score_0_10: number | null;
  method: string;
  formula: string;
  reference_lower_ml: number | null;
  reference_upper_ml: number | null;
  recorded_shortfall_ml: number | null;
  range_status: "below_reference" | "within_reference" | "above_reference" | "missing_weight" | "unsupported_age";
  reference_url: string;
  scope: string;
};

export type HealthSignal = {
  level: AttentionLevel;
  status: "available" | "not_available" | "out_of_training_domain" | "insufficient_data" | "insufficient_history" | "not_supported" | "model_not_ready" | "predicted";
  value_0_10?: number;
  target_date?: string;
  model_id?: string;
  method?: string;
  target?: "perceived_energy" | "perceived_thirst";
  reason_codes?: string[];
  headline?: string;
  drivers?: string[];
  possible_signals?: string[];
  recommendations?: string[];
};

export type ProfileGuidance = {
  topic: string;
  status: "available";
  message: string;
  reference_url?: string;
  reference_label?: string;
};

export type DailyHealthInterpretation = {
  daily_health_summary: HealthSignal;
  skin_care_attention_level: HealthSignal;
  acne_flare_signal: HealthSignal;
  next_day_predictions: {
    low_energy_signal: HealthSignal;
    thirst_attention: HealthSignal;
  };
  profile_guidance: ProfileGuidance[];
};

export type DailyHealthScores = {
  thirst_score_0_10: ScorePrediction;
  skin_dryness_score_0_10: ScorePrediction;
};

export type PredictionResponse = {
  forecast_receipt?: string | null;
  local_date: string;
  prediction_target_date: string;
  model_status: string;
  input_domain_status: "in_domain" | "out_of_training_domain";
  input_domain_reasons: string[];
  prediction_mode: "standard" | "test_only";
  prediction_status: "predicted" | "experimental_out_of_domain" | "abstained";
  input: {
    sleep_duration_total_minutes: number;
    water_intake_ml: number;
    weight_kg?: number | null;
    outdoor_exposure_choice: number;
  };
  calculated: {
    thirst_score_0_10?: number | null;
    hydration?: HydrationCalculation;
    sleep_score_0_100: number;
    sleep_score_method: string;
    sleep_score_scope: string;
  };
  predictions: DailyHealthScores;
  model?: { model_id?: string; family?: string; prediction_horizon_days?: number };
  interpretation: DailyHealthInterpretation;
  guidance: string[];
  warnings: string[];
};

export type DailyHealthHistoryItem = {
  local_date: string;
  prediction_target_date: string | null;
  prediction_status: string;
  prediction_model_id: string | null;
  input_domain_status: "in_domain" | "out_of_training_domain";
  input: {
    sleep_duration_total_minutes: number;
    water_intake_ml: number;
    weight_kg?: number | null;
    outdoor_exposure_choice: number;
  };
  calculated: { sleep_score_0_100: number };
  predictions: DailyHealthScores;
  interpretation: DailyHealthInterpretation;
};

export type DailyHealthHistoryResponse = {
  items: DailyHealthHistoryItem[];
};

export type PersonalForecastMetric = {
  value: number | null;
  status: "predicted" | "insufficient_history";
};

export type PersonalForecastDay = {
  local_date: string;
  sleep_duration_minutes: number | null;
  water_intake_ml: number | null;
};

export type DailyHealthPersonalForecast = {
  enabled: boolean;
  status:
    | "daily_health_consent_required"
    | "consent_required"
    | "forecasted"
    | "insufficient_history";
  prediction_target_date?: string;
  history_start_date?: string;
  history_end_date?: string;
  actual?: PersonalForecastDay[];
  predictions?: {
    sleep_duration_minutes: PersonalForecastMetric;
    water_intake_ml: PersonalForecastMetric;
  };
  model?: {
    model_id: string;
    family: string;
    scope: "account_only";
    prediction_horizon_days: 1;
    history_window_days: number;
    observations_used: number;
    minimum_observations: number;
    method: string;
  };
};

export type SmokingStatus = "current" | "former" | "never" | "prefer_not_to_say";
export type AgeBand = "13_17" | "18_60" | "61_64" | "65_plus";
export type SkinType =
  | "normal"
  | "dry"
  | "oily"
  | "combination"
  | "sensitive"
  | "prefer_not_to_say";

export type DailyHealthProfile = {
  has_session: boolean;
  consent_active: boolean;
  age_guidance_consent_active: boolean;
  weight_profile_consent_active?: boolean;
  weight_kg?: number | null;
  height_profile_consent_active?: boolean;
  height_cm?: number | null;
  skin_type_guidance_consent_active?: boolean;
  model_training_consent_active: boolean;
  can_report_outcomes: boolean;
  age_band: AgeBand | null;
  smoking_status: SmokingStatus | null;
  skin_type?: SkinType | null;
};
