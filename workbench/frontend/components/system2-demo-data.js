// Fictional product examples; no original business documents.
export const pdfSource = {
  "synthetic": true,
  "sourceHash": "b44cb1da09d7a651383ff5462b33f77884bc52f9215529cda2da78c68f74f185",
  "filename": "review-sample.pdf",
  "canonicalRevision": 0,
  "historicalRun": "synthetic example",
  "sourcePages": 2,
  "pages": {
    "0": {
      "width": 595,
      "height": 842,
      "printedLabel": "1"
    },
    "1": {
      "width": 595,
      "height": 842,
      "printedLabel": "2"
    }
  },
  "title": "Synthetic review practice",
  "officialUrl": "/demo-assets/review-sample.pdf"
};
export const demoCases = [
  {
    "id": "pdf-text",
    "text": "This fictional inspection guide demonstrates a review workflow. The operator records the inspection date and the equipment name. These examples are synthetic and contain no regulatory requirements.",
    "page": 0,
    "boxes": [
      [
        56,
        150,
        540,
        194
      ]
    ],
    "source": "SAMPLE-PDF",
    "format": "PDF",
    "kind": "text",
    "title": "Check extracted text",
    "question": "Does this text match the highlighted original?",
    "hint": "Confirm this paragraph only. Page completeness is reviewed separately.",
    "anchor": "Page 1 \u00b7 Practice guide",
    "segmentIds": "sample_p0_text"
  },
  {
    "id": "pdf-join",
    "text": "The operator[^6] shall record the equipment name\nand the inspection date.",
    "pieces": [
      "The operator[^6] shall record the equipment name",
      "and the inspection date."
    ],
    "page": 1,
    "boxes": [
      [
        56,
        150,
        490,
        181
      ]
    ],
    "footnote": {
      "id": "sample_note_6",
      "text": "6 Operator means the person recording this fictional example.",
      "page": 1,
      "boxes": [
        [
          56,
          740,
          520,
          754
        ]
      ]
    },
    "source": "SAMPLE-PDF",
    "format": "PDF",
    "kind": "join",
    "title": "Join a split paragraph",
    "question": "Should these two fragments be one paragraph?",
    "hint": "Compare the sentence and its footnote before merging.",
    "anchor": "Page 2 \u00b7 Inspection record",
    "segmentIds": [
      "sample_p1_a",
      "sample_p1_b"
    ]
  },
  {
    "id": "pdf-table",
    "text": "",
    "page": 1,
    "boxes": [
      [
        56,
        220,
        520,
        340
      ]
    ],
    "boxOrigin": "manually_located_for_review_demo",
    "cells": [
      [
        "Equipment",
        "Date"
      ],
      [
        "Pump A",
        ""
      ]
    ],
    "source": "SAMPLE-PDF",
    "format": "PDF",
    "kind": "table",
    "title": "Check missing table content",
    "question": "Has the full table been captured?",
    "hint": "The candidate omits rows. Compare it with the complete synthetic table.",
    "anchor": "Page 2 \u00b7 Practice table",
    "segmentIds": "sample_table"
  },
  {
    "id": "html-list",
    "source": "SAMPLE-HTML",
    "format": "HTML",
    "kind": "html",
    "title": "Check list hierarchy",
    "question": "Are a and b parallel items, or is b inside a?",
    "hint": "Use the indentation in the source to confirm the relationship.",
    "anchor": "Section 3.2 \u00b7 Records",
    "text": "Keep the following records:\na. Inspection date.\nb. Operator name.",
    "segmentIds": "html-list"
  },
  {
    "id": "excel-columns",
    "source": "SAMPLE-XLSX",
    "format": "Excel",
    "kind": "excel",
    "title": "Check column mapping",
    "question": "Which columns supply the record and its required fields?",
    "hint": "Check the headers above row 4, then confirm each field.",
    "anchor": "Checklist \u00b7 Cells B4:C4",
    "text": "Inspection record | Date and operator name",
    "segmentIds": "excel-columns"
  }
];
