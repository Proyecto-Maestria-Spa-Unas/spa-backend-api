"""Adaptadores SQLAlchemy del broker (esquema `broker` de spa-database).

- `reclamar` usa FOR UPDATE SKIP LOCKED: dos consumidores simultáneos nunca toman el mismo trabajo
  y ninguno se queda esperando al otro. Los bloqueos duran hasta el commit del request; si la función
  se corta, el rollback devuelve los trabajos a la cola.
- El orden es por prioridad efectiva (misma fórmula que `domain.modelo.prioridad_efectiva`) y luego
  por antigüedad.
- Cada trabajo se procesa en un punto de guardado: el fallo de uno no deshace los demás.
"""

from collections.abc import Callable
from typing import Any

from sqlalchemy import text
from sqlalchemy.engine import RowMapping
from sqlalchemy.orm import Session

from app.modulos.broker.domain.modelo import ConteoCola, EstadoTrabajo, Fallo, Prioridad, Trabajo


class ColaRepositorySQL:
    def __init__(self, session: Session) -> None:
        self._session = session

    def reclamar(self, limite: int, paso_envejecimiento_s: int) -> list[Trabajo]:
        filas = (
            self._session.execute(
                text(
                    """
                    SELECT id, tipo, prioridad, payload, intentos, max_intentos, creado_en
                    FROM broker.trabajo
                    WHERE estado = 'PENDIENTE'
                      AND disponible_en <= now()
                    ORDER BY
                      GREATEST(
                        1,
                        prioridad - floor(extract(epoch FROM now() - creado_en) / CAST(:paso AS numeric))::int
                      ),
                      creado_en,
                      id
                    LIMIT :limite
                    FOR UPDATE SKIP LOCKED
                    """
                ),
                {"limite": limite, "paso": paso_envejecimiento_s},
            )
            .mappings()
            .all()
        )
        return [self._a_trabajo(fila) for fila in filas]

    def ejecutar_aislado(self, accion: Callable[[], None]) -> Exception | None:
        try:
            with self._session.begin_nested():
                accion()
        except Exception as error:
            return error
        return None

    def marcar_hecho(self, trabajo_id: int) -> None:
        self._session.execute(
            text(
                """
                UPDATE broker.trabajo
                SET estado = 'HECHO', procesado_en = now(), ultimo_error = NULL
                WHERE id = :id
                """
            ),
            {"id": trabajo_id},
        )

    def marcar_fallo(self, trabajo_id: int, fallo: Fallo, error: str) -> None:
        self._session.execute(
            text(
                """
                UPDATE broker.trabajo
                SET intentos = :intentos,
                    estado = CAST(:estado AS text),
                    ultimo_error = :error,
                    disponible_en = CASE
                      WHEN CAST(:espera AS integer) IS NULL THEN disponible_en
                      ELSE now() + make_interval(secs => CAST(:espera AS integer))
                    END,
                    procesado_en = CASE WHEN CAST(:estado AS text) = 'FALLIDO' THEN now() ELSE NULL END
                WHERE id = :id
                """
            ),
            {
                "id": trabajo_id,
                "intentos": fallo.intentos,
                "estado": fallo.estado.value,
                "error": error,
                "espera": fallo.reintentar_en_s,
            },
        )

    def contar(self) -> list[ConteoCola]:
        filas = (
            self._session.execute(
                text(
                    """
                    SELECT estado, prioridad, count(*) AS cantidad
                    FROM broker.trabajo
                    GROUP BY estado, prioridad
                    ORDER BY estado, prioridad
                    """
                )
            )
            .mappings()
            .all()
        )
        return [
            ConteoCola(
                estado=EstadoTrabajo(fila["estado"]),
                prioridad=Prioridad(fila["prioridad"]),
                cantidad=int(fila["cantidad"]),
            )
            for fila in filas
        ]

    @staticmethod
    def _a_trabajo(fila: RowMapping) -> Trabajo:
        payload: dict[str, Any] = dict(fila["payload"] or {})
        return Trabajo(
            id=int(fila["id"]),
            tipo=str(fila["tipo"]),
            prioridad=Prioridad(fila["prioridad"]),
            payload=payload,
            intentos=int(fila["intentos"]),
            max_intentos=int(fila["max_intentos"]),
            creado_en=fila["creado_en"],
        )


class NotificacionRepositorySQL:
    def __init__(self, session: Session) -> None:
        self._session = session

    def registrar(self, trabajo: Trabajo, producto_id: str | None, mensaje: str) -> None:
        self._session.execute(
            text(
                """
                INSERT INTO broker.notificacion (trabajo_id, tipo, prioridad, producto_id, mensaje)
                VALUES (:trabajo_id, :tipo, :prioridad, CAST(:producto_id AS uuid), :mensaje)
                ON CONFLICT (trabajo_id) DO NOTHING
                """
            ),
            {
                "trabajo_id": trabajo.id,
                "tipo": trabajo.tipo,
                "prioridad": int(trabajo.prioridad),
                "producto_id": producto_id,
                "mensaje": mensaje,
            },
        )
