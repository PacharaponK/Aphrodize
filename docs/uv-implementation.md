# UV feature: delivery and operation

Checked 29 September 2026 (Asia/Bangkok). Users can select Bangkok, Songkhla, or Chiang Mai and see today/tomorrow clear-sky UV, WHO-based protection advice, optional noon weather, and source-reviewed sunscreen products.

## Phase 4 decision: observed all-sky UV

| Source | Coverage found | Decision |
| --- | --- | --- |
| [WOUDC public data-record API](https://api.woudc.org/collections/data_records/items?bbox=97,5,101,21&limit=1000&f=json) | 597 records in the Thai bounding box: 538 Bangna Bangkok and 59 Songkhla, all `TotalOzone`; zero UV broadband, multiband, spectral, or UV-index observations. No Chiang Mai record. Reproduce with `python scripts/audit_uv_observations.py`. | Cannot train or validate a three-city cloud correction using these records. Ozone is not an observed UV-index target. |
| [TMD open UV dataset](https://data.go.th/en/dataset/c3-2-1-11) | Publishes a UV **forecast**, not ground measurements. | Cannot use another provider's forecast as the training target or replace our own forecast. |
| [NASA POWER](uv-data-feasibility.md) | Historical satellite/model all-sky values; current feed ended 2026-06-30 in the direct check. | Useful as a separate historical comparison, not current ground truth or a live service. |
| [TEMIS station files](https://temis.nl/uvradiation/UVarchive/stations_uv.php) | Three continuous daily UVIEF series to 2026-09-28. | Local SARIMAX target is **clear-sky UV at solar noon** only. |

Phase 5 (cloud-correction model) is gated off. Open-Meteo supplies weather context but never changes the UV value or protection recommendation. [WOUDC documents its UV dataset types](https://woudc.org/en/data/data-search-and-download/), and [WHO notes that clouds do not reliably remove UV risk](https://www.who.int/news-room/questions-and-answers/item/radiation-ultraviolet-%28uv%29).

## Model and safety gate

SARIMAX with two annual Fourier harmonics is fitted locally. Locked two-day clear-sky test MAE: Bangkok **0.3309**, Songkhla **0.2819**, Chiang Mai **0.3482** UVI; each beats the persistence baseline. Details and threshold errors are in [the evaluation notebook](../models/time-series/uv/uv_model_evaluation.ipynb) and [the data report](uv-data-feasibility.md). **This does not establish all-sky or ground-level accuracy.**

[WHO UVI thresholds](https://www.who.int/news-room/questions-and-answers/item/radiation-the-ultraviolet-%28uv%29-index) determine low (<3), moderate (3–5), high (6–7), very high (8–10), and extreme (11+). At 8+, the app advises avoiding midday sun; at 3–7, seeking midday shade. Sunscreen guidance remains broad-spectrum SPF 30+, applied generously and reapplied at least every two hours outdoors. These rules do not relax for cloud cover. [WHO protection guidance](https://www.who.int/news-room/questions-and-answers/item/radiation-protecting-against-skin-cancer).

Only published, reviewed sunscreen records with a source URL, SPF ≥30, and stated UVA/UVB coverage appear. The starter catalog contains [CeraVe SPF 50](https://www.cerave.co.th/skincare/facial-moisturising-lotion-spf-50) and [CeraVe SPF 30](https://www.cerave.co.th/skincare/facial-moisturising-lotion-spf-30), whose manufacturer pages list SPF, broad-spectrum protection, skin type, and ingredients. No price or water-resistance duration is inferred. Formulas can change; recheck the packaging before use. The catalog is illustrative, not a ranking or claim of suitability for every person.

## Run and verify

From the repository root:

```powershell
docker compose up -d --build api uv-refresh
docker compose exec -T api python /app/scripts/seed_uv_products.py
```

The refresh service downloads raw TEMIS data, trains local models on first run if artifacts are absent, updates existing model state with new days, requests only cloud/rain weather fields from Open-Meteo, and atomically writes `storage/artifacts/uv/forecast_snapshot.json` every six hours. A failed refresh retries after 30 minutes. The API serves `/api/v1/uv/recommendation?city=bangkok` with Basic authentication. The Next.js server proxy protects credentials; `/recommendation` is the user page. A missing weather response leaves weather null without blocking UV. Missing or stale TEMIS data, a snapshot older than eight hours, or dates beyond the evaluated horizon returns 503. Generated files under `storage/` stay outside Git.

For local checks:

```powershell
.venv/Scripts/python.exe -m pytest tests/test_uv_service.py tests/test_products.py -q
.venv/Scripts/ruff.exe check backend/api/schemas/product.py backend/api/v1/router.py backend/api/v1/routes/products.py backend/api/v1/routes/uv.py backend/core/db/models.py backend/core/db/session.py backend/services/uv_service.py scripts/refresh_uv_forecast.py scripts/seed_uv_products.py scripts/audit_uv_observations.py tests/test_uv_service.py
cd frontend
pnpm lint
pnpm exec tsc --noEmit
pnpm build
```

On 2026-09-29, the complete Python suite passed (**125 tests**), the changed Python files passed Ruff, and Next lint, TypeScript, and production build passed. The running API and Next proxy returned two dated values plus two reviewed products for each of the three cities. A whole-repo Ruff run still reports unrelated existing errors in `backend/services/passwords.py` and several older tests. Browser automation could not start because the local Windows automation helper failed; the live HTTP routes and production build were verified instead.

## Monitoring, retraining, and rollback

- Check `docker compose logs uv-refresh` after each six-hour run. The script logs the newest TEMIS date, source SHA-256, weather availability, and snapshot publication without credentials or personal data.
- Watch the authenticated `/api/v1/monitoring/uv` endpoint, the snapshot's `generated_at`, each city's `data_date`, and the API's 503 response. Investigate if no fresh snapshot appears for eight hours or TEMIS lags more than one day.
- Once independent observed UV becomes available for all three cities, first lock an unseen time split and evaluate cloud correction against the present SARIMAX and persistence baselines. Do not call all-sky accuracy validated before that study.
- To replace the clear-sky model, rerun `python scripts/train_uv_model.py` and `python scripts/evaluate_uv_model.py`. Compare each city's two-day MAE and UV ≥8/≥11 undercall counts to the recorded version. Keep the prior three `.pkl` files and snapshot for rollback before replacing them. Do not automatically deploy a candidate that worsens the protection gate.
