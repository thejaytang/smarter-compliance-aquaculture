# R8 original HTML reader checks

R8-01–03 implemented; functional browser checks passed. Native 200% browser zoom remains pending Mac unlock. These are reading-projection changes only.

- The actual PE002 original was previewed in a 400 px sandboxed iframe. `Sist endret`, `Gjelder for` and definition identifiers `a.`/`b.` stayed intact; long metadata and definition text remained readable.
- Keyboard Enter followed a synthetic source-authored footnote to its exact derived anchor, and Tab/Enter returned to the original reference. The targeted paragraph showed the existing outline. Server request output recorded only initial page/iframe loads and favicon, with no document request during either fragment navigation.
- The native browser displayed reversed alphabetic identifiers `d.`, `c.`, explicit `a.`, and Roman identifiers `IX.`, `X.`. Invalid, duplicate, missing and external references remained inert; no external asset or model was called.
- The existing navigation/parser suites passed **19/19** tests, including new unique-target/security and declarative-list regressions. Original bytes are checked after reading, and registered-source hash rejection/cache behavior remains covered.
- Follow-up complete reader navigation/parser/resolution checks passed **36/36**, and actual HTTP boundary checks passed **9/9**.
- [Real-source comparison](reader-fidelity.json) confirms unchanged original SHA256, body text, table order/text, all 811 source anchors, navigation, document information and display-fidelity metadata against the before-round reader. The new safe local navigation is the only added source-link behavior.

Reproduce with System2's own environment:

```sh
PYTHONPATH=workbench/backend/system2/src:workbench/backend/application:workbench workbench/backend/system2/.venv/bin/python -m pytest workbench/tests/system2/test_material_reader_navigation.py workbench/tests/system2/test_material_reader_parser.py -q
PYTHONPATH=workbench/backend/system2/src workbench/backend/system2/.venv/bin/python project-support/validation/ui-round8-20260922/reader_fixture.py
```

The fixture writes only temporary derived HTML, uses the permanent Example as read-only input, and exposes no business API. Both iframe `sandbox=""` and the production reader's restrictive CSP remain in place. The preserved source hash is `9334a78a021971411e5c8826a2bb16aab1db707d778f6249c9a36b0afc90a4a1`. The user's live service was not restarted or written by this check. Windows execution is not established by these Mac results.
