// Historical PDF evidence and explicitly synthetic HTML / Excel examples.
export const pdfSource = {
  "sourceHash": "77e1d87383382fda4f27dc9be79937cc3017ce350b8b1d436a74500561083838",
  "filename": "CS005-001_ASC_Farm_and_Feed_Certification_and_Accreditation_Requirements.pdf",
  "canonicalRevision": 0,
  "historicalRun": "2026-08-31",
  "sourcePages": 89,
  "pages": {
    "19": {
      "width": 595.3200073242188,
      "height": 841.9199829101562,
      "printedLabel": "20"
    },
    "20": {
      "width": 595.3200073242188,
      "height": 841.9199829101562,
      "printedLabel": "21"
    }
  },
  "title": "ASC Farm and Feed Certification and Accreditation Requirements",
  "officialUrl": "https://programme-centre.asc-aqua.org/resource-hub/?filter=farm"
};
export const demoCases = [
  {
    "id": "pdf-text",
    "text": "Part B outlines the operational certification requirements for CABs to follow when auditing Clients and their Unit of Certification (UoC) against ASC Requirements; from the application phase until the certification decision and throughout the certificate lifetime. It also covers additional procedures such as transfer of certificates.",
    "page": 19,
    "boxes": [
      [
        56.50861012690589,
        151.53839795005376,
        507.4977087830402,
        164.85649943260006
      ],
      [
        56.50861012690589,
        167.7360889423398,
        525.1341539818834,
        181.0541904248861
      ],
      [
        56.50861012690589,
        183.57383124590837,
        514.3363303907549,
        197.25188141717211
      ],
      [
        56.50861012690589,
        199.7715222381944,
        467.9056889489023,
        213.44957240945817
      ]
    ],
    "source": "CS005",
    "format": "PDF",
    "kind": "text",
    "title": "Check extracted text",
    "question": "Does this text match the highlighted original?",
    "hint": "Confirm this paragraph only. Page completeness is reviewed separately.",
    "anchor": "Page 20 · Part B / Scope",
    "segmentIds": "p0019_paragraph_0002"
  },
  {
    "id": "pdf-join",
    "text": "The Client (Certificate Holder[^6] ) shall be capable of signing a binding contract\nthat is legally enforceable.",
    "pieces": [
      "The Client (Certificate Holder[^6] ) shall be capable of signing a binding contract",
      "that is legally enforceable."
    ],
    "page": 20,
    "boxes": [
      [
        102.93925156875851,
        310.9956670518918,
        485.90206160078316,
        323.2339224682857
      ],
      [
        102.93925156875851,
        322.87397377956825,
        233.2329895683759,
        335.11222919596213
      ]
    ],
    "footnote": {
      "id": "p0020_paragraph_0032",
      "text": "6 Client granted ASC certification for a specific UoC.",
      "page": 20,
      "boxes": [
        [
          56.50861012690589,
          743.6539908902876,
          286.50225261794327,
          754.4524515518116
        ]
      ]
    },
    "source": "CS005",
    "format": "PDF",
    "kind": "join",
    "title": "Join a split paragraph",
    "question": "Should these two fragments be one paragraph?",
    "hint": "Compare the sentence and its footnote before merging.",
    "anchor": "Page 21 · Table 1 / Requirement 2",
    "segmentIds": [
      "p0020_paragraph_0010",
      "p0020_paragraph_0012"
    ]
  },
  {
    "id": "pdf-table",
    "text": "",
    "page": 20,
    "boxes": [
      [
        50.5,
        160,
        504.5,
        628
      ]
    ],
    "boxOrigin": "manually_located_for_review_demo",
    "cells": [
      [
        "Po",
        "Certification Type",
        "cc ———is——"
      ],
      [
        "Single",
        "Single Site",
        "Multi-site"
      ]
    ],
    "source": "CS005",
    "format": "PDF",
    "kind": "table",
    "title": "Check missing table content",
    "question": "Has the full table been captured?",
    "hint": "The historical result contains only two rows. Check the body and report what is missing.",
    "anchor": "Page 21 · Table 1",
    "segmentIds": "page:20"
  },
  {
    "id": "html-list",
    "source": "SAMPLE-HTML",
    "format": "HTML",
    "kind": "html",
    "title": "Check list hierarchy",
    "question": "Are a and b parallel items, or is b inside a?",
    "hint": "Use the indentation in the source to confirm the relationship.",
    "anchor": "Section 3.2 · Records",
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
    "anchor": "Checklist · Cells B4:C4",
    "text": "Inspection record | Date and operator name",
    "segmentIds": "excel-columns"
  }
];
