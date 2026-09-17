"""Canonical implementation of the Requirement domain."""

from .canonical import (
    apply_family_trust,
    canonicalize_native_requirement,
    canonicalize_native_requirements,
    parse_english_modalities,
)
from .clauses import ClauseBuildResult, build_requirement_clauses
from .footnotes import (
    FootnoteDefinition,
    detect_page_footnote_definitions,
    detect_table_footnote_definitions,
    link_requirement_footnotes,
)
from .hierarchy import (
    HierarchyHeading,
    HierarchyKind,
    RequirementHierarchyProfile,
    bind_requirement_hierarchy,
    learn_requirement_hierarchy_profile,
)
from .native_assembler import (
    NativeFootnoteLinkCandidate,
    NativeRequirement,
    NativeRequirementAssembler,
    RequirementSourceSpan,
    TemplateFamily,
    assemble_native_requirements,
)
from .profile import (
    FamilyProfileStatus,
    RequirementFamilyProfile,
    RequirementTemplateProfile,
    RoleXBand,
    learn_requirement_template_profile,
)

__all__ = [
    "NativeRequirement",
    "NativeRequirementAssembler",
    "RequirementSourceSpan",
    "TemplateFamily",
    "assemble_native_requirements",
    "FootnoteDefinition",
    "NativeFootnoteLinkCandidate",
    "detect_page_footnote_definitions",
    "detect_table_footnote_definitions",
    "link_requirement_footnotes",
    "FamilyProfileStatus",
    "RequirementFamilyProfile",
    "RequirementTemplateProfile",
    "RoleXBand",
    "learn_requirement_template_profile",
    "HierarchyHeading",
    "HierarchyKind",
    "RequirementHierarchyProfile",
    "bind_requirement_hierarchy",
    "learn_requirement_hierarchy_profile",
    "apply_family_trust",
    "canonicalize_native_requirement",
    "canonicalize_native_requirements",
    "parse_english_modalities",
    "ClauseBuildResult",
    "build_requirement_clauses",
]
