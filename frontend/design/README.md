# Frontend design references

These SVGs are historical visual references, not executable screens or a specification of current backend capabilities. Use [DESIGN.md](../DESIGN.md), nearby components, and the [frontend guide](../README.md) when implementing UI.

## Open and reuse

- [aphrodize-ui-wireframe.svg](aphrodize-ui-wireframe.svg): desktop dashboard and mobile capture/result concepts. Open in a browser or import into Figma.
- [aphrodize-logo-concepts.svg](aphrodize-logo-concepts.svg): Contour A, Calm Orbit, and Protected Signal logo concepts.

Contour A explores a curved A/visual signal; Calm Orbit explores longitudinal observations; Protected Signal explores consent/privacy controls. They are concepts, not a requirement to replace the current logo.

## Apply to current flows

The wireframe explores consent/capture, quality rejection, results, history, and privacy controls. Some historical labels, including acne-like image observations, do not represent supported current inference. Verify against the implemented API before reusing copy or metrics.

- Separate image-derived observations, user-reported information, and rule-based guidance.
- Keep quality limitations, release/confidence status, and model version near results. Show unavailable/withheld states honestly.
- Explain capture rejection and provide a retake action. Do not invent a score for rejected input.
- Preserve explicit consent, deletion controls, accessible labels, keyboard navigation, and visible focus.
- Avoid diagnosis, age-prediction, treatment-effect claims, or unsupported accuracy claims. Label prices and research results with their recorded provenance/date.

For the running pages use `pnpm dev` in `frontend/`; the SVGs do not start an app. See [safety and governance](../../docs/project/Safety%20and%20Governance.md) for product constraints.
