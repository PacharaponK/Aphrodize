# UV map approved scope — 5 October 2026

Mode: Operate. Scope: `/uv-map` only; Home retains its incumbent map.

## Direction contract

THESIS: Province exploration through a lightweight tilted 2.5D map, not a WebGL scene or simulated geographic elevation.

OWN-WORLD: Existing Aphrodize blush/coral tokens, white information panel, restrained cartographic grid and offset depth. Preserve the five semantic UV colors and gray unavailable areas.

STORY: Choose API/model and day, select a province by map or native dropdown, read its actual returned UV status and provenance. Never interpolate or fabricate missing values.

FIRST VIEWPORT: Controls and availability precede a large map left and selected-province details right. Legend sits with the map. Mobile stacks the same content with smaller tilt and wrapping controls.

FORM: User-pinned 2.5D direction; no concept seed needed for this narrow confirmed extension. Signature interaction: selected province lifts slightly, zoom centers on its representative coordinate; flat view removes depth. Reduced motion removes tilt and animated movement.

FINISH: unreviewed and undocumented is unfinished; this build ends with the finish review, the verdict, DESIGN.md, and every shipping raster carrying its provenance

Implementation uses existing SVG boundary data, no new library or raster. Zoom is 1x/1.5x/2x, with whole-country reset. Height is explicitly decorative, not UV magnitude or terrain.
