# Engineering Scripts

Current scripts support Requirement Gold construction, immutable revisions, evaluation and parser
fingerprints. Keep their current directory depth to preserve the existing `Path(__file__).parents[1]` path contract.

After the relevant Gold/manifest regressions pass, progressively organise them as:

```text
scripts/
├── gold/
├── evaluation/
└── maintenance/
```

Production entry points belong to the Python package/CLI. Do not add parallel pipelines under `scripts/`.
