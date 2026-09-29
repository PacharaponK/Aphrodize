# UV data feasibility — phase 1

Checked on **29 September 2026 (Asia/Bangkok)** for Bangkok (13.7563, 100.5018), Songkhla (7.1898, 100.5954), and Chiang Mai (18.7883, 98.9853). This phase checks public data access and completeness; it does not measure forecast accuracy.

| Source | Direct download result | Latest valid date | What the UV value means | Phase-1 decision |
| --- | --- | --- | --- | --- |
| [NASA POWER](https://power.larc.nasa.gov/docs/services/api/temporal/hourly/) `ALLSKY_SFC_UV_INDEX` | HTTP 200 without an account for all three places. In 2025, hourly valid values were 8,759/8,760 (Bangkok) and 8,760/8,760 (Songkhla and Chiang Mai). | **2026-06-30 23:00 UTC** for all three places. Every hourly response from 2026-07-01 through 2026-09-28 is `-999`. The daily endpoint ends on **2026-06-29**. | All-sky, satellite/model-derived UV index; hourly values could be grouped by local date for a daily peak. | Useful historical reference, **unsuitable as the current UV feed**. The observed gap is about three months, despite the [general POWER solar-data estimate of 5–7 days](https://registry.opendata.aws/nasa-power/). |
| [TEMIS operational station series](https://temis.nl/uvradiation/UVarchive/stations_uv.php) `UVIEF` | HTTP 200 without an account. Each city file has 8,856 daily rows from 2002-07-01 through 2026-09-28. All 271 dates in 2026 through 2026-09-28 have valid `UVIEF` values in all three cities. | **2026-09-28** for all three places. | **Clear-sky** erythemal UV index at local solar noon, on a 0.25° grid. Cloud-modified UV fields for these Thai locations are unavailable (`-1`). | Viable current data for a model of **clear-sky UV potential**, not observed all-sky UV. |
| [Open-Meteo weather forecast](https://open-meteo.com/en/docs) | HTTP 200 without an account. All three cities returned 48 hourly cloud-cover values in `Asia/Bangkok`, including all 24 hours of 2026-09-30. The [historical forecast endpoint](https://open-meteo.com/en/docs/historical-forecast-api) also returned a 2025 sample. | Forecast for **2026-09-30** was present at check time. | Forecast cloud cover, not a UV observation. | Viable weather input. Do not request Open-Meteo's ready-made UV forecast for this project. |

## Reproduce the source checks

- NASA POWER hourly example (Bangkok): `https://power.larc.nasa.gov/api/temporal/hourly/point?parameters=ALLSKY_SFC_UV_INDEX&community=RE&longitude=100.5018&latitude=13.7563&start=20260625&end=20260928&format=JSON&time-standard=UTC`. Treat `-999` as missing. Its daily endpoint was checked separately and must not be treated as a daily maximum without confirming the aggregation definition.
- TEMIS city files: [Bangkok](https://d1qb6yzwaaq4he.cloudfront.net/uvradiation/v2.0/overpass/uv_Bangkok_Thailand.dat), [Songkhla](https://d1qb6yzwaaq4he.cloudfront.net/uvradiation/v2.0/overpass/uv_Songkhla_Thailand.dat), [Chiang Mai](https://d1qb6yzwaaq4he.cloudfront.net/uvradiation/v2.0/overpass/uv_Chiang_Mai_Thailand.dat). Ignore `#` lines; split data lines on whitespace. Column 1 is `YYYYMMDD`, column 2 is `UVIEF`, and `-1` means missing. The file header defines all columns.
- Open-Meteo example (Bangkok): `https://api.open-meteo.com/v1/forecast?latitude=13.7563&longitude=100.5018&hourly=cloud_cover,cloud_cover_low,cloud_cover_mid,cloud_cover_high&forecast_days=2&timezone=Asia%2FBangkok`. Only cloud and weather fields were requested.

## Repository fit

- There is no deployed generic time-series model yet (`README.md`). The UV model needs its own trained artifact and integration in a later phase.
- The product schema already supports a `sunscreen` category (`backend/api/schemas/product.py`), while the current recommendation in `backend/services/analysis_service.py` is general guidance tied to image-analysis eligibility. A location-based UV recommendation needs a separate input and safety path.
- The current product-scope document does not include this environmental UV forecast. Update its scope and acceptance criteria when implementing the feature; do not imply a forecast of treatment outcomes.

## Decision for phase 2

Start with the three TEMIS `UVIEF` series as the timely prediction target, and label every forecast **clear-sky UV potential**. Use weather forecasts to explain cloud conditions separately. NASA POWER can support historical comparison and a later, explicitly validated cloud-correction model; its current gap prevents using it as the live all-sky target. Before showing any numeric cloud-adjusted UV estimate to users, test that estimate against independent all-sky observations. Keep the source date and forecast date visible in the app.

## Phase 2 — prepared dataset (29 September 2026)

Run `python scripts/prepare_uv_dataset.py` from the repository root. The script downloads the three public TEMIS files, verifies the `UVIEF` column definition and 17-column rows, rejects duplicate or skipped dates and invalid values, and writes `storage/data/uv/temis_clear_sky_uv.csv`. The local CSV is gitignored and can be regenerated without an account or a forecast-model API. Its columns are `date`, `city`, `uv_index_clear_sky`, and `uv_index_uncertainty`; a TEMIS `-1` becomes an empty CSV field rather than an invented UV value.

| City ID | Daily rows | Date range | Missing days | Missing `UVIEF` | `UVIEF` range |
| --- | ---: | --- | ---: | ---: | ---: |
| `bangkok` | 8,856 | 2002-07-01 to 2026-09-28 | 0 | 0 | 7.708–16.187 |
| `songkhla` | 8,856 | 2002-07-01 to 2026-09-28 | 0 | 0 | 9.327–16.866 |
| `chiang_mai` | 8,856 | 2002-07-01 to 2026-09-28 | 0 | 0 | 6.101–15.882 |

The combined file has **26,568 data rows** (SHA-256 `9e047b625710219f051161c82c390ccc5a3287964cd7cbed016868835859b04a`). The downloaded source SHA-256 values, in city order above, are `12db307eb3fdf8b09330889ac7ba28e03b4b9b6e126777d79944c8c5126fd6a1`, `8b3c91e68d8522757a184eec19cbec9537b6c679c721bbfb52c524a709c81abc`, and `29bdf2cee0e1dde7b841cfd76b732ab4bd2a5ef5929b73adfd0a96071a31d6cf`. TEMIS updates its files, so later runs may have different row counts and hashes. The source hash identifies the data used here; the source files themselves are not archived in this repository.

For the next phase, split **by date within each city**: train through 2023-12-31, validate on 2024, and reserve 2025-01-01 onward for final testing. Compare a seasonal baseline with a locally fitted SARIMAX model. Use only information available by each forecast date when backtesting. Cloud cover is not a predictor of this clear-sky target; forecast weather can be displayed as separate context until a cloud-adjusted model is independently validated.

Check the parser with `python -m unittest discover -s tests -p test_prepare_uv_dataset.py -v`.

## Phase 3 — local model training and backtest (29 September 2026)

Run `python scripts/train_uv_model.py` after preparing the CSV. This fits a separate SARIMAX to each city **on this machine** using `statsmodels`; no external forecast-model API is called. The target remains TEMIS clear-sky UV at local solar noon. Four known-in-advance annual sine/cosine terms (two harmonics, 365.2425-day period) represent seasonality; SARIMAX models the remaining day-to-day correlation. The four candidate orders are `(1,0,0)`, `(2,0,0)`, `(3,0,0)`, and `(1,0,1)`.

Parameters are fitted on data through 2023-12-31, and the candidate with the lowest **two-day validation MAE** in 2024 is selected per city. The selected order is refitted through 2024-12-31 and tested once on 2025-01-01 through 2026-09-28. Rolling predictions use only values observed through each forecast origin. A two-day forecast is evaluated from 2025-01-02 onward (635 target days), which matches the case where today's latest TEMIS value is from yesterday and tomorrow is two days ahead of that observation. After evaluation, the selected order is fitted to all available observations for a local model artifact.

| City | Selected order | Validation two-day MAE | Test two-day MAE | Test two-day persistence MAE | Test previous-year MAE |
| --- | --- | ---: | ---: | ---: | ---: |
| Bangkok | `(1,0,1)` | 0.3229 | **0.3309** | 0.3938 | 0.6195 |
| Songkhla | `(1,0,1)` | 0.3095 | **0.2819** | 0.3451 | 0.7501 |
| Chiang Mai | `(1,0,1)` | 0.3600 | **0.3482** | 0.4129 | 0.5704 |

MAE is in UV-index units; lower is better. Persistence repeats the value available at the forecast origin, while the seasonal baseline repeats the same calendar date from the preceding year (28 February for leap day). The selected SARIMAX beats both baselines on this held-out period in all three cities. This comparison tests **clear-sky UV potential**, not cloud-affected ground-level UV or the quality of sunscreen recommendations.

The script saves `storage/models/uv/{city}.pkl`, `storage/artifacts/uv/metrics.json`, and `storage/artifacts/uv/backtest_predictions.csv` locally; these generated files are gitignored. The metrics file records candidate scores, selected orders, library version, and source CSV SHA-256. With source observations ending 2026-09-28, the fitted models' example forecasts for **2026-09-30** are Bangkok **11.577**, Songkhla **12.366**, and Chiang Mai **11.373** clear-sky UVI. Refreshing TEMIS data and retraining changes these numbers. All three saved models were reloaded and reproduced these forecasts. Run the focused checks with `python -m unittest discover -s tests -p 'test_*uv*.py' -v`.

The next phase can expose city selection, a dated forecast, weather context, and sunscreen guidance. Show the forecast as clear-sky potential; cloud cover must not be used as an unvalidated numeric correction. Add a freshness check before serving forecasts so a delayed TEMIS update does not silently turn tomorrow into a longer-range prediction.

## Phase 3 evaluation gate — before app integration

Run `python scripts/evaluate_uv_model.py` after training. It reads the locked 2025–2026 test predictions and checks the source checksum, sample count, and reported MAE. It audits two-day forecasts on **635 target dates per city**. The 95% ranges below come from 2,000 paired 14-day moving-block resamples of daily absolute-error improvement over persistence. They describe uncertainty within this historical test period, not a guarantee for future days.

| City | Test MAE | 90th-percentile absolute error | MAE gain vs persistence (95% block range) | Months beating persistence | Under-called UV ≥8 | Under-called UV ≥11 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Bangkok | 0.3309 | 0.6838 | 0.0629 (0.0429–0.0820) | 11/12 | 0/635 | 3/492 |
| Songkhla | 0.2819 | 0.5758 | 0.0632 (0.0492–0.0776) | 12/12 | 0/635 | 5/609 |
| Chiang Mai | 0.3482 | 0.7386 | 0.0647 (0.0440–0.0852) | 11/12 | 9/578 | 2/447 |

For the threshold audit, predicted and target values are rounded to the nearest whole UVI before comparing with 8 and 11. These are the [WHO action and exposure-category boundaries](https://www.who.int/news-room/questions-and-answers/item/radiation-the-ultraviolet-%28uv%29-index) ([11+ category and whole-number reporting in the WHO practical guide](https://iris.who.int/bitstream/handle/10665/42459/9241590076.pdf)). An *under-call* means the target reached the threshold but the forecast did not. All targets here are TEMIS **clear-sky** values. The largest individual absolute error was 2.2057 UVI in Bangkok on 2025-09-14 (target 14.911, forecast 12.705).

**Decision:** The locally trained SARIMAX passes this held-out point-forecast comparison against both simple baselines for clear-sky UV. The threshold misses and lack of independent cloud-affected, ground-level UV observations prevent claiming that its risk level or product advice is validated for actual outdoor exposure. Before release, evaluate a conservative recommendation rule against these under-calls; any numeric cloud correction also needs separate validation against all-sky observations. A prototype may show a dated, explicitly labeled clear-sky forecast while that work continues. Detailed results are in the ignored local file `storage/artifacts/uv/evaluation.json`.

The executed notebook `models/time-series/uv/uv_model_evaluation.ipynb` contains the validation selection table, held-out score table, threshold audit, and four plots (baseline comparison, recent actual vs forecast, monthly MAE, and residual distribution/scatter). It reuses matching local artifacts or runs the data preparation and training scripts when needed. Install the project's development dependencies to run its Python kernel and Matplotlib plots.
