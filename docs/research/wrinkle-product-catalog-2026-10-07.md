# Expanded Thai wrinkle-care catalog — 7 October 2026

This import adds 11 cosmetic wrinkle-care products to the existing 18-product catalog. Complete source ingredient lists, application permission, skin-type claims, direct Thai purchase links, observed prices and product photos are recorded below. The `treatment` category denotes their cosmetic wrinkle-care role; it does not denote a medicinal treatment.

Two researched Paula's Choice candidates are **excluded from this import**: Pro-Collagen Multi-Peptide Booster uses the undecomposed blend name SYN-TC, and CellularYouth lists Goji Fruit Extract without precise botanical INCI. The face research below documents these candidates for provenance only; the machine-readable import contains only the other three Paula's Choice face products. The Ordinary and COSRX products omitted by one researcher for image access were subsequently resolved by the additional face research and are included.

## Application and selection

Reviewed eye-contour labels may match the left/right periocular image regions. Reviewed face labels may match forehead, glabella, cheeks, nasolabial and perioral regions, excluding direct contact with eyes and mucosa. A face label is not a claim of separately proven efficacy for each region. Existing release gates, area thresholds, age rules, sensitivity and allergy exclusions continue to apply. Exact skin-type matches rank ahead of all-type products; the existing matcher returns at most three products per recommendation. A budget filters only products with sourced prices checked within 30 days.

## Reproduce the product-only import

```sh
docker compose exec -T api python -m backend.scripts.load_fixtures --products /app/backend/fixtures/wrinkle-products-2026-10-07.yaml
```

The file must be included in the deployed API image or copied into that path first. `load_products` validates the entire batch, identifies exact variants by source URL plus variant, and preserves existing catalog edits. No user fixtures or profile changes are part of this import.

## Eye-contour product snapshot — 2026-10-07 (Asia/Bangkok)

Five non-retinoid eye products use the catalog treatment category for their explicitly described cosmetic wrinkle-care role (not a medical treatment). They were reviewed for `backend/fixtures/wrinkle-products-2026-10-07.yaml`. These are cosmetic care labels, not a promise that creams remove facial expression wrinkles. INCI is a dated source snapshot: actual package labeling must prevail. No ingredient list was assembled from highlighted actives alone. Prices are page snapshots and can vary with promotions. Shopping links were read; image URLs were extracted from their real product links/variant metadata. Initial browsing-tool image fetches returned cache misses; the final runtime verification fetched all included product images successfully as HTTP 200 image/jpeg.

| Product | Skin types | Price shown | INCI provenance |
|---|---|---:|---|
| Vichy Mineral 89 Eyes Serum 15 ml | All, including sensitive | THB 950 | Thai manufacturer |
| Curél Moisture Repair Eye Cream 25 g | Dry | THB 820 | Thai Watsons full ingredient list |
| Eucerin Hyaluron-Filler + Elasticity Eye SPF20 15 ml | All | THB 1,462 | Thai Watsons full ingredient list |
| Paula's Choice Pro-Collagen Peptide Firming Eye Serum 15 ml | Dry, combination, normal, oily | THB 1,550 | Thai official brand store |
| Paula's Choice C5 Super Boost Eye Cream 15 ml | Combination, dry | THB 1,650 | Thai official brand store |

### Vichy

[Thai manufacturer](https://www.vichy-th.com/all-products/skincare/mineral-89/mineral-89---eyes-gel) explicitly supports all skin types and fragrance-free status, describes eye wrinkles and hydration, and provides the complete 13-entry ingredient list. The gentle concern tag is omitted because suitability for sensitive skin alone does not establish that wording. [Watsons product](https://www.watsons.co.th/en/vichy-vichy-mineral89-eyes-serum-15ml/p/BP_281998) corroborates those uses and shows THB 950. [Image](https://medias.watsons.co.th/publishing/WTCTH-281998-front-zoom.jpg?version=1733713620) was followed from its product image link.

### Curél

[Watsons Thailand](https://www.watsons.co.th/en/curel-curel-intensive-moisture-care-moisture-repair-eye-cream-25g/p/BP_293393) lists 22 INCI entries, THB 820, and care for dry, rough, sensitive eye skin. [Manufacturer product](https://www.curel.com/en-gb/products/moisture-repair-eye-cream/) identifies dry sensitive skin, fragrance-free status and fine lines associated with dryness. The Thai retailer explicitly describes gentle moisturizing, supporting the gentle tag. Its displayed INCI differs from the Thai retailer list: this fixture deliberately retains the full Thai retailer formulation, including allantoin and ginger extract, and does not merge them. The wrinkle-care label refers to cosmetic smoothing through hydration. [Thai retailer image](https://medias.watsons.co.th/publishing/WTCTH-293393-front-zoom.jpg?version=1733772743) is the actual image link; initial browsing-tool image fetch returned cache miss; final runtime verification returned HTTP 200 image/jpeg.

### Eucerin

[Thai manufacturer](https://www.eucerin.co.th/products/hyaluron-filler-plus-elasticity/eye-cream-spf20) supports the eye use and wrinkle claim. The manufacturer's [SPF20 product page](https://images-us.eucerin.com/eucerin%20relaunch/home/products/hyaluron-filler-plus-elasticity/eye-care) is titled for all skin types and explicitly states fragrance-free and non-comedogenic. [Watsons Thailand](https://www.watsons.co.th/en/eucerin-eucerin-hyaluron-filler-elasticity-eye-cream-spf20-15-ml./p/BP_302357) provides the entire 36-entry formula and THB 1,462. Use the Thai formula, not the newer UK eye formula with Thiamidol. This product uses the catalog treatment category because its explicit cosmetic role is wrinkle care; the category does not imply a medicine. SPF20 does not satisfy the recommendation system's SPF30+ sunscreen role, and the fixture warning calls for additional facial sunscreen. [Image](https://medias.watsons.co.th/publishing/WTCTH-302357-front-zoom.jpg?version=1733814906) was followed from its retailer image link.

### Paula's Choice Pro-Collagen

[Thai official brand store](https://paulaschoice.th/en/products/pro-collagen-peptide-firming-eye-serum) provides full INCI, all four supported skin categories, fragrance-free status, eye-area application, and a THB 1,550 price for 15 ml. The SKU 1080 variant is listed as available. It targets eye-area fine lines and crow's feet. The gentle tag is omitted: gentle application directions and suitability for sensitive skin are not an explicit gentle-formula claim. Minor formatting was normalized only: `1, 2-Hexanediol` becomes `1,2-Hexanediol`; adjacent INCI paragraphs are joined without adding ingredients. [15 ml product image](https://paulaschoice.th/cdn/shop/files/pro-collagen-peptide-firming-eye-serum-15ml.jpg?v=1770105477) comes directly from the variant's featured image metadata. Avoid the lash line and direct eye contact; apply sunscreen for daytime use.

### Paula's Choice C5

[Thai official brand store](https://paulaschoice.th/en/products/c5-super-boost-eye-cream) provides full INCI, combination and dry/very dry skin categories, fragrance-free status, THB 1,650 for 15 ml, and an available SKU 1010. The 5 ml size was unavailable and was excluded. Word-joiner formatting characters from the ingredient list are removed only; ingredient spellings are retained. [15 ml image](https://paulaschoice.th/cdn/shop/files/c_-c5-super-boost-eye-cream-15ml.jpg?v=1749111348) is the variant's actual featured image. Manufacturer directions restrict application to under-eye skin, avoiding the lash line, and call for SPF30+ in the daytime.

### Candidates omitted

- Existing Eucerin Hyaluron (3X) Filler Eye SPF15: duplicate.
- Plantnery Cica Centella Ceramide Eye Cream: only highlighted ingredients were available at the reviewed retailer; insufficient full INCI for allergy filtering.
- Hada Labo Intensive Revitalizing Eye Essence Cream: contains Retinyl Palmitate; omitted to keep this batch non-retinoid.
- Her Hyness Royal Lift White Anti-Wrinkle Eye Cream: complete [manufacturer INCI](https://www.herhynessbeauty.com/en/products/royal-lift-white-anti-wrinkle-eye-cream-15-ml) and all-skin/fragrance-free claims were found, but the official store was sold out. Not added while available alternatives cover the same need.
- Bioderma Sensibio Eye / Atoderm Intensive Eye: could not establish a current Thai retailer variant and complete matching ingredient evidence during this review.

## Face wrinkle-care catalog review — 7 October 2026

Five non-retinoid entries use the Thai official Paula's Choice store for product claims, the complete ingredient list as published, current purchase links, product image URLs and price snapshots. Availability is the store's captured `available: true`, not a guarantee of stock at checkout. Category `treatment` represents the Aphrodize wrinkle-care role, including the peptide gel cream.

| Product | Official source / purchase page | Snapshot price | Supported mapping |
|---|---|---:|---|
| Pro-Collagen Multi-Peptide Booster | [Thai official store](https://paulaschoice.th/en/products/pro-collagen-multi-peptide-booster) | THB 2,250 / 20 ml | All types; expressly suitable for sensitive skin; lightweight; face, eye area and neck; wrinkles and crow's feet |
| Pro-Collagen Peptide Plumping Moisturizer | [Thai official store](https://paulaschoice.th/en/products/pro-collagen-peptide-plumping-moisturizer) | THB 1,665 / 50 ml | All four specified types; especially normal, oily and combination; sensitive-skin FAQ; face and neck; expression lines |
| CALM Repairing Serum | [Thai official store](https://paulaschoice.th/en/collections/extra-sensitive-skin/products/calm-repairing-serum) | THB 1,700 / 30 ml | All types; explicit gentle, sensitive-skin and visibly smooths wrinkles claims; face, neck and eye area |
| Hyaluronic Acid Booster | [Thai official store](https://paulaschoice.th/en/collections/shop-all-copy/products/hyaluronic-acid-booster) | THB 1,440 | All four types explicitly listed; face and under-eye; fine lines and wrinkles; no `gentle` tag inferred solely from fragrance absence |
| CellularYouth Age-Disrupting Longevity Serum | [Thai official store](https://paulaschoice.th/en/products/cellularyouth-age-disrupting-longevity-serum) | THB 3,000 | All types; lightweight; face and neck; fine lines and wrinkles. FAQ expressly says no fragrance. |

Every entry has an explicit manufacturer fragrance-free statement. `gentle` is added only where the manufacturer directly supports gentleness or sensitive-skin suitability. Face placement supports facial zones at the catalog level, without inventing separately tested forehead, glabella or nasolabial efficacy. Eye-contour permission follows explicit directions. These are cosmetic manufacturer claims, not independent efficacy verification.

### Ingredient fidelity and limitations

Source-order ingredient lists are preserved. Non-ingredient explanatory parentheses in the Hyaluronic Acid Booster list are removed; `1, 2-Hexanediol` is normalized to `1,2-Hexanediol` so the internal comma remains one ingredient. The booster source publishes `SYN-TC`, a proprietary blend name, without decomposing it into INCI constituents. CellularYouth publishes `Goji Fruit Extract`, rather than a botanical INCI expansion. These labels are retained without guessed constituents. Consequently those two source lists are complete as published but do not establish all constituents of named blends. A package-label check is needed before claiming fully resolved blend-level allergen screening.

Product images come from the official store's actual product media. Booster, gel cream, CALM and Hyaluronic Booster URLs were exposed in Shopify variant metadata; the CellularYouth image URL was resolved from its linked product photograph. Older photo alt text mentioning Malaysia appears on the Thai store for Hyaluronic Booster; this is not used as evidence for a different formula.

### Omitted candidates

- [Omega+ Complex Serum](https://paulaschoice.th/en/products/resist-omega-complex-serum): explicit dry-skin and fine-line/wrinkle claims and fragrance-free, but captured 30 ml SKU is sold out (`available: false`); omitted from import.
- [Ultra-Light Super Antioxidant Concentrate Serum](https://paulaschoice.th/en/products/resist-ultra-light-super-antioxidant-concentrate-serum): explicit oily/combination placement, wrinkle claims and fragrance-free, but captured 30 ml and 5 ml SKUs are sold out; omitted from import.
- [Eucerin Epicelline Serum](https://www.eucerin.co.th/products/hyaluron-filler-plus-longevity/epigenetic-serum): current Thai manufacturer page provides wrinkle claims and application directions but no complete ingredient list in accessible content; not combined with a guessed or older-country formula.
- [The Ordinary Multi-Peptide + HA Serum at Watsons](https://www.watsons.co.th/th/the-ordinary-ดิ-ออดินารี-มัลติ-เปปไทด์-เอชเอ-เซรั่ม-30-มล./p/BP_325259): THB 1,070 and full formula matching [manufacturer](https://theordinary.com/en-us/multi-peptide-ha-serum-100613.html); retailer product image links could not be resolved through the browsing tool, so omitted rather than constructing an image URL. Manufacturer [scientific-proof page](https://theordinary.com/en-nz/scientific-proof-skincare.html) states it does not use fragrance in its formulations.

No stock-price monitor is introduced. Check labels and retailer pages before purchase.

## Additional face wrinkle products, reviewed 7 October 2026 (Asia/Bangkok)

Three non-retinoid products in `backend/fixtures/wrinkle-products-2026-10-07.yaml`. No import performed by this research task. Product claims are cosmetic manufacturer claims, not evidence that every wrinkle or user will respond. Regions are conservatively `face`: manufacturer application directions support the face, not eyelid application. The Ordinary HA's crow's-feet claim does not itself establish eye-contour application instructions.

| Product | Manufacturer evidence | Thai label, price, purchase evidence |
| --- | --- | --- |
| The Ordinary Multi-Peptide + HA Serum 30 ml | [Manufacturer](https://theordinary.com/en-us/multi-peptide-ha-serum-100613.html): all skin types, appearance of fine lines and crow's feet, face AM/PM; 51 INCI ingredients match Thai retailer in order | [Watsons BP_325259](https://www.watsons.co.th/en/the-ordinary-the-ordinary-multi-peptide-ha-serum-int-30-ml./p/BP_325259): 1,070 THB, Add to Bag, full INCI, Thai notification 10-2-6700024690 |
| The Ordinary Multi-Peptide + Copper Peptides 1% Serum 30 ml | [Manufacturer](https://theordinary.com/en-us/multi-peptide-copper-peptides-1-serum-100625.html): all skin types, appearance of fine lines, firmness, face AM/PM, oil-free; 49 INCI match Thai retailer in order | [Watsons BP_320285](https://www.watsons.co.th/en/the-ordinary-the-ordinary-multi-peptide-copper-peptides-1-serum-30-ml./p/BP_320285): 1,710 THB, Add to Bag, full INCI, Thai notification 10-2-6700026291 |
| COSRX The 6 Peptide Skin Booster Serum 150 ml | [Manufacturer](https://www.cosrx.com/products/the-6-peptide-skin-booster-serum-bundle): single 150 ml among bundle choices, all types including sensitive/acne-prone, fine lines, lightweight, non-comedogenic test and gentle claim; directions pat on face | [Watsons BP_311042](https://www.watsons.co.th/en/cosrx-cosrx-the-6-peptide-skin-booster-serum-150-ml./p/BP_311042): 649 THB, Add to Bag, full INCI, Thai notification 10-2-6600032411 |

The COSRX manufacturer lists the same 44 ingredients but in a different order, placing peptide ingredients earlier. We preserve the Thai retailer's ingredient order, rather than claiming the global formulation/order is identical. Watsons has a stray comma between `Ammonium Acryloyldimethyltaurate/VP` and `Copolymer`; this is one ingredient, corroborated by the manufacturer's intact INCI name. Case differences SH/sh, T/t and HCL/HCl do not add or remove ingredients. The warning explicitly tells users to check the actual package. The default manufacturer single-product URL redirects to the bundle URL, which still contains single-product directions, ingredients and skin-type evidence.

No fragrance-free tag was assigned: the reviewed manufacturer pages did not explicitly claim it. All types is a manufacturer claim, not a guarantee against irritation. No additional oily/dry/sensitive eligibility is inferred from ingredient functions. Oil-free is recorded only for Copper Peptides, where explicitly stated.

Manufacturer incompatibility warnings are retained. HA should not be layered in the same routine with direct acids/direct vitamin C/resveratrol/ferulic acid/salicylic acid. Copper Peptides additionally excludes retinoids, EUK and strong antioxidants. Both manufacturers advise patch testing and use on unbroken skin. The fixture also advises avoiding direct eye contact.

### Images

URLs were extracted by clicking the actual retailer product gallery links; none were constructed from guessed product IDs. HA image retrieval returned a cache miss but exposed the exact retailer-linked URL. Copper and COSRX image links resolved.

- [HA front image](https://medias.watsons.co.th/publishing/WTCTH-325259-front-zoom.jpg?version=1771009859)
- [Copper front image](https://medias.watsons.co.th/publishing/WTCTH-320285-front-zoom.jpg?version=1754940006)
- [COSRX front image](https://medias.watsons.co.th/publishing/WTCTH-311042-front-zoom.jpg?version=1733871036)

Web indexed retailer pages showed Add to Bag at review time; stock and prices may change. COSRX canonical page had repeated fetch timeouts; the verified alternate retailer route [without duplicated brand slug](https://www.watsons.co.th/en/cosrx-the-6-peptide-skin-booster-serum-150-ml./p/BP_311042) redirected to the canonical page and exposed the gallery. Its older cached snapshot also showed 649 THB, consistent with the newer indexed canonical snapshot. Manufacturer US stock is irrelevant to Thai retailer stock; Copper and COSRX manufacturer's own US/global listings were out of stock/backordered.

### Excluded candidates

The Ordinary Matrixyl 10% + HA was omitted: Thai-targeted Strawberrynet listed an additional Polyacrylamide compared with the current manufacturer list and showed out of stock. Argireline was omitted because exact Thai INCI and a verifiable product image were not established in the available retailer evidence. This preserves source accuracy over product count.

## Additional fragrance-claim verification

The two The Ordinary serums have the `fragrance-free` tag supported by the manufacturer’s explicit brand-wide [formulation statement](https://theordinary.com/en-nz/scientific-proof-skincare.html), not merely absence of fragrance tokens in INCI. Both reviewed retailer ingredient lists are consistent with that statement. No fragrance-free tag is inferred for COSRX. Fragrance-free status does not establish allergy safety; the existing reported-allergy exclusion still applies.

## Runtime validation and import result

The API runtime validated the entire 11-product batch with `products_from_fixture` before writing. All 11 image URLs returned HTTP 200 with image/jpeg content. The real recommendation engine was checked both before and after import against 64 synthetic combinations: four skin types × two sensitivity levels × eight image regions. Each eligible wrinkle recommendation selected three correctly labeled products for its application area. Additional checks covered minors, high sensitivity, reported allergies, unreleased image scores, zero wrinkle area and a THB 1,500 budget. No real user health records were read or altered for these checks.

`load_products` inserted 11 records. Repeating the import inserted zero additional records. The running database now contains 29 total products, including 13 published Thai wrinkle-care products. Eight allow eye-contour use and seven allow face use; two products allow both, so these counts overlap. All four skin types now have fragrance-free face and eye options for the medium-sensitivity rule, which previously had no matching face product. Prices remain dated snapshots, not live prices.
