"""pyproject.toml (lo lee Vercel) y requirements.txt (lo leen Docker y CI) declaran lo mismo."""

import tomllib
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent


def test_dependencias_sincronizadas() -> None:
    pyproject = tomllib.loads((RAIZ / "pyproject.toml").read_text(encoding="utf-8"))
    declaradas = {d.replace(" ", "") for d in pyproject["project"]["dependencies"]}
    requirements = {
        linea.strip().replace(" ", "")
        for linea in (RAIZ / "requirements.txt").read_text(encoding="utf-8").splitlines()
        if linea.strip() and not linea.startswith("#")
    }
    assert declaradas == requirements
