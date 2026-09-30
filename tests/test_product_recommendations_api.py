from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException

from backend.api.v1.routes.analyses import get_recommendations
from backend.core.db.models import AnalysisStatus


class FakeSession:
    def __init__(self, analysis, questionnaire, *scalar_results):
        self.analysis = analysis
        self.questionnaire = questionnaire
        self.scalar_results = iter(scalar_results)
        self.queries = []

    async def get(self, _model, _id):
        return self.analysis

    async def scalar(self, _query):
        self.queries.append(_query)
        if self.questionnaire is not None:
            questionnaire, self.questionnaire = self.questionnaire, None
            return questionnaire
        return next(self.scalar_results, None)


def sample_analysis(user_id):
    return SimpleNamespace(
        id=uuid4(), user_id=user_id, status=AnalysisStatus.completed,
        image_quality_score=1.0,
        result={"recommendation_gate": {"eligible": False}},
    )


@pytest.mark.asyncio
async def test_recommendation_endpoint_hides_analysis_from_non_owner():
    owner_id = uuid4()
    analysis = sample_analysis(owner_id)

    with pytest.raises(HTTPException) as error:
        await get_recommendations(
            analysis.id, user_id=uuid4(), session=FakeSession(analysis, None),
        )

    assert error.value.status_code == 404


@pytest.mark.asyncio
async def test_recommendation_endpoint_uses_the_owner_questionnaire():
    owner_id = uuid4()
    analysis = sample_analysis(owner_id)
    questionnaire = SimpleNamespace(id=uuid4(), answers={
        "skin_type": "dry", "skin_sensitivity": "low",
        "known_product_allergy": "no", "severe_irritation": "no",
    })

    result = await get_recommendations(
        analysis.id, user_id=owner_id,
        session=FakeSession(analysis, questionnaire, None),
    )

    assert result["recommendations"][0]["input_fields"] == ["skin_type"]
    assert result["recommendations"][0]["signal_sources"] == ["self_reported"]


@pytest.mark.asyncio
async def test_recommendation_endpoint_uses_only_consent_authorized_daily_context():
    owner_id = uuid4()
    analysis = sample_analysis(owner_id)
    questionnaire = SimpleNamespace(id=uuid4(), answers={
        "skin_type": "normal", "sunscreen_frequency": "sometimes",
        "skin_sensitivity": "low", "known_product_allergy": "no", "severe_irritation": "no",
    })
    lifestyle = SimpleNamespace(
        id=uuid4(), local_date=__import__("datetime").date.today(), sleep_duration_minutes=360,
        water_intake_ml=1200, outdoor_exposure_choice=3,
    )
    consent = SimpleNamespace(id=uuid4(), version="daily-health-v1")
    session = FakeSession(analysis, questionnaire, consent, lifestyle, None)

    result = await get_recommendations(analysis.id, user_id=owner_id, session=session)

    assert result["recommendations"][0]["category"] == "broad-spectrum sunscreen SPF 30+"
    assert result["recommendations"][0]["signal_sources"] == [
        "self_reported",
        "daily_health_reported",
    ]
    assert result["daily_context"]["consent"] == {
        "record_id": str(consent.id), "version": "daily-health-v1",
    }
    assert result["daily_context"]["lifestyle"] == {
        "source_table": "daily_health_entries", "record_id": str(lifestyle.id),
        "observed_date": lifestyle.local_date.isoformat(), "sleep_duration_minutes": 360,
        "water_intake_ml": 1200, "outdoor_exposure_choice": 3,
    }
    sql = "\n".join(str(query) for query in session.queries)
    assert "reported_dryness_level_0_10 IS NOT NULL" in sql
    assert "local_date BETWEEN" in sql
    assert "target_date BETWEEN" in sql


@pytest.mark.asyncio
async def test_recommendation_endpoint_uses_outcome_for_dryness_with_provenance():
    owner_id = uuid4()
    analysis = sample_analysis(owner_id)
    questionnaire = SimpleNamespace(id=uuid4(), answers={
        "skin_type": "normal", "skin_sensitivity": "low",
        "known_product_allergy": "no", "severe_irritation": "no",
    })
    observed_on = __import__("datetime").date.today()
    outcome = SimpleNamespace(id=uuid4(), target_date=observed_on, reported_dryness_level_0_10=7)
    consent = SimpleNamespace(id=uuid4(), version="daily-health-v1")
    session = FakeSession(analysis, questionnaire, consent, None, outcome)

    result = await get_recommendations(analysis.id, user_id=owner_id, session=session)

    assert result["daily_context"]["reported_dryness"] == {
        "source_table": "daily_health_outcomes", "record_id": str(outcome.id),
        "observed_date": observed_on.isoformat(), "value": 7,
    }
    assert result["recommendations"][0]["signal_sources"] == ["daily_health_reported"]
    sql = "\n".join(str(query) for query in session.queries)
    assert "daily_health_entries.reported_dryness_score_0_10" not in sql
    assert "daily_health_outcomes.reported_dryness_level_0_10 IS NOT NULL" in sql


@pytest.mark.asyncio
async def test_recommendation_endpoint_reports_missing_questionnaire_for_full_edit_cta():
    owner_id = uuid4()
    analysis = sample_analysis(owner_id)

    result = await get_recommendations(
        analysis.id, user_id=owner_id, session=FakeSession(analysis, None, None),
    )

    assert result["status"] == "safety_blocked"
    assert result["questionnaire_context"] == {"status": "missing", "revision_id": None}
