from pathlib import Path

from tests.support.paths import PROJECT_ROOT


PACKAGE_ROOT = PROJECT_ROOT / "src" / "pdf_extraction"


def test_legacy_namespaces_are_facades_not_parallel_implementations() -> None:
    for name in ("requirements", "regulatory_ir", "export", "ontology"):
        python_files = {
            path.name
            for path in (PACKAGE_ROOT / name).glob("*.py")
        }
        assert python_files == {"__init__.py"}, name


def test_domain_and_delivery_compatibility_paths_share_implementations() -> None:
    from pdf_extraction.delivery import export_markdown as new_markdown
    from pdf_extraction.domains.regulatory import extract_regulatory_ir as new_ir
    from pdf_extraction.domains.requirements import NativeRequirementAssembler as new_req
    from pdf_extraction.export import export_markdown as old_markdown
    from pdf_extraction.regulatory_ir import extract_regulatory_ir as old_ir
    from pdf_extraction.requirements import NativeRequirementAssembler as old_req

    assert new_markdown is old_markdown
    assert new_ir is old_ir
    assert new_req is old_req


def test_internal_code_does_not_depend_on_legacy_namespace_facades() -> None:
    forbidden = (
        "from ..requirements import",
        "from ..regulatory_ir import",
        "from ..export import",
        "from ..ontology import",
        "from ..derived import",
    )
    excluded = {
        PACKAGE_ROOT / "requirements" / "__init__.py",
        PACKAGE_ROOT / "regulatory_ir" / "__init__.py",
        PACKAGE_ROOT / "export" / "__init__.py",
        PACKAGE_ROOT / "ontology" / "__init__.py",
        PACKAGE_ROOT / "derived.py",
    }
    violations: list[str] = []
    for path in PACKAGE_ROOT.rglob("*.py"):
        if path in excluded:
            continue
        content = path.read_text(encoding="utf-8")
        if any(token in content for token in forbidden):
            violations.append(str(path.relative_to(PACKAGE_ROOT)))
    assert violations == []
