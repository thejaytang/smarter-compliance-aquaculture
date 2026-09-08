import ast
from pathlib import Path


PACKAGE_ROOT = Path(__file__).resolve().parents[2] / "src" / "pdf_extraction"


def _parent_package_imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.level >= 2:
            imports.add(node.module or "")
    return imports


def test_contracts_do_not_depend_on_runtime_orchestration() -> None:
    forbidden = {"orchestration", "delivery", "verification", "extraction"}
    for path in (PACKAGE_ROOT / "contracts").glob("*.py"):
        assert not (_parent_package_imports(path) & forbidden), path


def test_verification_does_not_import_orchestrator_or_extractor_decisions() -> None:
    forbidden = {"orchestration", "pipeline", "parsers", "assemble", "reconcile"}
    for path in (PACKAGE_ROOT / "verification").glob("*.py"):
        assert not (_parent_package_imports(path) & forbidden), path
