"""Proteções básicas das dependências entre as camadas MSCV."""

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
FORBIDDEN = {
    "views": {"services", "models", "database"},
    "controllers": {"models", "database", "views"},
    "services": {"controllers", "views"},
    "models": {"controllers", "services", "views"},
}


def _imports(path):
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            yield node.module.split(".")[0]
        elif isinstance(node, ast.Import):
            for alias in node.names:
                yield alias.name.split(".")[0]


def test_camadas_nao_importam_dependencias_proibidas():
    violations = []
    for layer, forbidden in FORBIDDEN.items():
        for path in (ROOT / layer).rglob("*.py"):
            invalid = sorted(set(_imports(path)) & forbidden)
            if invalid:
                violations.append(
                    f"{path.relative_to(ROOT)} importa {', '.join(invalid)}"
                )
    assert not violations, "\n".join(violations)
