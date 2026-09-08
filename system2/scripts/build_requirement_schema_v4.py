from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "gold/requirements/schema-v3.json"
OUTPUT = ROOT / "gold/requirements/schema-v4.json"


def build_schema() -> dict[str, object]:
    schema = json.loads(SOURCE.read_text(encoding="utf-8"))
    schema["$id"] = (
        "https://local.pdf-extraction-product/requirement-gold-v4.schema.json"
    )
    schema["title"] = "Requirement Gold v4 with source-backed semantic scope"
    schema["properties"]["schema_version"] = {"const": "4.0"}
    definitions = schema["$defs"]
    definitions["sourceAnchor"] = {
        "type": "object",
        "additionalProperties": False,
        "required": ["source_segment_id", "start_char", "end_char", "text"],
        "properties": {
            "source_segment_id": {"type": "string", "minLength": 1},
            "start_char": {"type": "integer", "minimum": 0},
            "end_char": {"type": "integer", "minimum": 1},
            "text": {"type": "string", "minLength": 1},
        },
    }
    definitions["scopeRef"] = {
        "type": "object",
        "additionalProperties": False,
        "required": ["kind", "target", "anchors"],
        "properties": {
            "kind": {
                "enum": [
                    "source_span",
                    "field",
                    "clause",
                    "requirement",
                    "action",
                    "footnote",
                ]
            },
            "target": {
                "type": "string",
                "pattern": (
                    "^(indicator_text|requirement_value|applicability|"
                    "normative_text|clause:.+|requirement:.+|client:.+|"
                    "auditor:.+|footnote:.+)$"
                ),
            },
            "anchors": {
                "type": "array",
                "minItems": 1,
                "items": {"$ref": "#/$defs/sourceAnchor"},
            },
        },
    }
    definitions["textEvidence"] = {
        "type": "object",
        "additionalProperties": False,
        "required": ["text", "basis", "source_segment_ids", "anchors"],
        "properties": {
            "text": {"type": "string", "minLength": 1},
            "basis": {"enum": ["explicit", "inferred_from_source_structure"]},
            "source_segment_ids": {
                "type": "array",
                "minItems": 1,
                "items": {"type": "string"},
            },
            "anchors": {
                "type": "array",
                "minItems": 1,
                "items": {"$ref": "#/$defs/sourceAnchor"},
            },
        },
    }
    for name in ("modality", "scopedText", "threshold"):
        definitions[name]["required"].append("scope_ref")
        definitions[name]["properties"]["scope_ref"] = {
            "$ref": "#/$defs/scopeRef"
        }
    requirement = definitions["requirement"]
    requirement["required"].extend(
        ["normative_subject_evidence", "applicability_evidence"]
    )
    evidence_array = {
        "type": "array",
        "items": {"$ref": "#/$defs/textEvidence"},
    }
    requirement["properties"]["normative_subject_evidence"] = evidence_array
    requirement["properties"]["applicability_evidence"] = evidence_array
    return schema


def main() -> None:
    OUTPUT.write_text(
        json.dumps(build_schema(), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
