from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "gold" / "pdfs"


def _canvas(name: str) -> canvas.Canvas:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    return canvas.Canvas(str(OUTPUT / name), pagesize=letter)


def born_digital() -> None:
    pdf = _canvas("born-digital-multicolumn.pdf")
    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(54, 742, "Section 1 - Digital Evidence")
    pdf.setFont("Helvetica", 10)
    left = ["The limit is 5 mg.", "It shall remain below 10 mg.", "See Table 1."]
    right = ["Effective date: 2026-08-25.", "The value must not exceed 7 mg.", "Annex 2 applies."]
    for index, value in enumerate(left):
        pdf.drawString(54, 700 - index * 22, value)
    for index, value in enumerate(right):
        pdf.drawString(320, 700 - index * 22, value)
    pdf.setFont("Helvetica-Bold", 10)
    pdf.drawString(54, 590, "Table 1: Limits")
    data = [["Item", "Limit"], ["A", "5 mg"], ["B", "7 mg"]]
    x_values, y_values = [54, 190, 300], [570, 548, 526, 504]
    for x in x_values:
        pdf.line(x, y_values[-1], x, y_values[0])
    for y in y_values:
        pdf.line(x_values[0], y, x_values[-1], y)
    pdf.setFont("Helvetica", 9)
    for row, values in enumerate(data):
        for column, value in enumerate(values):
            pdf.drawString(x_values[column] + 5, y_values[row + 1] + 7, value)
    pdf.showPage()
    pdf.save()


def scanned_critical() -> None:
    width, height = 1275, 1650
    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)
    font = ImageFont.load_default(size=24)
    draw.text((110, 120), "SCANNED SAFETY NOTICE", fill="black", font=font)
    draw.text((110, 240), "The dosage shall be 0.01 mg.", fill="black", font=font)
    draw.text((110, 300), "It must not exceed 0.02 mg.", fill="black", font=font)
    draw.text((110, 360), "Valid until 2027-12-31.", fill="black", font=font)
    temp = OUTPUT / "scanned-critical.png"
    OUTPUT.mkdir(parents=True, exist_ok=True)
    image.save(temp)
    pdf = _canvas("scanned-critical.pdf")
    pdf.drawImage(str(temp), 0, 0, width=letter[0], height=letter[1])
    pdf.showPage()
    pdf.save()
    temp.unlink()


def cross_page() -> None:
    pdf = _canvas("cross-page-content.pdf")
    pdf.setFont("Helvetica-Bold", 14)
    pdf.drawString(54, 742, "Section 2 - Cross-page Evidence")
    pdf.setFont("Helvetica", 10)
    pdf.drawString(54, 190, "This paragraph deliberately continues")
    pdf.drawString(54, 170, "across the page boundary with a hy-")
    pdf.setFont("Helvetica-Bold", 9)
    pdf.drawString(300, 160, "Table 2: Continued Limits")
    x_values = [300, 390, 480, 558]
    y_values = [145, 123, 101, 79]
    for x in x_values:
        pdf.line(x, y_values[-1], x, y_values[0])
    for y in y_values:
        pdf.line(x_values[0], y, x_values[-1], y)
    pdf.setFont("Helvetica", 8)
    for row, values in enumerate([["Item", "Min", "Max"], ["A", "1", "5"], ["B", "2", ""]]):
        for column, value in enumerate(values):
            pdf.drawString(x_values[column] + 4, y_values[row + 1] + 7, value)
    pdf.showPage()
    pdf.setFont("Helvetica", 10)
    pdf.drawString(54, 740, "phenated word and ends on the next page.")
    x_values = [300, 390, 480, 558]
    y_values = [720, 698, 676, 654]
    for x in x_values:
        pdf.line(x, y_values[-1], x, y_values[0])
    for y in y_values:
        pdf.line(x_values[0], y, x_values[-1], y)
    pdf.setFont("Helvetica", 8)
    for row, values in enumerate([["Item", "Min", "Max"], ["B", "", "8"], ["C", "3", "9"]]):
        for column, value in enumerate(values):
            pdf.drawString(x_values[column] + 4, y_values[row + 1] + 7, value)
    pdf.showPage()
    pdf.save()


def borderless_figure() -> None:
    pdf = _canvas("borderless-merged-figure.pdf")
    pdf.setFont("Helvetica-Bold", 14)
    pdf.drawString(54, 742, "Annex 2 - Mixed Objects")
    pdf.setFont("Helvetica", 10)
    pdf.drawString(54, 700, "The following table contains a merged header.")
    pdf.setFont("Helvetica-Bold", 10)
    pdf.drawString(54, 662, "Table 3: Borderless Values")
    pdf.setFont("Helvetica", 9)
    rows = [("Combined category", "", ""), ("Item", "Low", "High"), ("Alpha", "2", "8"), ("Beta", "3", "9")]
    for row, values in enumerate(rows):
        y = 635 - row * 22
        pdf.drawString(54, y, values[0])
        pdf.drawString(220, y, values[1])
        pdf.drawString(320, y, values[2])
    pdf.setFont("Helvetica", 8)
    pdf.drawString(54, 535, "Source: synthetic scheme-two gold fixture.")
    pdf.setFont("Helvetica-Bold", 10)
    pdf.drawString(54, 470, "Figure 1: Embedded label")
    pdf.rect(54, 300, 270, 150, stroke=1, fill=0)
    pdf.circle(120, 375, 30, stroke=1, fill=0)
    pdf.line(150, 375, 250, 375)
    pdf.setFont("Helvetica", 12)
    pdf.drawString(170, 390, "TARGET 42")
    pdf.drawString(170, 350, "LIMIT 7 mg")
    pdf.showPage()
    pdf.save()


def main() -> None:
    born_digital()
    scanned_critical()
    cross_page()
    borderless_figure()


if __name__ == "__main__":
    main()
