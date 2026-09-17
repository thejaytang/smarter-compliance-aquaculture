from __future__ import annotations

from pathlib import Path

import pypdfium2 as pdfium

from ..types import PixelBox, RenderedPage


class PDFRenderer:
    def __init__(self, dpi: int = 200) -> None:
        self.dpi = dpi

    def render(
        self,
        pdf_path: str | Path,
        output_dir: str | Path,
        *,
        reuse_existing: bool = False,
        page_indices: set[int] | None = None,
    ) -> list[RenderedPage]:
        output = Path(output_dir)
        output.mkdir(parents=True, exist_ok=True)
        document = pdfium.PdfDocument(str(pdf_path))
        rendered: list[RenderedPage] = []
        try:
            selected = (
                range(len(document))
                if page_indices is None
                else sorted(page_indices)
            )
            for page_index in selected:
                if page_index < 0 or page_index >= len(document):
                    raise IndexError(f"page index out of range: {page_index}")
                page = document[page_index]
                width_points, height_points = map(float, page.get_size())
                image_path = output / f"page-{page_index + 1:04d}.png"
                if reuse_existing and image_path.is_file():
                    from PIL import Image

                    with Image.open(image_path) as cached:
                        width_px, height_px = cached.size
                else:
                    image = page.render(scale=self.dpi / 72).to_pil().convert("RGB")
                    image.save(image_path, format="PNG")
                    width_px, height_px = image.size
                rendered.append(
                    RenderedPage(
                        page_index=page_index,
                        image_path=image_path,
                        width_points=width_points,
                        height_points=height_points,
                        width_px=width_px,
                        height_px=height_px,
                        rotation=int(page.get_rotation()) * 90,
                    )
                )
                page.close()
        finally:
            document.close()
        return rendered

    @staticmethod
    def crop(page: RenderedPage, box: PixelBox, output_path: str | Path) -> Path:
        from PIL import Image

        target = Path(output_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        with Image.open(page.image_path) as image:
            image.crop((box.x0, box.y0, box.x1, box.y1)).save(target, format="PNG")
        return target
