"""El código y los contratos publicados en docs/openapi/ no pueden divergir."""

from pathlib import Path

import pytest

from scripts.exportar_contratos import DESTINO, SERVICIOS, _serializar, contrato


@pytest.mark.parametrize("servicio", list(SERVICIOS))
def test_contrato_publicado_coincide_con_el_codigo(servicio: str) -> None:
    archivo: Path = DESTINO / f"{servicio}-v1.yaml"
    assert archivo.exists(), f"Falta {archivo.name}: ejecute python scripts/exportar_contratos.py"
    assert archivo.read_text(encoding="utf-8") == _serializar(contrato(servicio)), (
        f"{archivo.name} no coincide con el código. Ejecute python scripts/exportar_contratos.py "
        "y abra el cambio como PR de contrato (lo aprueba equipo-frontend)."
    )


def test_cada_endpoint_pertenece_a_un_solo_servicio() -> None:
    rutas = [r for s in SERVICIOS for r in contrato(s)["paths"]]
    assert len(rutas) == len(set(rutas))
