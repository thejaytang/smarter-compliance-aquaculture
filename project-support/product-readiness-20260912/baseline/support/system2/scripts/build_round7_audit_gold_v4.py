from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PREDECESSOR = (
    ROOT
    / "gold/requirements/annotations/audit-manual-p017-p018-round7-holdout.json"
)
OUTPUT = (
    ROOT
    / "gold/requirements/annotations/audit-manual-p017-p018-round7-holdout-v4.json"
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _anchor(
    segments: dict[str, dict[str, Any]], segment_id: str, text: str
) -> dict[str, Any]:
    source = segments[segment_id]["source_text"]
    occurrences = source.count(text)
    if occurrences != 1:
        raise ValueError(
            f"expected one exact occurrence of {text!r} in {segment_id}, got {occurrences}"
        )
    start = source.index(text)
    return {
        "source_segment_id": segment_id,
        "start_char": start,
        "end_char": start + len(text),
        "text": text,
    }


def _scope(
    segments: dict[str, dict[str, Any]],
    *,
    kind: str,
    target: str,
    segment_id: str,
    text: str,
) -> dict[str, Any]:
    return {
        "kind": kind,
        "target": target,
        "anchors": [_anchor(segments, segment_id, text)],
    }


def _modality(
    segments: dict[str, dict[str, Any]],
    *,
    token: str,
    scope_text: str,
    segment_id: str,
    target: str = "indicator_text",
    kind: str = "source_span",
) -> dict[str, Any]:
    return {
        "token": token,
        "type": "obligation",
        "scope": scope_text,
        "scope_ref": _scope(
            segments,
            kind=kind,
            target=target,
            segment_id=segment_id,
            text=scope_text,
        ),
    }


def _scoped_text(
    segments: dict[str, dict[str, Any]],
    *,
    text: str,
    applies_to: str,
    segment_id: str,
    target: str = "indicator_text",
    kind: str = "source_span",
) -> dict[str, Any]:
    return {
        "text": text,
        "applies_to": applies_to,
        "scope_ref": _scope(
            segments,
            kind=kind,
            target=target,
            segment_id=segment_id,
            text=applies_to,
        ),
    }


def _threshold(
    segments: dict[str, dict[str, Any]],
    *,
    raw_text: str,
    operator: str,
    normalized_value: float | str,
    unit: str | None,
    source_segment_id: str,
    applies_to: str,
    scope_segment_id: str,
    target: str,
    kind: str,
) -> dict[str, Any]:
    if raw_text not in segments[source_segment_id]["source_text"]:
        raise ValueError(
            f"threshold {raw_text!r} is absent from {source_segment_id}"
        )
    return {
        "raw_text": raw_text,
        "operator": operator,
        "normalized_value": normalized_value,
        "unit": unit,
        "applies_to": applies_to,
        "basis": "explicit",
        "source_segment_ids": [source_segment_id],
        "scope_ref": _scope(
            segments,
            kind=kind,
            target=target,
            segment_id=scope_segment_id,
            text=applies_to,
        ),
    }


def _evidence(
    segments: dict[str, dict[str, Any]],
    *,
    text: str,
    segment_id: str,
    anchor_text: str | None = None,
    basis: str = "explicit",
) -> dict[str, Any]:
    exact = anchor_text or text
    return {
        "text": text,
        "basis": basis,
        "source_segment_ids": [segment_id],
        "anchors": [_anchor(segments, segment_id, exact)],
    }


def build_gold() -> dict[str, Any]:
    predecessor = json.loads(PREDECESSOR.read_text(encoding="utf-8"))
    result = deepcopy(predecessor)
    segments = {item["segment_id"]: item for item in result["segments"]}
    requirements = {
        item["requirement_id"]: item for item in result["requirements"]
    }

    result.update(
        {
            "schema_version": "4.0",
            "gold_revision": 2,
            "supersedes": (
                "annotations/audit-manual-p017-p018-round7-holdout.json"
            ),
            "supersedes_sha256": _sha256(PREDECESSOR),
            "revision_reason": (
                "Migrate semantic scope to source-exact v4 anchors and correct "
                "source-adjudicated condition, date, threshold and clause boundaries "
                "without changing the source window, source segments or exclusions."
            ),
        }
    )
    result["annotation"]["notes"].extend(
        [
            "Revision 2 preserves every predecessor source segment and excluded region byte-for-structure; only semantic representation and the one non-source-exact 5.2.5 clause label are revised.",
            "All v4 scope anchors were recomputed against the frozen segment text after a separate rendered-page review of pages 17-18.",
            "5.1.6 retains one applicability threshold (> 6%) plus its explicit condition; the repeated wording in the Indicator and Applicability cells is not double-counted as two legal thresholds.",
            "5.2.4 'after treatments' modifies withholding periods and is not annotated as a conditional trigger.",
            "5.2.5 includes both source-explicit production-cycle temporal scopes.",
            "5.2.11 removes the predecessor's complement-clause false condition while retaining the source-explicit before-prescribing temporal scope from footnote 88.",
        ]
    )

    for requirement in requirements.values():
        requirement["modalities"] = []
        requirement["negations"] = []
        requirement["conditions"] = []
        requirement["exceptions"] = []
        requirement["exemptions"] = []
        requirement["thresholds"] = []
        requirement["dates"] = []
        requirement["normative_subject_evidence"] = []
        applicability_segment = next(
            segment_id
            for segment_id in requirement["source_segment_ids"]
            if segments[segment_id]["role"] == "applicability"
        )
        requirement["applicability_evidence"] = [
            _evidence(
                segments,
                text=value,
                segment_id=applicability_segment,
            )
            for value in requirement["applicability"]
        ]

    subject_sources = {
        "5.2.5": ("p18-r5.2.5-indicator", "The farm"),
        "5.2.6": (
            "p18-r5.2.6-indicator",
            "The Weighted Number of Medicinal Treatments",
        ),
        "5.2.7": ("p18-r5.2.7-indicator", "The farm"),
        "5.2.8": ("p18-r5.2.8-indicator", "The farm"),
        "5.2.9": ("p18-r5.2.9-indicator", "The farm"),
        "5.2.10": ("p18-r5.2.10-indicator", "The farm"),
        "5.2.11": ("p18-footnote-88", "The designated veterinarian"),
    }
    for requirement_id, (segment_id, subject) in subject_sources.items():
        requirement = requirements[requirement_id]
        if requirement["normative_subjects"] != [subject]:
            raise ValueError(f"unexpected v3 subject for {requirement_id}")
        requirement["normative_subject_evidence"] = [
            _evidence(segments, text=subject, segment_id=segment_id)
        ]

    requirements["5.1.6"]["conditions"] = [
        _scoped_text(
            segments,
            text="for farms with total mortality > 6%",
            applies_to=(
                "Maximum unexplained mortality rate from each of the previous "
                "two production cycles"
            ),
            segment_id="p17-r5.1.6-indicator",
        )
    ]
    requirements["5.1.6"]["thresholds"] = [
        _threshold(
            segments,
            raw_text="≤ 40% of total mortalities",
            operator="lte",
            normalized_value=40,
            unit="%",
            source_segment_id="p17-r5.1.6-value",
            applies_to="Maximum unexplained mortality rate",
            scope_segment_id="p17-r5.1.6-indicator",
            target="indicator_text",
            kind="field",
        ),
        _threshold(
            segments,
            raw_text="> 6% total mortality",
            operator="gt",
            normalized_value=6,
            unit="%",
            source_segment_id="p17-r5.1.6-applicability",
            applies_to=(
                "All farms with > 6% total mortality in the most recent complete "
                "production cycle."
            ),
            scope_segment_id="p17-r5.1.6-applicability",
            target="applicability",
            kind="field",
        ),
    ]
    requirements["5.1.6"]["dates"] = [
        _scoped_text(
            segments,
            text="each of the previous two production cycles",
            applies_to="Maximum unexplained mortality rate",
            segment_id="p17-r5.1.6-indicator",
        ),
        _scoped_text(
            segments,
            text="the most recent complete production cycle",
            applies_to="All farms with > 6% total mortality",
            segment_id="p17-r5.1.6-applicability",
            target="applicability",
        ),
    ]
    requirements["5.1.7"]["dates"] = [
        _scoped_text(
            segments,
            text="annual targets",
            applies_to=(
                "reductions in mortalities and reductions in unexplained mortalities"
            ),
            segment_id="p17-r5.1.7-indicator",
        )
    ]
    requirements["5.2.1"]["dates"] = [
        _scoped_text(
            segments,
            text="during the most recent production cycle",
            applies_to="chemicals [84] and therapeutants used",
            segment_id="p17-r5.2.1-indicator",
        )
    ]

    for requirement_id in ("5.2.2", "5.2.11"):
        indicator_segment = (
            f"p17-r{requirement_id}-indicator"
            if requirement_id == "5.2.2"
            else f"p18-r{requirement_id}-indicator"
        )
        indicator = segments[indicator_segment]["source_text"]
        requirements[requirement_id]["negations"] = [
            _scoped_text(
                segments,
                text="None",
                applies_to=indicator,
                segment_id=indicator_segment,
                kind="field",
            )
        ]

    indicator_523 = segments["p17-r5.2.3-indicator"]["source_text"]
    requirements["5.2.3"]["thresholds"] = [
        _threshold(
            segments,
            raw_text="100%",
            operator="eq",
            normalized_value=100,
            unit="%",
            source_segment_id="p17-r5.2.3-value",
            applies_to=indicator_523,
            scope_segment_id="p17-r5.2.3-indicator",
            target="indicator_text",
            kind="field",
        )
    ]

    requirements["5.2.5"]["modalities"] = [
        _modality(
            segments,
            token="shall",
            scope_text=(
                "publicly report (via Appendix VI) the: 1. Weighted Number of "
                "Medicinal Treatments (see Appendix VII) for each production cycle "
                "2. The parasiticide load for each agent over the production cycle "
                "3. The benthic parasiticide residue levels"
            ),
            segment_id="p18-r5.2.5-indicator",
        )
    ]
    requirements["5.2.5"]["dates"] = [
        _scoped_text(
            segments,
            text="for each production cycle",
            applies_to="Weighted Number of Medicinal Treatments (see Appendix VII)",
            segment_id="p18-r5.2.5-indicator",
        ),
        _scoped_text(
            segments,
            text="over the production cycle",
            applies_to="The parasiticide load for each agent",
            segment_id="p18-r5.2.5-indicator",
        ),
    ]
    requirements["5.2.5"]["clauses"][0]["text"] = (
        "The farm shall publicly report (via Appendix VI) the:"
    )

    requirements["5.2.6"]["modalities"] = [
        _modality(
            segments,
            token="shall",
            scope_text="be at or below the country Entry Level (see Appendix VII)",
            segment_id="p18-r5.2.6-indicator",
        )
    ]
    requirements["5.2.6"]["thresholds"] = [
        _threshold(
            segments,
            raw_text="at or below the country Entry Level",
            operator="lte",
            normalized_value="country Entry Level",
            unit=None,
            source_segment_id="p18-r5.2.6-indicator",
            applies_to="The Weighted Number of Medicinal Treatments",
            scope_segment_id="p18-r5.2.6-indicator",
            target="indicator_text",
            kind="source_span",
        )
    ]

    reduction_scope = "reduce the Weighted Number of Medicinal Treatments"
    requirements["5.2.7"]["modalities"] = [
        _modality(
            segments,
            token="shall",
            scope_text=reduction_scope,
            segment_id="p18-r5.2.7-indicator",
        )
    ]
    requirements["5.2.7"]["conditions"] = [
        _scoped_text(
            segments,
            text="after achieving indicator 5.2.6",
            applies_to=reduction_scope,
            segment_id="p18-r5.2.7-indicator",
        ),
        _scoped_text(
            segments,
            text=(
                "until the WNMT is at or below the Global Level (see Appendix VII)"
            ),
            applies_to=reduction_scope,
            segment_id="p18-r5.2.7-indicator",
        ),
    ]
    requirements["5.2.7"]["thresholds"] = [
        _threshold(
            segments,
            raw_text="25%",
            operator="eq",
            normalized_value=25,
            unit="%",
            source_segment_id="p18-r5.2.7-indicator",
            applies_to=reduction_scope,
            scope_segment_id="p18-r5.2.7-indicator",
            target="indicator_text",
            kind="source_span",
        ),
        _threshold(
            segments,
            raw_text="at or below the Global Level",
            operator="lte",
            normalized_value="Global Level",
            unit=None,
            source_segment_id="p18-r5.2.7-indicator",
            applies_to="the WNMT",
            scope_segment_id="p18-r5.2.7-indicator",
            target="indicator_text",
            kind="source_span",
        ),
    ]
    requirements["5.2.7"]["dates"] = [
        _scoped_text(
            segments,
            text="per 2 years",
            applies_to=reduction_scope,
            segment_id="p18-r5.2.7-indicator",
        )
    ]

    requirements["5.2.8"]["modalities"] = [
        _modality(
            segments,
            token="shall",
            scope_text=(
                "implement Integrated Pest Management (IPM) according to the "
                "guidance in Appendix VII"
            ),
            segment_id="p18-r5.2.8-indicator",
        )
    ]
    requirements["5.2.9"]["modalities"] = [
        _modality(
            segments,
            token="shall",
            scope_text=(
                "public present (e.g., via company website) the IPM-measures that "
                "the company applies"
            ),
            segment_id="p18-r5.2.9-indicator",
        ),
        _modality(
            segments,
            token="need to",
            scope_text="be approved by a authorised veterinarian",
            segment_id="p18-r5.2.9-indicator",
        ),
    ]
    requirements["5.2.10"]["modalities"] = [
        _modality(
            segments,
            token="shall",
            scope_text=(
                "monitor parasiticide residue levels annually in the benthic "
                "sediment directly outside the AZE"
            ),
            segment_id="p18-r5.2.10-indicator",
        )
    ]
    requirements["5.2.10"]["dates"] = [
        _scoped_text(
            segments,
            text="annually",
            applies_to="monitor parasiticide residue levels",
            segment_id="p18-r5.2.10-indicator",
        )
    ]

    requirements["5.2.11"]["modalities"] = [
        _modality(
            segments,
            token="must",
            scope_text=(
                "certify that a pathogen or disease is present before prescribing "
                "medication"
            ),
            segment_id="p18-footnote-88",
            target="footnote:88",
            kind="footnote",
        )
    ]
    requirements["5.2.11"]["dates"] = [
        _scoped_text(
            segments,
            text="before prescribing medication",
            applies_to="certify that a pathogen or disease is present",
            segment_id="p18-footnote-88",
            target="footnote:88",
            kind="footnote",
        )
    ]

    if result["segments"] != predecessor["segments"]:
        raise ValueError("v4 migration changed frozen source segments")
    if result["excluded_regions"] != predecessor["excluded_regions"]:
        raise ValueError("v4 migration changed frozen excluded regions")
    result["summary"]["critical_gold_ambiguities"] = []
    return result


def main() -> None:
    OUTPUT.write_text(
        json.dumps(build_gold(), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
