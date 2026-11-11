"""Automated architecture boundary tests enforcing Router -> Service -> Repository -> DB separation."""

import ast
from pathlib import Path


def _extract_imports(py_file: Path) -> set[str]:
    tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.add(alias.name)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module)
    return imports


def test_api_routes_never_import_sqlalchemy_orm_or_repositories() -> None:
    v1_dir = Path(__file__).resolve().parents[1] / "src" / "voc_intel" / "api" / "v1"
    route_files = [p for p in v1_dir.glob("*.py") if p.name != "__init__.py"]
    assert len(route_files) >= 5

    for rf in route_files:
        imports = _extract_imports(rf)
        for mod in imports:
            assert not mod.startswith("sqlalchemy"), f"{rf.name} illegally imports SQLAlchemy ({mod})"
            assert not mod.startswith("sqlite3"), f"{rf.name} illegally imports sqlite3 ({mod})"
            assert not mod.startswith("voc_intel.db"), f"{rf.name} illegally imports ORM db ({mod})"
            assert not mod.startswith("voc_intel.repositories"), (
                f"{rf.name} illegally bypasses services into repositories ({mod})"
            )


def test_services_never_depend_on_http_transport_or_raw_sqlite3() -> None:
    svc_dir = Path(__file__).resolve().parents[1] / "src" / "voc_intel" / "services"
    svc_files = [p for p in svc_dir.glob("*.py") if p.name != "__init__.py"]
    assert len(svc_files) >= 5

    for sf in svc_files:
        imports = _extract_imports(sf)
        for mod in imports:
            assert not mod.startswith("fastapi"), f"{sf.name} illegally couples to FastAPI ({mod})"
            assert not mod.startswith("sqlite3"), f"{sf.name} illegally uses raw sqlite3 ({mod})"

