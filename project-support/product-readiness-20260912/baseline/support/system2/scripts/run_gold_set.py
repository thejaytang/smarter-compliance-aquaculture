from __future__ import annotations

from pathlib import Path

from pdf_extraction.pipeline import ExtractionPipeline


ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    pipeline = ExtractionPipeline.from_config_file(ROOT / "config" / "default.yaml")
    for pdf in sorted((ROOT / "gold" / "pdfs").glob("*.pdf")):
        pipeline.run(pdf, ROOT / "outputs" / "gold" / pdf.stem)


if __name__ == "__main__":
    main()
