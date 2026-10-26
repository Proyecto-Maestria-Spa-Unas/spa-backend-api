"""Genera docs/openapi/<servicio>-v1.yaml a partir de los routers (un archivo por servicio).

Uso:
    python scripts/exportar_contratos.py           # escribe los 4 contratos
    python scripts/exportar_contratos.py --check   # falla si los archivos no coinciden con el código

Los contratos son el acuerdo con frontend: cualquier cambio entra por PR y lo aprueba equipo-frontend.
"""

import argparse
import copy
import json
import sys
from pathlib import Path
from typing import Any

import yaml

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from app.compartido.config import get_settings  # noqa: E402
from app.main import app  # noqa: E402

SERVICIOS = {
    "identidad": "S1 · Identidad",
    "catalogo": "S2 · Catálogo",
    "movimientos": "S3 · Movimientos",
    "analitica": "S4 · Alertas y analítica",
}
DESTINO = RAIZ / "docs" / "openapi"
PREFIJO = get_settings().api_prefix


def _referencias(nodo: Any) -> set[str]:
    encontradas: set[str] = set()
    if isinstance(nodo, dict):
        for clave, valor in nodo.items():
            if clave == "$ref" and isinstance(valor, str):
                encontradas.add(valor.rsplit("/", 1)[-1])
            else:
                encontradas |= _referencias(valor)
    elif isinstance(nodo, list):
        for valor in nodo:
            encontradas |= _referencias(valor)
    return encontradas


def contrato(servicio: str) -> dict[str, Any]:
    completo = app.openapi()
    rutas: dict[str, Any] = {}
    for ruta, operaciones in completo["paths"].items():
        propias = {m: op for m, op in operaciones.items() if servicio in op.get("tags", [])}
        if propias:
            rutas[ruta.removeprefix(PREFIJO)] = copy.deepcopy(propias)
    esquemas = completo.get("components", {}).get("schemas", {})
    pendientes, incluidos = _referencias(rutas), set()
    while pendientes:
        nombre = pendientes.pop()
        if nombre in incluidos or nombre not in esquemas:
            continue
        incluidos.add(nombre)
        pendientes |= _referencias(esquemas[nombre]) - incluidos
    componentes: dict[str, Any] = {"schemas": {n: esquemas[n] for n in sorted(incluidos)}}
    if "securitySchemes" in completo.get("components", {}):
        componentes["securitySchemes"] = completo["components"]["securitySchemes"]
    return {
        "openapi": completo["openapi"],
        "info": {"title": f"{SERVICIOS[servicio]} · Spa de Uñas", "version": "1.0.0"},
        "servers": [{"url": PREFIJO}],
        "paths": rutas,
        "components": componentes,
    }


def _serializar(documento: dict[str, Any]) -> str:
    # Pasar por JSON normaliza tipos; sort_keys=False conserva el orden de declaración.
    limpio = json.loads(json.dumps(documento))
    return yaml.safe_dump(limpio, allow_unicode=True, sort_keys=False, width=120)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="Solo verificar; no escribir")
    args = parser.parse_args()
    DESTINO.mkdir(parents=True, exist_ok=True)
    desactualizados = []
    for servicio in SERVICIOS:
        archivo = DESTINO / f"{servicio}-v1.yaml"
        contenido = _serializar(contrato(servicio))
        if args.check:
            if not archivo.exists() or archivo.read_text(encoding="utf-8") != contenido:
                desactualizados.append(archivo.name)
        else:
            archivo.write_text(contenido, encoding="utf-8")
            print(f"escrito {archivo.relative_to(RAIZ)}")
    if desactualizados:
        print("Contratos desactualizados:", ", ".join(desactualizados))
        print("Ejecute: python scripts/exportar_contratos.py  y abra un PR de contrato.")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
