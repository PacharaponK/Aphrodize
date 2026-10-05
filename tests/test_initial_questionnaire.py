from backend.api.schemas.consent import InitialWellnessQuestionnaire


def test_initial_questionnaire_accepts_profile_without_daily_answers():
    profile = {
        "sex": "female",
        "age_group": "25_34",
        "age_years": 25,
        "sunscreen_frequency": "sometimes",
        "skin_type": "normal",
        "menstrual_tracking": "yes",
        "wellness_goal": "general_wellness",
    }
    answers = InitialWellnessQuestionnaire.model_validate(profile).answers_for_storage()
    assert answers["menstrual_tracking"] == "yes"
    daily_keys = {
        "sleep_hours", "sleep_quality", "water_liters", "outdoor_minutes",
        "stress_level", "menstrual_status",
    }
    assert daily_keys.isdisjoint(answers)
    # An older browser's payload remains accepted, without saving stale daily values.
    legacy = {**profile, **dict.fromkeys(daily_keys, 1)}
    assert InitialWellnessQuestionnaire.model_validate(legacy).answers_for_storage() == answers
