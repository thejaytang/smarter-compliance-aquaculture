# Normal original-location follow-up

**One visible-source conflict found; one body-location control passed.** This read-only check extends checkpoint 15, within its authorized normal-entry verification window. It does not rerun parsing or alter normal records.

CS004 physical page 1, unit `pdf:1c70d5a4e493b4297650da99`, has effective text “Aquaculture Stewardship” and top-left bounding box (402.84, 36.0, 515.52, 45.0). The source, retained parser copy and Canonical all bind SHA256 `a34e5f4fc78486136ddbf3d661d26aad85e4b8a1990b2e6eda3f3ac1df7f7b5c`. Native text extraction returns the text in that area, while the original rendered crop contains background/icon pixels and does not visibly display it. The renderer is following the stored coordinates; this is a native-layer/visible-page conflict. A follow-up object inspection finds the text as object 3 in normal fill mode (0), followed by image object 36 spanning the whole page. Combined with the rendered result, this supports paint-order occlusion by the later cover image. An invisible-render-mode check alone would miss it.

The unit stays A Pending and B blocked, with no calibrated confidence or automatic release. That prevents false completion, but the current generic missing-confidence warning does not explicitly detect this source conflict. A future detector improvement should target this failure mode and retain a visible-original comparison.

As a control, physical page 19 clause 2.1.1 (`pdf:d9f2d131d10121178a814f90:row:2`) produces an original crop that visibly contains the expected two-column redox/sulphide requirement and criteria. Thus these observations do not support changing the preview coordinate convention globally.

This adds a separately reported normal-instance diagnostic outside the frozen eight-page quality cohort. It neither changes its denominator nor upgrades the body control to full-table correctness. The 16 functional scenarios retain their declared scope; overall source-quality acceptance remains incomplete.

Evidence: [structured findings](../../../system2/outputs/runs/requirement-acceptance-20260911/stage-v2/normal-load-current08/location-followup.json), [full original cover render](../../../system2/outputs/runs/requirement-acceptance-20260911/stage-v2/normal-load-current08/location-full.png), [body control crop](../../../system2/outputs/runs/requirement-acceptance-20260911/stage-v2/normal-load-current08/location-clause-crop.png).

[Native object evidence](../../../system2/outputs/runs/requirement-acceptance-20260911/stage-v2/normal-load-current08/native-render-mode.json) records render mode, bounds and object order. Next discriminating experiment: validate a paint-order visibility diagnostic with opaque overlay, transparent overlay, native-only and form-object controls, plus the correct page-19 location. Do not repeat the stopped generic raster line/contrast experiments or automatically rewrite source facts.


## Isolated visibility intervention completed

A separately callable experimental diagnostic now renders an in-memory original copy, removes only top-level native text from that in-memory copy, and compares pixel changes in the native text bounds. It never saves a modified source or updates business state. Nested form text remains explicitly unverified. Positive pixel changes do not establish complete character visibility, and the same renderer is not independent content verification.

Five synthetic cases met their expected visibility outcomes: opaque overlay, transparent overlay, native-only text, unhandled form text, and a correct matching raster/OCR layer. The final case visibly preserves “Requirement 123” after removing the native layer, demonstrating why a zero-contribution result cannot itself be called an extraction error.

The real CS004 cover has eight of eight native text objects with no visible contribution. The unchanged eight frozen pages have 906 top-level text objects and zero zero-contribution objects. This establishes applicability limits; it does not repair or reduce any of the existing 29 natural fidelity defects.

Decision: **ADJUST**. Preserve this diagnostic and the explicit cover conflict, but do not integrate it as an automatic content-error verdict or claim improved frozen-sample recall. The measured cross-page/table-relation failures remain the next development priority. Candidate 08 and normal service code remain unchanged.

Evidence: [five controls and cover result](../../../system2/outputs/runs/requirement-acceptance-20260911/stage-v2/native-visibility-probe-v1/result.json), [frozen-page scope](../../../system2/outputs/runs/requirement-acceptance-20260911/stage-v2/native-visibility-probe-v1/frozen-page-visibility.json), [decision](../../../system2/outputs/runs/requirement-acceptance-20260911/stage-v2/native-visibility-probe-v1/decision.json). All samples and results are development diagnostics, not independent acceptance.
