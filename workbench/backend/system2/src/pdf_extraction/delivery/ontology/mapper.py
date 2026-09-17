from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from pyshacl import validate
from rdflib import Graph, Literal, Namespace, RDF, RDFS, URIRef
from rdflib.namespace import SH, XSD

from ...domains.regulatory import RegulatoryIRDocument


@dataclass(frozen=True)
class OntologyValidationResult:
    conforms: bool
    report_text: str
    violation_count: int
    violating_focus_nodes: list[str]


def _uri(namespace: Namespace, value: str) -> URIRef:
    return namespace[value.replace(":", "_").replace("/", "_")]


def build_tbox(namespace: str) -> Graph:
    ns = Namespace(namespace)
    graph = Graph()
    graph.bind("reg", ns)
    for class_name in ("RegulatoryDocument", "RegulatoryStatement"):
        graph.add((ns[class_name], RDF.type, RDFS.Class))
    for prop in (
        "hasStatement", "regulatedEntity", "modality", "action", "object",
        "condition", "exception", "threshold", "jurisdiction", "effectiveDate",
        "crossReference", "sourceBlock", "sourceSegment", "sourcePage", "confidence",
    ):
        graph.add((ns[prop], RDF.type, RDF.Property))
    return graph


def map_ir_to_rdf(ir: RegulatoryIRDocument, namespace: str) -> Graph:
    ns = Namespace(namespace)
    graph = build_tbox(namespace)
    document_uri = _uri(ns, ir.document_id)
    graph.add((document_uri, RDF.type, ns.RegulatoryDocument))
    for statement in ir.statements:
        subject = _uri(ns, statement.id)
        graph.add((subject, RDF.type, ns.RegulatoryStatement))
        graph.add((document_uri, ns.hasStatement, subject))
        values = {
            "regulatedEntity": statement.regulated_entity,
            "modality": statement.modality,
            "action": statement.action,
            "object": statement.object,
            "condition": statement.condition,
            "exception": statement.exception,
            "threshold": statement.threshold,
            "jurisdiction": statement.jurisdiction,
            "effectiveDate": statement.effective_date,
        }
        for predicate, value in values.items():
            if value is not None:
                graph.add((subject, ns[predicate], Literal(value)))
        for value in statement.cross_references:
            graph.add((subject, ns.crossReference, Literal(value)))
        for value in statement.source_block_ids:
            graph.add((subject, ns.sourceBlock, Literal(value)))
        for value in statement.source_segment_ids:
            graph.add((subject, ns.sourceSegment, Literal(value)))
        for value in statement.source_page_indices:
            graph.add((subject, ns.sourcePage, Literal(value, datatype=XSD.integer)))
        graph.add((subject, ns.confidence, Literal(statement.confidence, datatype=XSD.decimal)))
    return graph


def build_shapes(namespace: str) -> Graph:
    ns = Namespace(namespace)
    shapes = Graph()
    shape = ns.RegulatoryStatementShape
    shapes.add((shape, RDF.type, SH.NodeShape))
    shapes.add((shape, SH.targetClass, ns.RegulatoryStatement))
    # Canonical Requirement v1.3 is assembled directly from native evidence and
    # may not map to one layout block. Segment/page provenance remains required;
    # sourceBlock is retained when available for backward compatibility.
    for predicate in (ns.modality, ns.sourceSegment, ns.sourcePage):
        prop = URIRef(f"{shape}/{predicate.split('/')[-1]}")
        shapes.add((shape, SH.property, prop))
        shapes.add((prop, SH.path, predicate))
        shapes.add((prop, SH.minCount, Literal(1)))
    return shapes


def validate_graph(graph: Graph, namespace: str) -> OntologyValidationResult:
    conforms, report_graph, report_text = validate(
        data_graph=graph,
        shacl_graph=build_shapes(namespace),
        ont_graph=build_tbox(namespace),
        inference="rdfs",
        abort_on_first=False,
        allow_infos=False,
        allow_warnings=False,
    )
    focus_nodes = sorted({str(value) for value in report_graph.objects(None, SH.focusNode)})
    violation_count = sum(1 for _ in report_graph.subjects(RDF.type, SH.ValidationResult))
    return OntologyValidationResult(bool(conforms), str(report_text), violation_count, focus_nodes)


def export_ontology(
    ir: RegulatoryIRDocument,
    output_dir: str | Path,
    namespace: str,
) -> tuple[Path, Path, Path, OntologyValidationResult]:
    target = Path(output_dir)
    target.mkdir(parents=True, exist_ok=True)
    graph = map_ir_to_rdf(ir, namespace)
    ttl_path = target / "regulatory.ttl"
    graph.serialize(destination=ttl_path, format="turtle")
    tbox_path = target / "tbox.ttl"
    build_tbox(namespace).serialize(destination=tbox_path, format="turtle")
    shapes_path = target / "shapes.ttl"
    build_shapes(namespace).serialize(destination=shapes_path, format="turtle")
    result = validate_graph(graph, namespace)
    report_path = target / "shacl-report.json"
    report_path.write_text(json.dumps({
        "conforms": result.conforms,
        "violation_count": result.violation_count,
        "violating_focus_nodes": result.violating_focus_nodes,
        "report_text": result.report_text,
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    return ttl_path, shapes_path, report_path, result
