from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException

from backend.api.v1.routes.analyses import get_profile_recommendations, get_recommendations
from backend.core.db.models import AnalysisStatus, Product, UserProfile


class FakeSession:
    def __init__(self, analysis, questionnaire, *scalar_results, profile=None,
                 products=(), consent=True):
        self.analysis = analysis
        self.questionnaire = questionnaire
        self.scalar_results = iter(scalar_results)
        self.queries = []
        self.profile = profile
        self.products = products
        self.consent = consent

    async def get(self, _model, _id):
        return self.profile if _model is UserProfile else self.analysis

    async def scalar(self, _query):
        self.queries.append(_query)
        if _query.compile().params.get("version_1") == "signup-v1":
            return uuid4() if self.consent else None
        if self.questionnaire is not None:
            questionnaire, self.questionnaire = self.questionnaire, None
            return questionnaire
        return next(self.scalar_results, None)

    async def scalars(self, query):
        self.queries.append(query)
        return SimpleNamespace(all=lambda: self.products)


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


@pytest.mark.asyncio
async def test_both_endpoints_use_current_profile_instead_of_stale_questionnaire():
    owner_id = uuid4()
    candidate = sample_analysis(owner_id)
    questionnaire = SimpleNamespace(id=uuid4(), answers={
        "skin_type": "dry", "skin_sensitivity": "low", "age_group": "25_34",
        "age_years": 30, "known_product_allergy": "no", "severe_irritation": "no",
    })
    profile = SimpleNamespace(
        skin_type="oily", age_group="13_17", sex="female", sunscreen_frequency="every_day",
    )
    for endpoint in (get_recommendations, get_profile_recommendations):
        session = FakeSession(candidate, questionnaire, None, profile=profile)
        if endpoint is get_recommendations:
            result = await endpoint(candidate.id, user_id=owner_id, session=session)
        else:
            result = await endpoint(user_id=owner_id, session=session)
        assert [item["rule_id"] for item in result["recommendations"]] == [
            "R-YOUTH-CLEANSE-001", "R-YOUTH-MOIST-001", "R-YOUTH-SUN-001",
        ]
        assert result["profile_context"]["age_years"] is None
        assert result["profile_context"]["source"] == "user_profile"
        sql = "\n".join(str(query) for query in session.queries)
        assert "products.status" in sql and "products.reviewed_at IS NOT NULL" in sql


@pytest.mark.asyncio
async def test_no_profile_or_catalog_is_read_without_active_profile_consent():
    owner_id = uuid4()
    candidate = sample_analysis(owner_id)
    session = FakeSession(candidate, None, consent=False)
    result = await get_recommendations(candidate.id, user_id=owner_id, session=session)
    assert result["status"] == "safety_blocked"
    assert result["blocked_reason"] == "profile_consent_required"
    assert len(session.queries) == 1
    assert "consents.revoked_at IS NULL" in str(session.queries[0])


@pytest.mark.asyncio
async def test_processing_analysis_does_not_read_profile_or_catalog():
    owner_id = uuid4()
    candidate = sample_analysis(owner_id)
    candidate.status = AnalysisStatus.running
    session = FakeSession(candidate, None)
    result = await get_recommendations(candidate.id, user_id=owner_id, session=session)
    assert result["status"] == "pending"
    assert result["recommendations"] == []
    assert session.queries == []


@pytest.mark.asyncio
async def test_completed_endpoint_returns_reviewed_products_when_image_score_is_withheld():
    owner_id = uuid4()
    candidate = sample_analysis(owner_id)
    questionnaire = SimpleNamespace(id=uuid4(), answers={
        "skin_type": "dry", "skin_sensitivity": "low", "known_product_allergy": "no",
        "severe_irritation": "no", "sunscreen_frequency": "every_day",
    })
    sunscreen = Product(
        id=uuid4(), brand="Test catalog", name="Test SPF", variant="", category="sunscreen",
        market="TH",
        status="published", reviewed_at=datetime.now(UTC), price_satang=15900,
        ingredients_label="Aqua", ingredients_inci=["Aqua"], warnings_label="Avoid eyes",
        target_skin_types=["all"], concerns=[], source_url="https://example.com/test-spf",
        spf=50, broad_spectrum=True,
    )
    result = await get_recommendations(candidate.id, user_id=owner_id, session=FakeSession(
        candidate, questionnaire, None, products=[sunscreen],
    ))
    assert result["image_context"]["status"] == "withheld"
    assert result["product_context"]["status"] == "ready"
    product = result["recommendations"][1]["products"][0]
    assert product["id"] == str(sunscreen.id)
    assert product["price_satang"] == 15900
    assert product["warnings_label"] == "Avoid eyes"
