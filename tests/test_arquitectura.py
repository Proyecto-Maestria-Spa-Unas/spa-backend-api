"""Fronteras de la arquitectura (sección 7): import-linter debe pasar en verde."""

from pathlib import Path

from importlinter.cli import lint_imports

RAIZ = Path(__file__).resolve().parent.parent


def test_contratos_de_importacion() -> None:
    codigo = lint_imports(config_filename=str(RAIZ / ".importlinter"))
    assert codigo == 0, "Un módulo importa a otro o una capa viola la arquitectura (ver salida de lint-imports)"
