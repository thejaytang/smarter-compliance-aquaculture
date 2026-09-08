from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

from pdf_extraction.evaluation.requirement_gold import load_requirement_gold


ROOT = Path(__file__).resolve().parents[1]
GOLD_ROOT = ROOT / "gold" / "requirements"
SOURCE = GOLD_ROOT / "annotations" / "interpretation-manual-p080-p082-round8-holdout.json"
TARGET = GOLD_ROOT / "annotations" / "interpretation-manual-p080-p082-round8-holdout-v2.json"
SCHEMA = GOLD_ROOT / "schema-v4.json"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _anchor(segment_id: str, start: int, end: int, text: str) -> dict[str, object]:
    return {
        "source_segment_id": segment_id,
        "start_char": start,
        "end_char": end,
        "text": text,
    }


def _scope(kind: str, target: str, anchor: dict[str, object]) -> dict[str, object]:
    return {"kind": kind, "target": target, "anchors": [anchor]}


def main() -> None:
    source = json.loads(SOURCE.read_text(encoding="utf-8"))
    revised = copy.deepcopy(source)
    revised.update(
        {
            "gold_revision": 2,
            "supersedes": "annotations/interpretation-manual-p080-p082-round8-holdout.json",
            "supersedes_sha256": _sha256(SOURCE),
            "revision_reason": (
                "Post-blind source adjudication corrects v4 scope targets, stable criterion identity, "
                "the explicit footnote-11 negation/date, resolved footnote-marker references, and "
                "Requirement-target anchors. Frozen source segments, sample window and exclusions are unchanged."
            ),
        }
    )
    revised["annotation"]["notes"].extend(
        [
            "Revision 2 was created after blind scoring exposed annotation-contract defects; the original Gold and blind report remain immutable evidence.",
            "Modal scope anchors now target the exact governed predicate rather than the entire normative field.",
            "Requirement-scoped exemptions anchor the printed Requirement ID; footnote 11 also carries an explicit negation and a time-bounded date phrase.",
            "criterion_path uses stable semantic identities; the full Criterion title remains source evidence.",
        ]
    )

    requirements = {item["requirement_id"]: item for item in revised["requirements"]}
    for requirement in requirements.values():
        requirement["criterion_path"] = ["Principle 2", "Criterion 2.5"]

    r251 = requirements["2.5.1"]
    predicate_251 = (
        "determine benthic status, following the method outlined in Appendix 7 "
        "(7.2.1, 7.3.1, 7.4.1, 7.7)"
    )
    r251["modalities"][0]["scope"] = predicate_251
    r251["modalities"][0]["scope_ref"] = _scope(
        "source_span",
        "normative_text",
        _anchor("p80-r2.5.1-normative", 14, 110, predicate_251),
    )
    r251["exemptions"][0]["scope_ref"] = _scope(
        "requirement",
        "requirement:2.5.1",
        _anchor("p80-r2.5.1-id", 0, 5, "2.5.1"),
    )
    r251["cross_references"] = [
        {"text": "[10]", "target": "footnote 10", "type": "internal_exact"},
        {
            "text": "Appendix 7 (7.2.1, 7.3.1, 7.4.1, 7.7)",
            "target": "Appendix 7 (7.2.1, 7.3.1, 7.4.1, 7.7)",
            "type": "internal_exact",
        },
    ]

    r252 = requirements["2.5.2"]
    predicate_252 = (
        "demonstrate an 'Acceptable' benthic status, following the method outlined in "
        "Appendix 7 (7.2.2, 7.3.2, 7.4.2)"
    )
    r252["modalities"][0]["scope"] = predicate_252
    r252["modalities"][0]["scope_ref"] = _scope(
        "source_span",
        "normative_text",
        _anchor("p80-r2.5.2-normative", 14, 123, predicate_252),
    )
    r252["negations"] = [
        {
            "text": "is not required",
            "applies_to": "demonstration that the status is 'Acceptable'",
            "scope_ref": _scope(
                "footnote",
                "footnote:11",
                _anchor(
                    "p80-footnote-11",
                    141,
                    186,
                    "demonstration that the status is 'Acceptable'",
                ),
            ),
        }
    ]
    r252["exemptions"][0]["scope_ref"] = _scope(
        "requirement",
        "requirement:2.5.2",
        _anchor("p80-r2.5.2-id", 0, 5, "2.5.2"),
    )
    r252["dates"] = [
        {
            "text": "for the first three years of the ASC Farm Standard being effective",
            "applies_to": "demonstration that the status is 'Acceptable' is not required",
            "scope_ref": _scope(
                "footnote",
                "footnote:11",
                _anchor(
                    "p80-footnote-11",
                    141,
                    202,
                    "demonstration that the status is 'Acceptable' is not required",
                ),
            ),
        }
    ]
    r252["cross_references"] = [
        {"text": "[11]", "target": "footnote 11", "type": "internal_exact"},
        {
            "text": "Appendix 7 (7.2.2, 7.3.2, 7.4.2)",
            "target": "Appendix 7 (7.2.2, 7.3.2, 7.4.2)",
            "type": "internal_exact",
        },
        {"text": "Indicator 2.5.1", "target": "2.5.1", "type": "internal_exact"},
    ]

    r253 = requirements["2.5.3"]
    predicate_253_a = (
        "ensure that the person conducting sediment sampling and analysis "
        "(see Indicator 2.5.1) is independent and has the necessary competencies, "
        "experience and training"
    )
    predicate_253_b = (
        "ensure that the person conducting the sampling and analysis complies with these requirements"
    )
    r253["modalities"][0]["scope"] = predicate_253_a
    r253["modalities"][0]["scope_ref"] = _scope(
        "source_span",
        "normative_text",
        _anchor("p80-r2.5.3-normative", 14, 175, predicate_253_a),
    )
    r253["modalities"][1]["scope"] = predicate_253_b
    r253["modalities"][1]["scope_ref"] = _scope(
        "source_span",
        "normative_text",
        _anchor("p80-r2.5.3-normative", 243, 335, predicate_253_b),
    )
    r253["conditions"] = [
        {
            "text": "In cases where regulatory requirements are defined",
            "applies_to": predicate_253_b,
            "scope_ref": _scope(
                "source_span",
                "normative_text",
                _anchor("p80-r2.5.3-normative", 243, 335, predicate_253_b),
            ),
        }
    ]

    revised["summary"]["critical_gold_ambiguities"] = [
        "The shared interpretation block follows a three-row Requirement group. It is retained as related context for all three rows, while its modal-bearing sentences remain explicitly excluded from formal Requirement inventory."
    ]

    TARGET.write_text(
        json.dumps(revised, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    load_requirement_gold(TARGET, SCHEMA)
    print(_sha256(TARGET))


if __name__ == "__main__":
    main()
