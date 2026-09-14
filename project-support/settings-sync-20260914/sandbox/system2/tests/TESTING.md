# Test Directory

- `contracts/`: cross-module schemas, policy, dependencies and compatibility contracts.
- `unit/`: focused model, profiling, native-extraction and routing tests.
- `integration/`: pipeline, API, delivery, Regulatory IR and security tests.
- `domains/requirements/`: Requirement parsing, semantics, Gold and manifest regression.
- `support/`: shared infrastructure, including project-root resolution.

Tests must not infer the project root from their own file depth. Use
`tests.support.paths.PROJECT_ROOT`.

Passing tests do not replace source-fidelity acceptance. Real artifacts still require joint checks of Canonical,
source evidence, quality reports and domain semantics.
