# 内部 Gold Set

该目录保存方案二的人工可核对回归集。`pdfs/` 中的 4 份合成 PDF 覆盖 born-digital、扫描、跨页段落、跨页表格、重复表头、断行拼接、无边框/合并单元格、Figure、显式/推断链接和高风险 span。`annotations/` 是根据 PDF 可见内容写定的期望值，不由当前解析输出自动生成。

生成和运行：

```bash
PYTHONPATH=src .venv/bin/python scripts/build_gold_fixtures.py
PYTHONPATH=src .venv/bin/python scripts/run_gold_set.py
PYTHONPATH=src .venv/bin/python -m pdf_extraction.evaluation.cli \
  --manifest gold/manifest.json \
  --output outputs/evaluation-report.json \
  --config config/default.yaml
```

正式回归门禁增加 `--enforce`。门禁阈值来自 `config/default.yaml`，报告同时按文档类型和错误类型拆分。
