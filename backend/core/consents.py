"""Versioned consent scopes used across routes and offline model jobs."""

LEGACY_MODEL_TRAINING_CONSENT_VERSION = "daily-health-model-training-v1"
MODEL_TRAINING_CONSENT_VERSION = "daily-health-model-training-v2"
MODEL_TRAINING_CONSENT_VERSIONS = (
    LEGACY_MODEL_TRAINING_CONSENT_VERSION, MODEL_TRAINING_CONSENT_VERSION,
)
ACNE_TRACKING_CONSENT_VERSION = "acne-tracking-v1"
ACNE_MODEL_TRAINING_CONSENT_VERSION = "acne-model-training-v1"
WRINKLE_TRAINING_CONSENT_VERSION = "wrinkle-model-training-v1"
