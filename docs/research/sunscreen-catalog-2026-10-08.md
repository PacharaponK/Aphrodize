# Expanded sunscreen catalog — 8 October 2026 (Asia/Bangkok)

Eight additional exact manufacturer variants expand the UV catalog from three to eleven products. These are US-market formulas, explicitly labeled as such in the UV dialog; availability or equivalent composition in Thailand is not inferred. No Thai prices or purchase availability are invented. Full active/inactive ingredient snapshots and exact image URLs are retained in `backend/fixtures/sunscreens-2026-10-08.yaml`.

SPF, broad-spectrum status, skin-type claims, sensitive-skin wording and water resistance were checked against each linked manufacturer page. All eight image URLs returned HTTP 200 with an image content type. The reviewed timestamp records this source check; it is not a clinical review or an allergy guarantee. Actual package labeling takes precedence if formulas change.

| Product / exact variant | Skin-type label used | Water resistance | Type / use | Manufacturer evidence |
|---|---|---|---|---|
| Cetaphil Sheer Mineral Sunscreen Lotion SPF 50 / 3 fl oz / 89 ml | all; explicit sensitive-skin claim | 80 minutes | mineral | [Product label](https://www.cetaphil.com/us/products/product-categories/sunscreens/sheer-mineral%2A-sunscreen-lotion-spf-50/302994122004.html) |
| Cetaphil Sheer Mineral Sunscreen Face Drops SPF 50 / 1 fl oz / 30 ml | all; explicit sensitive-skin claim | 80 minutes | mineral | [Product label](https://www.cetaphil.com/us/products/product-categories/sunscreens/sheer-mineral%2A-sunscreen-face-drops-spf-50/302994110001.html) |
| Cetaphil DermaControl Oil Absorbing Moisturizer SPF 30 / 4 fl oz / 118 ml | oily; explicit sensitive-skin claim | Not verified; excluded from sports/swimming | oil-control | [Product label](https://www.cetaphil.com/us/products/product-categories/all-moisturizers/dermacontrol-oil-absorbing-moisturizer-spf-30/302994313044.html) |
| Cetaphil Daily Facial Moisturizer SPF 50 / 1.7 fl oz / 50 ml | normal, dry; explicit sensitive-skin claim | Not verified; excluded from sports/swimming | hydrating | [Product label](https://www.cetaphil.com/us/products/product-categories/all-moisturizers/daily-facial-moisturizer-spf-50/302993930020.html) |
| La Roche-Posay Anthelios Clear Skin Oil Free Sunscreen SPF 60 / 90 ml | normal, oily, combination; explicit sensitive-skin claim | 80 minutes | oil-control | [Product label](https://www.laroche-posay.us/our-products/sun/face-sunscreen/anthelios-clear-skin-oil-free-sunscreen-spf-60-antheliosclearskin.html) |
| La Roche-Posay Anthelios Melt-In Milk Sunscreen SPF 60 / 150 ml | all; explicit sensitive-skin claim | 80 minutes | hydrating | [Product label](https://www.laroche-posay.us/our-products/sun/body-sunscreen/anthelios-melt-in-milk-sunscreen-spf-60-antheliosmeltinmilk.html) |
| La Roche-Posay Anthelios Ultra Light Fluid Facial Sunscreen SPF 60 / 50 ml | all; explicit sensitive-skin claim | 80 minutes | light-fluid | [Product label](https://www.laroche-posay.us/our-products/sun/face-sunscreen/anthelios-ultra-light-fluid-facial-sunscreen-spf-60-883140012993.html) |
| CeraVe Hydrating Mineral Sunscreen SPF 30 Face Sheer Tint — Medium / 1.7 fl oz / 50 ml | all; explicit sensitive-skin claim | Not verified; excluded from sports/swimming | mineral, tinted, hydrating | [Product label](https://www.cerave.com/sunscreen/face/hydrating-mineral-sunscreen-spf-30-face-sheer-tint-medium) |

Sensitive skin is a separate reviewed concern, stored as `concerns: [sensitive-skin, ...]`, rather than a new generic skin type. `/api/v1/uv/products` exposes `suitable_for_sensitive_skin` only when that explicit tag exists. An all-skin-types label alone never enables the sensitive filter. The five 80-minute products meet the existing sports/swimming gate, including dry skin through their explicitly all-type labels; no minute value is inferred from a generic water-resistant claim. Daily Facial Moisturizer SPF 50 uses the narrower dry/normal recommendation in the manufacturer's Features section. CeraVe tint is specifically Medium, contains salicylic-acid derivatives, and retains its package caution in `warnings_label`; no shade matching is inferred.

The existing UV display preference (SPF 50+ at UV ≥8) and five-result maximum remain. The new SPF 30 products can appear for lower UV or when no SPF 50 product passes the user's mandatory filters. This is a UI selection rule, not a clinical superiority ranking.

Import only products through the existing validated fixture service (`load_products`): identity is source URL plus variant, so rerunning does not duplicate products or overwrite edited/archived rows. User accounts and profiles are not part of this import. No status or label on an existing product is changed.

```sh
docker compose exec -T api python -m backend.scripts.load_fixtures /app/backend/fixtures/sunscreens-2026-10-08.yaml --products
```

The fixture must be present in the API image. The published importer validates the whole batch before adding rows; the existing publishability requirements remain enforced.

## Delivered verification

Published all eight additions on the live site; public UV catalog now has eleven items, five with explicit 80-minute water resistance. Both application containers and standard deployment readiness/HTTPS checks passed. Python catalog/import checks passed (including repeatability and preserving archived edits); frontend UV tests, lint, TypeScript and production build passed. Chromium verified 20 skin/activity combinations against the actual catalog, all eleven product photos loading, US-market formula text, and Thai mobile dark-mode layout without JavaScript exceptions or horizontal overflow. Dry sports/swimming has four matches; other tested combinations have five displayed matches under the existing cap. Deployment was built from the current live API/frontend images to preserve concurrent unrelated fixes.
