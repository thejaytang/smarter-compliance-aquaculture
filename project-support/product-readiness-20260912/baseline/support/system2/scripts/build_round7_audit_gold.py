#!/usr/bin/env python3
"""Build the frozen Round 7 Audit Manual Gold from source-only native lines.

This script is intentionally annotation-specific.  It never imports or runs the
Requirement assembler, so the holdout answer is frozen independently from the
parser prediction that will be scored later.
"""

from __future__ import annotations

import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE_PATH = ROOT / "gold/requirements/source-evidence/audit-manual-p017-p018-round7-source.json"
OUTPUT_PATH = ROOT / "gold/requirements/annotations/audit-manual-p017-p018-round7-holdout.json"


def lid(page_index: int, number: int) -> str:
    return f"native_p{page_index:04d}_t{number:06d}"


def ids(page_index: int, *numbers: int) -> list[str]:
    return [lid(page_index, number) for number in numbers]


def span(page_index: int, start: int, end: int) -> list[str]:
    return ids(page_index, *range(start, end + 1))


ROWS = [
    dict(rid="5.1.6", page=16, ident=ids(16, 84), indicator=span(16, 122, 125), value=span(16, 126, 127), applicability=span(16, 128, 130), client=[span(16, 0, 2), span(16, 5, 7), span(16, 10, 11)], auditor=[span(16, 3, 4), span(16, 8, 9), ids(16, 12)]),
    dict(rid="5.1.7", page=16, ident=ids(16, 150), indicator=span(16, 140, 144), value=span(16, 145, 146), applicability=span(16, 147, 148), client=[span(16, 13, 14), span(16, 17, 19), span(16, 22, 23)], auditor=[span(16, 15, 16), span(16, 20, 21), span(16, 24, 25)]),
    dict(rid="5.2.1", page=16, ident=ids(16, 87), indicator=span(16, 88, 96), value=span(16, 97, 98), applicability=span(16, 99, 100), client=[span(16, 29, 38), span(16, 42, 44), span(16, 47, 48)], auditor=[span(16, 39, 41), span(16, 45, 46), ids(16, 49)]),
    dict(rid="5.2.2", page=16, ident=ids(16, 112), indicator=span(16, 101, 105), value=span(16, 106, 107), applicability=span(16, 108, 109), client=[span(16, 51, 53), span(16, 55, 56)], auditor=[ids(16, 54), ids(16, 57), span(16, 59, 60)]),
    dict(rid="5.2.3", page=16, ident=ids(16, 131), indicator=span(16, 132, 134), value=span(16, 135, 136), applicability=span(16, 137, 138), client=[span(16, 63, 64), span(16, 68, 70)], auditor=[span(16, 65, 67), ids(16, 71)]),
    dict(rid="5.2.4", page=16, ident=ids(16, 120), indicator=span(16, 113, 115), value=span(16, 116, 117), applicability=span(16, 118, 119), client=[ids(16, 72), span(16, 75, 77), span(16, 80, 81)], auditor=[span(16, 73, 74), span(16, 78, 79), span(16, 82, 83)]),
    dict(rid="5.2.5", page=17, ident=ids(17, 121), indicator=span(17, 77, 84), value=span(17, 85, 86), applicability=span(17, 87, 88), client=[span(17, 0, 3), span(17, 6, 7), span(17, 9, 10)], auditor=[span(17, 4, 5), ids(17, 8), ids(17, 11)]),
    dict(rid="5.2.6", page=17, ident=ids(17, 139), indicator=span(17, 131, 134), value=span(17, 135, 136), applicability=span(17, 137, 138), client=[span(17, 12, 13), span(17, 16, 17)], auditor=[span(17, 14, 15), span(17, 18, 19)]),
    dict(rid="5.2.7", page=17, ident=ids(17, 90), indicator=span(17, 91, 95), value=span(17, 96, 97), applicability=span(17, 98, 99), client=[span(17, 20, 22), span(17, 27, 28)], auditor=[span(17, 23, 26), span(17, 29, 30)]),
    dict(rid="5.2.8", page=17, ident=ids(17, 110), indicator=span(17, 102, 105), value=span(17, 106, 107), applicability=span(17, 108, 109), client=[span(17, 31, 32), span(17, 35, 36)], auditor=[span(17, 33, 34), ids(17, 37)]),
    dict(rid="5.2.9", page=17, ident=ids(17, 111), indicator=span(17, 112, 116), value=span(17, 117, 118), applicability=span(17, 119, 120), client=[ids(17, 38), ids(17, 41)], auditor=[span(17, 39, 40), ids(17, 42)]),
    dict(rid="5.2.10", page=17, ident=ids(17, 89), indicator=span(17, 69, 72), value=span(17, 73, 74), applicability=span(17, 75, 76), client=[span(17, 43, 44), span(17, 47, 48), span(17, 50, 51), span(17, 53, 54)], auditor=[span(17, 45, 46), ids(17, 49), ids(17, 52), span(17, 55, 56)]),
    dict(rid="5.2.11", page=17, ident=ids(17, 122), indicator=span(17, 123, 125), value=span(17, 126, 127), applicability=span(17, 128, 129), client=[span(17, 57, 58), ids(17, 61), span(17, 64, 65)], auditor=[span(17, 59, 60), span(17, 62, 63), span(17, 66, 67)]),
]


FOOTNOTES = {
    "83": ("p17-footnote-83", ids(16, 86), "semantic"),
    "84": ("p17-footnote-84", ids(16, 85), "direct"),
    "85": ("p17-footnote-85", span(16, 110, 111), "direct"),
    "86": ("p17-footnote-86", ids(16, 149), "direct"),
    "88": ("p18-footnote-88", ids(17, 130), "direct"),
}


FOOTNOTE_OWNERS = {
    "5.2.1": ["83", "84"],
    "5.2.2": ["85", "86"],
    "5.2.6": ["83"],
    "5.2.7": ["83"],
    "5.2.10": ["83"],
    "5.2.11": ["88"],
}


def normalize(parts: list[str]) -> str:
    return re.sub(r"\s+", " ", " ".join(part.strip() for part in parts)).strip()


def strip_label(text: str, label: str) -> str:
    return re.sub(rf"^{re.escape(label)}\s*:?\s*", "", text, flags=re.I).strip()


def lower_initial(text: str) -> str:
    return text[:1].lower() + text[1:] if text else text


def main() -> None:
    if OUTPUT_PATH.exists():
        raise FileExistsError(
            f"frozen Gold already exists: {OUTPUT_PATH}; create a superseding revision instead"
        )
    source = json.loads(SOURCE_PATH.read_text(encoding="utf-8"))
    line_by_id = {
        line["id"]: line
        for page in source["pages"]
        for line in page["text_lines"]
    }
    page_by_index = {page["page_index"]: page for page in source["pages"]}
    segments: list[dict] = []

    def joined(line_ids: list[str]) -> str:
        return normalize([line_by_id[value]["text"] for value in line_ids])

    def add_segment(
        segment_id: str,
        line_ids: list[str],
        role: str,
        object_kind: str,
        *,
        source_text: str | None = None,
    ) -> str:
        lines = [line_by_id[value] for value in line_ids]
        page_indices = {int(value.split("_p", 1)[1].split("_", 1)[0]) for value in line_ids}
        if len(page_indices) != 1:
            raise ValueError(f"segment crosses pages: {segment_id}")
        page_index = page_indices.pop()
        page = page_by_index[page_index]
        boxes = [line["bbox_points"] for line in lines]
        segments.append(
            {
                "segment_id": segment_id,
                "page_number": page_index + 1,
                "page_index": page_index,
                "page_size": {
                    "width": page["width_points"],
                    "height": page["height_points"],
                    "unit": "pdf_point",
                    "origin": "top_left",
                },
                "bbox": {
                    "x0": min(box[0] for box in boxes),
                    "y0": min(box[1] for box in boxes),
                    "x1": max(box[2] for box in boxes),
                    "y1": max(box[3] for box in boxes),
                },
                "role": role,
                "object_kind": object_kind,
                "segment_order": 0,
                "source_text": source_text or joined(line_ids),
            }
        )
        return segment_id

    footer_ids = [
        add_segment("p17-footer", span(16, 154, 156), "footer", "text_block", source_text="\n".join(line_by_id[value]["text"].strip() for value in span(16, 154, 156))),
        add_segment("p18-footer", span(17, 140, 142), "footer", "text_block", source_text="\n".join(line_by_id[value]["text"].strip() for value in span(17, 140, 142))),
    ]
    criterion_id = add_segment("p17-criterion-5.2", ids(16, 121), "criterion_heading", "text_block")
    table_header_id = add_segment("p17-audit-table-header-5.2", span(16, 26, 28), "other", "other")
    note_517_id = add_segment("p17-r5.1.7-option-note", ids(16, 139), "other", "text_block")
    instruction_52_id = add_segment(
        "p17-shared-instruction-5.2",
        span(16, 151, 153),
        "other",
        "text_block",
        source_text=line_by_id[lid(16, 151)]["text"].strip() + "\n" + normalize([line_by_id[lid(16, 152)]["text"], line_by_id[lid(16, 153)]["text"]]),
    )
    note_5210_id = add_segment("p18-r5.2.10-guidance-note", span(17, 100, 101), "other", "text_block")

    footnote_text: dict[str, str] = {}
    for marker, (segment_id, line_ids, _link_type) in FOOTNOTES.items():
        text = joined(line_ids)
        footnote_text[marker] = re.sub(rf"^\[{marker}\]\s*", "", text).strip()
        add_segment(segment_id, line_ids, "footnote", "footnote")

    requirement_segments: dict[str, dict[str, str | list[str]]] = {}
    action_objects: dict[str, tuple[list[dict], list[dict]]] = {}
    for row in ROWS:
        rid = row["rid"]
        prefix = f"p{row['page'] + 1}-r{rid}"
        indicator = strip_label(joined(row["indicator"]), "Indicator")
        value = strip_label(joined(row["value"]), "Requirement")
        applicability = strip_label(joined(row["applicability"]), "Applicability")
        direct = [
            add_segment(f"{prefix}-id", row["ident"], "requirement_id", "table_cell", source_text=rid),
            add_segment(f"{prefix}-indicator", row["indicator"], "indicator_text", "table_cell", source_text=indicator),
            add_segment(f"{prefix}-value", row["value"], "requirement_value", "table_cell", source_text=value),
            add_segment(f"{prefix}-applicability", row["applicability"], "applicability", "table_cell", source_text=applicability),
        ]
        requirement_segments[rid] = {
            "direct": direct,
            "indicator": indicator,
            "value": value,
            "applicability": applicability,
            "value_segment": direct[2],
            "indicator_segment": direct[1],
            "app_segment": direct[3],
        }
        linked: list[list[dict]] = []
        for action_role, groups in (("client_action", row["client"]), ("auditor_action", row["auditor"])):
            entries: list[dict] = []
            for index, line_ids in enumerate(groups):
                source_action = joined(line_ids)
                match = re.match(r"^([A-Za-z])\.\s*(.*)$", source_action)
                if not match:
                    raise ValueError(f"missing action marker for {rid}: {source_action}")
                marker, action_text = match.groups()
                segment_id = add_segment(
                    f"{prefix}-{'client' if action_role == 'client_action' else 'cab'}-{marker.lower()}",
                    line_ids,
                    action_role,
                    "table_cell",
                    source_text=source_action,
                )
                entries.append({"marker": marker, "text": action_text, "source_segment_ids": [segment_id]})
            linked.append(entries)
        action_objects[rid] = (linked[0], linked[1])

    # Give every segment a deterministic physical reading-order index.
    segments.sort(key=lambda item: (item["page_index"], item["bbox"]["y0"], item["bbox"]["x0"], item["segment_id"]))
    for order, segment in enumerate(segments):
        segment["segment_order"] = order

    thresholds = {
        "5.1.6": [
            {"raw_text": "≤ 40% of total mortalities", "operator": "lte", "normalized_value": 40, "unit": "%", "applies_to": "unexplained mortality as a share of total mortalities", "basis": "explicit", "source_segment_ids": [requirement_segments["5.1.6"]["value_segment"]]},
            {"raw_text": "> 6% total mortality", "operator": "gt", "normalized_value": 6, "unit": "%", "applies_to": "total mortality in the most recent complete production cycle", "basis": "explicit", "source_segment_ids": [requirement_segments["5.1.6"]["app_segment"]]},
        ],
        "5.2.3": [{"raw_text": "100%", "operator": "eq", "normalized_value": 100, "unit": "%", "applies_to": "medication events prescribed by a veterinarian", "basis": "explicit", "source_segment_ids": [requirement_segments["5.2.3"]["value_segment"]]}],
        "5.2.6": [{"raw_text": "at or below the country Entry Level", "operator": "lte", "normalized_value": "country Entry Level", "unit": "WNMT score", "applies_to": "Weighted Number of Medicinal Treatments", "basis": "explicit", "source_segment_ids": [requirement_segments["5.2.6"]["indicator_segment"]]}],
        "5.2.7": [
            {"raw_text": "25% per 2 years", "operator": "eq", "normalized_value": 25, "unit": "%", "applies_to": "reduction in Weighted Number of Medicinal Treatments every two years", "basis": "explicit", "source_segment_ids": [requirement_segments["5.2.7"]["indicator_segment"]]},
            {"raw_text": "at or below the Global Level", "operator": "lte", "normalized_value": "Global Level", "unit": "WNMT score", "applies_to": "Weighted Number of Medicinal Treatments", "basis": "explicit", "source_segment_ids": [requirement_segments["5.2.7"]["indicator_segment"]]},
        ],
    }
    conditions = {
        "5.1.6": [{"text": "for farms with total mortality > 6%", "applies_to": "maximum unexplained mortality requirement"}],
        "5.2.7": [
            {"text": "after achieving indicator 5.2.6", "applies_to": "25% reduction requirement"},
            {"text": "until the WNMT is at or below the Global Level", "applies_to": "continuation of the two-year reduction requirement"},
        ],
        "5.2.11": [{"text": "that a pathogen or disease is present before prescribing medication", "applies_to": "the designated veterinarian's certification"}],
    }
    dates = {
        "5.1.6": [
            {"text": "each of the previous two production cycles", "applies_to": "maximum unexplained mortality rate"},
            {"text": "the most recent complete production cycle", "applies_to": "applicability based on total mortality"},
        ],
        "5.1.7": [{"text": "annual targets", "applies_to": "reductions in mortalities and unexplained mortalities"}],
        "5.2.1": [{"text": "during the most recent production cycle", "applies_to": "documented chemical and therapeutant use"}],
        "5.2.5": [{"text": "for each production cycle", "applies_to": "public reporting of the Weighted Number of Medicinal Treatments"}],
        "5.2.7": [{"text": "per 2 years", "applies_to": "25% reduction in Weighted Number of Medicinal Treatments"}],
        "5.2.10": [{"text": "annually", "applies_to": "monitoring parasiticide residue levels"}],
        "5.2.11": [{"text": "before prescribing medication", "applies_to": "certification that a pathogen or disease is present"}],
    }
    cross_refs = {
        "5.1.7": [("5.1.1", "Indicator 5.1.1", "internal_exact")],
        "5.2.1": [("[83]", "footnote 83", "internal_exact"), ("[84]", "footnote 84", "internal_exact"), ("Appendix VI", "Appendix VI", "internal_exact")],
        "5.2.2": [("[85]", "footnote 85", "internal_exact"), ("[86]", "footnote 86", "internal_exact")],
        "5.2.5": [("Appendix VI", "Appendix VI", "internal_exact"), ("Appendix VII", "Appendix VII", "internal_exact")],
        "5.2.6": [("[83]", "footnote 83", "internal_exact"), ("Appendix VI", "Appendix VI", "internal_exact"), ("Appendix VII", "Appendix VII", "internal_exact")],
        "5.2.7": [("5.2.6", "Indicator 5.2.6", "internal_exact"), ("[83]", "footnote 83", "internal_exact"), ("Appendix VI", "Appendix VI", "internal_exact"), ("Appendix VII", "Appendix VII", "internal_exact")],
        "5.2.8": [("Appendix VII", "Appendix VII", "internal_exact")],
        "5.2.10": [("[83]", "footnote 83", "internal_exact"), ("Appendix VI", "Appendix VI", "internal_exact"), ("QA 111", "ASC interpretation platform QA0111", "external_document")],
        "5.2.11": [("[88]", "footnote 88", "internal_exact")],
    }
    subjects = {
        "5.2.5": ["The farm"],
        "5.2.6": ["The Weighted Number of Medicinal Treatments"],
        "5.2.7": ["The farm"],
        "5.2.8": ["The farm"],
        "5.2.9": ["The farm"],
        "5.2.10": ["The farm"],
        "5.2.11": ["The designated veterinarian"],
    }
    modalities = {
        rid: [{"token": "shall", "type": "obligation", "scope": strip_label(str(requirement_segments[rid]["indicator"]), "Indicator").split(" shall ", 1)[1]}]
        for rid in ("5.2.5", "5.2.6", "5.2.7", "5.2.8", "5.2.9", "5.2.10")
    }
    modalities["5.2.9"].append({"token": "need to", "type": "obligation", "scope": "be approved by a authorised veterinarian"})
    modalities["5.2.11"] = [{"token": "must", "type": "obligation", "scope": "certify that a pathogen or disease is present before prescribing medication"}]
    instructions = {
        "5.1.7": [{"marker": "Note", "text": joined(ids(16, 139)), "effect": "method", "source_segment_ids": [note_517_id]}],
        "5.2.1": [{"marker": None, "text": segments[[item["segment_id"] for item in segments].index(instruction_52_id)]["source_text"], "effect": "method", "source_segment_ids": [instruction_52_id]}],
        "5.2.10": [{"marker": "Note Indicator 5.2.10", "text": joined(span(17, 100, 101)), "effect": "method", "source_segment_ids": [note_5210_id]}],
    }
    source_anomalies = {
        "5.2.5": ["client_action_source_typo:5..2.1a", "client_action_acronym_inconsistency:WNMT/WMNT"],
        "5.2.7": ["client_and_auditor_action_acronym_inconsistency:WNMT/WMNT"],
        "5.2.8": ["auditor_action_source_typo:IMP"],
        "5.2.9": ["source_grammar:shall_public_present", "source_grammar:a_authorised", "auditor_action_marker_lowercase:a"],
        "5.2.10": ["client_action_source_grammar:collections_stations", "client_action_source_grammar:analysed_an_independent_laboratory"],
    }

    requirements: list[dict] = []
    for row in ROWS:
        rid = row["rid"]
        metadata = requirement_segments[rid]
        indicator = str(metadata["indicator"])
        value = str(metadata["value"])
        applicability = str(metadata["applicability"])
        normative = f"Indicator: {indicator}\nRequirement: {value}\nApplicability: {applicability}"
        direct = list(metadata["direct"])
        footnote_refs: list[dict] = []
        for marker in FOOTNOTE_OWNERS.get(rid, []):
            segment_id, _line_ids, link_type = FOOTNOTES[marker]
            direct.append(segment_id)
            footnote_refs.append({"marker": marker, "text": footnote_text[marker], "link_type": link_type, "source_segment_ids": [segment_id]})
        related: list[str] = []
        if rid.startswith("5.2."):
            related.append(criterion_id)
        if rid == "5.1.7":
            related.append(note_517_id)
        if rid == "5.2.1":
            related.append(instruction_52_id)
        if rid == "5.2.10":
            related.append(note_5210_id)
        clause_list = [{"clause_id": f"{rid}-main", "parent_clause_id": None, "marker": None, "text": normative, "joins_next": None}]
        if rid == "5.2.5":
            clause_list = [
                {"clause_id": "5.2.5-main", "parent_clause_id": None, "marker": None, "text": "The farm shall publicly report (via Appendix VI) the following:", "joins_next": None},
                {"clause_id": "5.2.5-1", "parent_clause_id": "5.2.5-main", "marker": "1", "text": "Weighted Number of Medicinal Treatments (see Appendix VII) for each production cycle", "joins_next": None},
                {"clause_id": "5.2.5-2", "parent_clause_id": "5.2.5-main", "marker": "2", "text": "The parasiticide load for each agent over the production cycle", "joins_next": None},
                {"clause_id": "5.2.5-3", "parent_clause_id": "5.2.5-main", "marker": "3", "text": "The benthic parasiticide residue levels", "joins_next": None},
            ]
        requirements.append(
            {
                "requirement_id": rid,
                "requirement_form": "audit_matrix",
                "criterion_path": ["Principle 5", "Criterion 5.1" if rid.startswith("5.1.") else "Criterion 5.2"],
                "language": "en",
                "indicator_text": indicator,
                "requirement_value": value,
                "normative_text": normative,
                "normative_subjects": subjects.get(rid, []),
                "applicability": [applicability],
                "modalities": modalities.get(rid, []),
                "negations": ([{"text": value, "applies_to": lower_initial(re.sub(r"\s*\[\d+\]", "", indicator))}] if value.casefold() in {"none", "no"} else []),
                "clauses": clause_list,
                "conditions": conditions.get(rid, []),
                "exceptions": [],
                "exemptions": [],
                "thresholds": thresholds.get(rid, []),
                "dates": dates.get(rid, []),
                "cross_references": [{"text": text, "target": target, "type": ref_type} for text, target, ref_type in cross_refs.get(rid, [])],
                "footnote_refs": footnote_refs,
                "associated_instructions": instructions.get(rid, []),
                "client_actions": action_objects[rid][0],
                "auditor_actions": action_objects[rid][1],
                "related_context_ids": related,
                "source_segment_ids": direct,
                "source_anomalies": source_anomalies.get(rid, []),
                "gold_notes": ["The formal Requirement is the audit-matrix combination of indicator_text, requirement_value and applicability; client and CAB actions remain separate provenance fields."],
            }
        )

    client_segment_ids = [item["source_segment_ids"][0] for requirement in requirements for item in requirement["client_actions"]]
    auditor_segment_ids = [item["source_segment_ids"][0] for requirement in requirements for item in requirement["auditor_actions"]]
    document = {
        "schema_version": "3.0",
        "gold_revision": 1,
        "supersedes": None,
        "supersedes_sha256": None,
        "revision_reason": "Initial frozen annotation selected before source inspection and created before any current parser prediction for pages 17-18 was run.",
        "sample_id": "audit-manual-p017-p018-round7-holdout",
        "source": {"file_name": source["source"]["file_name"], "sha256": source["source"]["sha256"], "language": "en", "document_family": "audit_manual", "page_count": source["source"]["page_count"]},
        "sample": {"round_id": "goal04-round7", "split": "holdout", "page_numbers": [17, 18], "selection_rationale": "Untouched dense audit-matrix window containing thirteen formal Requirement rows, Yes/None/percentage/inequality values, linked footnotes, shared and row-specific instructions, numbered clauses, client/CAB actions, source anomalies, and cross-page semantic footnote ownership."},
        "annotation": {"status": "frozen", "frozen_at": "2026-08-28", "verification": ["visual_page", "native_text", "second_annotator"], "notes": ["Frozen before any parser prediction or current output for pages 17-18 was inspected.", "Pass 1 transcribed all formal cells, action cells, footnotes and instructions from native source lines while checking the rendered pages.", "Pass 2 independently reconciled the 13-ID sequence, 34 client actions, 35 CAB actions, direct bboxes, footnote ownership and source anomalies against the source-only evidence.", "The dash in the 5.2.2 client-action column is a visual placeholder and is not annotated as an action.", "Source typos and the lowercase 5.2.9 CAB marker are preserved as evidence rather than silently corrected."]},
        "segments": segments,
        "requirements": requirements,
        "excluded_regions": [
            {"source_segment_ids": footer_ids, "classification": "header_footer", "reason": "Repeated footer branding, copyright and page numbers are not Requirement content."},
            {"source_segment_ids": [criterion_id, table_header_id], "classification": "other_non_requirement", "reason": "Criterion and matrix column headings establish hierarchy and roles but are not formal Requirement evidence."},
            {"source_segment_ids": [note_517_id, instruction_52_id, note_5210_id], "classification": "other_non_requirement", "reason": "Notes and instructions are preserved through associated_instructions but remain outside the formal Requirement cells."},
            {"source_segment_ids": client_segment_ids, "classification": "client_action", "reason": "Required client actions are linked to their Requirement but never merged into normative_text."},
            {"source_segment_ids": auditor_segment_ids, "classification": "auditor_action", "reason": "Required CAB actions are linked in an independent provenance bucket and never merged into normative_text or client actions."},
        ],
        "summary": {"requirement_count": len(requirements), "cross_page_requirement_count": sum(len({next(segment["page_number"] for segment in segments if segment["segment_id"] == segment_id) for segment_id in requirement["source_segment_ids"]}) > 1 for requirement in requirements), "client_action_count": sum(len(requirement["client_actions"]) for requirement in requirements), "auditor_action_count": sum(len(requirement["auditor_actions"]) for requirement in requirements), "critical_gold_ambiguities": []},
    }
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(OUTPUT_PATH.relative_to(ROOT)), "requirements": len(requirements), "client_actions": document["summary"]["client_action_count"], "auditor_actions": document["summary"]["auditor_action_count"], "cross_page_requirements": document["summary"]["cross_page_requirement_count"]}, indent=2))


if __name__ == "__main__":
    main()
