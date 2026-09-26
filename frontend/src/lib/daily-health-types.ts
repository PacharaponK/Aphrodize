export type AttentionLevel = "low" | "moderate" | "high" | null;

export type ScorePrediction = {
  value: number | null;
  status: "predicted" | "experimental_out_of_domain" | "not_available";
};

export type HealthSignal = {
  level: AttentionLevel;
  status: "available" | "not_available" | "out_of_training_domain" | "insufficient_data" | "insufficient_history";
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
};

export type PredictionResponse = {
  local_date: string;
  model_status: string;
  input_domain_status: "in_domain" | "out_of_training_domain";
  input_domain_reasons: string[];
  prediction_mode: "standard" | "test_only";
  prediction_status: "predicted" | "experimental_out_of_domain" | "abstained";
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
  interpretation: {
    daily_health_summary: HealthSignal;
    skin_care_attention_level: HealthSignal;
    acne_flare_signal: HealthSignal;
    next_day_predictions: {
      low_energy_signal: HealthSignal;
      thirst_attention: HealthSignal;
    };
    profile_guidance: ProfileGuidance[];
  };
  guidance: string[];
  warnings: string[];
};

export type SmokingStatus = "current" | "former" | "never" | "prefer_not_to_say";
export type AgeBand = "13_17" | "18_60" | "61_64" | "65_plus";

export type DailyHealthProfile = {
  has_session: boolean;
  consent_active: boolean;
  age_guidance_consent_active: boolean;
  can_report_outcomes: boolean;
  age_band: AgeBand | null;
  smoking_status: SmokingStatus | null;
};
