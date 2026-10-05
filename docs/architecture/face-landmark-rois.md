# Landmark-derived wrinkle regions

New analysis jobs use `mediapipe-landmark-skin-roi-v1`. Existing stored analysis
JSON and old artifacts are not rewritten. The wrinkle network and overall parsed
face denominator remain unchanged; regional values are a new experimental method
and must not be compared directly to old fixed-ROI regional values.

## Pixel lineage

1. Existing YuNet alignment and face parsing produce the aligned RGB/skin mask.
2. MediaPipe Tasks Face Landmarker runs on that same RGB image, locally in the
   inference worker. It requires exactly one face and finite in-image coordinates.
3. Versioned polygon/hull and contour-dilation definitions create eight regions.
   The mask intersection excludes eye and lip interiors. Left/right mean image X.
4. `derive_scores` counts wrinkle pixels in these exact skin-constrained masks.
   A private `regions.png` renders a neutral head/feature sketch with pink only on
   detected wrinkle pixels intersecting the evaluated masks. No full ROI fill,
   dilation, or hull expands the highlighted pixels. ROI overlap is permitted; region percentages
   are not additive. The shapes are experimental geometry, not clinical anatomy.
5. Raw landmarks are temporary only, not persisted in analysis JSON or logs.

Landmark failure returns no regional values, never fixed-coordinate replacements.
The overall measurement can remain available. API provenance reports
`regional_geometry_status` as `available`, `unavailable`, or `legacy_fixed`.
New maps identify `regional_map_version: wrinkle-only-sketch-v1`; absent metadata
keeps the older evaluated-area caption. Stored artifacts are not rewritten.
The sketch includes anti-aliased oval, eye, brow, nose and lip contours. Ear and
neck outlines are illustrative framing derived from the oval bounds, not detected
anatomy, evaluated regions or model predictions. No illustration changes scoring.

## Release and privacy

Latest jobs use `head-region-area-v3`: a simplified landmark-based icon outline,
with upper eye contours, filled irises, heavier brows and short nose/mouth lines.
No photo edges, hair or background. Ears/neck are illustrative icon framing only,
not measured anatomy or evaluated regions. A region is
filled pink only if its ROI intersects at least one detected wrinkle pixel.
This is a REGION-PRESENCE visualization, not pixel coverage or severity. The
presentation uses pale pink with clipped diagonal hatching and fine neutral
anti-aliased facial contours; smoothing is display-only and leaves ROIs unchanged.
caption distinguishes it from the unchanged exact overlay/mask artifacts.
Scoring remains pixel-based; rendering never changes counts or denominators.

Previous jobs rendered `photo-doodle-wrinkle-v2`: bilateral smoothing and Canny
edges and simplified contours transform the uploaded image's aligned RGB into
outlines on white, without pencil shading. Tiny texture fragments are omitted. The full
aligned frame is preserved; generic ears/neck are not added. Details outside the
preprocessing crop cannot be reconstructed. Edge lines are aesthetic, never
wrinkle detections. Only the segmentation-mask intersection with evaluated ROIs
is painted pink, on the unchanged pixel grid. Older map versions remain readable.

Existing confidence releases do not approve the new ROI geometry. New landmark
results remain experimental and the image-score recommendation gate is withheld
with `landmark_roi_not_calibrated`; profile-based product flow remains separate.
Releasing landmark scores requires explicit validation and a future version-aware
release policy, not reuse of an old approval.

`GET /api/v1/analyses/{id}/artifacts/regions` uses the same owner check, no-store
header, expiry enforcement and delayed deletion as overlay/mask. The frontend
proxy keeps credentials server-side. Landmark maps are image artifacts and expire
with the other derived images. They are not public URLs.

## Runtime

New jobs additionally generate a private `outline.svg` from the uploaded image's
landmarks: the face oval and brows use measured coordinates; simplified eye,
nose and lip curves follow measured feature bounds. No hair or background edges
are drawn. Hatched area fills use the same ROI masks as regional scoring, only
where the wrinkle mask intersects that ROI. These indicate region presence, not
severity or exact wrinkle pixels. Scoring is unchanged.

`personalized_outline_available` advertises this artifact without putting raw
landmarks in result JSON. The authenticated `artifacts/outline` route enforces
ownership, expiry, no-store, nosniff and a sandboxed CSP. Worker cleanup deletes
the SVG alongside all derived images. The frontend renders it as an image, never
injecting SVG markup. Old results and missing/expired SVGs use an explicitly
labelled standard diagram; submit a new analysis for personalized geometry.

The inference Docker image installs MediaPipe 0.10.21 and downloads Google's
version-1 float16 Face Landmarker task at build time. There is no runtime model
download. `FACE_LANDMARKER_MODEL_PATH` can select a pre-provisioned local asset;
the default is `/app/assets/face_landmarker.task`.

Rebuild and restart the inference worker for new jobs. Restart the API for the new
artifact route. Users must submit a new image; an existing result keeps its prior
ROI method. Geometry/ROI accuracy needs representative-image validation before
clinical or treatment-related use.
