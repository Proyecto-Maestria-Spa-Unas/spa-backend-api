"""Adaptador SQLAlchemy de MovimientoRepository.

Errores de la base que este adaptador traduce a errores de dominio (app.compartido.errores):
- CHECK de saldo o mensaje del trigger por stock → StockInsuficiente (409)
- UNIQUE de clave_idempotencia → devolver el movimiento existente (reintento seguro)
- UNIQUE de movimiento_anulado_id → MovimientoYaAnulado (409)
"""

from decimal import Decimal
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.engine import RowMapping
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.compartido.errores import DatosInvalidos, RecursoNoExiste
from app.modulos.movimientos.domain.modelo import (
    MotivoMovimiento,
    Movimiento,
    MovimientoRegistrado,
    TipoMovimiento,
)


class MovimientoRepositorySQL:
    def __init__(self, session: Session) -> None:
        self._session = session

    def registrar_entrada(
        self,
        producto_id: UUID,
        cantidad: Decimal,
        motivo_codigo: str,
        costo_unitario: Decimal | None,
        proveedor_id: UUID | None,
        observacion: str | None,
        registrado_por: UUID,
        clave_idempotencia: UUID,
    ) -> MovimientoRegistrado:
        self._bloquear_clave(clave_idempotencia)
        existente = self._buscar_por_clave(clave_idempotencia)
        if existente is not None:
            return existente
        motivo_id = self._motivo_id(motivo_codigo, TipoMovimiento.ENTRADA)
        return self._insertar(
            "ENTRADA",
            producto_id,
            cantidad,
            motivo_id,
            costo_unitario,
            proveedor_id,
            observacion,
            registrado_por,
            clave_idempotencia,
        )

    def registrar_salida(
        self,
        producto_id: UUID,
        cantidad: Decimal,
        motivo_codigo: str,
        observacion: str | None,
        registrado_por: UUID,
        clave_idempotencia: UUID,
    ) -> MovimientoRegistrado:
        self._bloquear_clave(clave_idempotencia)
        existente = self._buscar_por_clave(clave_idempotencia)
        if existente is not None:
            return existente
        motivo_id = self._motivo_id(motivo_codigo, TipoMovimiento.SALIDA)
        return self._insertar(
            "SALIDA",
            producto_id,
            cantidad,
            motivo_id,
            None,
            None,
            observacion,
            registrado_por,
            clave_idempotencia,
        )

    def _motivo_id(self, codigo: str, tipo: TipoMovimiento) -> int:
        motivo_id = self._session.execute(
            text(
                """
                SELECT id
                FROM inventario.motivo_movimiento
                WHERE codigo = :codigo AND aplica_a = :tipo AND activo
                """
            ),
            {"codigo": codigo, "tipo": tipo.value},
        ).scalar_one_or_none()
        if motivo_id is None:
            raise DatosInvalidos("El motivo no existe, está inactivo o no aplica a este movimiento")
        return int(motivo_id)

    def _bloquear_clave(self, clave_idempotencia: UUID) -> None:
        """Serializa peticiones concurrentes con la misma clave antes del trigger de saldo."""
        self._session.execute(
            text("SELECT pg_advisory_xact_lock(hashtextextended(CAST(:clave_idempotencia AS text), 0))"),
            {"clave_idempotencia": clave_idempotencia},
        )

    def _insertar(
        self,
        tipo: str,
        producto_id: UUID,
        cantidad: Decimal,
        motivo_id: int,
        costo_unitario: Decimal | None,
        proveedor_id: UUID | None,
        observacion: str | None,
        registrado_por: UUID,
        clave_idempotencia: UUID,
    ) -> MovimientoRegistrado:
        try:
            with self._session.begin_nested():
                fila = (
                    self._session.execute(
                        text(
                            """
                        INSERT INTO inventario.movimiento (
                            producto_id, tipo, motivo_id, cantidad, costo_unitario,
                            proveedor_id, observacion, registrado_por, clave_idempotencia
                        ) VALUES (
                            :producto_id, :tipo, :motivo_id, :cantidad, :costo_unitario,
                            :proveedor_id, :observacion, :registrado_por, :clave_idempotencia
                        )
                        RETURNING id
                        """
                        ),
                        {
                            "producto_id": producto_id,
                            "tipo": tipo,
                            "motivo_id": motivo_id,
                            "cantidad": cantidad,
                            "costo_unitario": costo_unitario,
                            "proveedor_id": proveedor_id,
                            "observacion": observacion,
                            "registrado_por": registrado_por,
                            "clave_idempotencia": clave_idempotencia,
                        },
                    )
                    .mappings()
                    .one()
                )
        except IntegrityError as error:
            if self._es_clave_duplicada(error):
                existente = self._buscar_por_clave(clave_idempotencia)
                if existente is not None:
                    return existente
            if getattr(error.orig, "sqlstate", None) == "23503":
                raise RecursoNoExiste("El producto o proveedor indicado no existe") from error
            raise
        return self._buscar_por_id(int(fila["id"]))

    def _buscar_por_clave(self, clave_idempotencia: UUID) -> MovimientoRegistrado | None:
        fila = (
            self._session.execute(
                text(
                    """
                SELECT
                    m.id, m.producto_id, m.tipo, mm.codigo AS motivo_codigo,
                    m.cantidad, m.saldo_resultante, m.costo_unitario,
                    m.costo_promedio_resultante, m.proveedor_id, m.observacion,
                    m.registrado_por, m.ocurrido_en,
                    CASE
                        WHEN p.descontinuado THEN 'DESCONTINUADO'
                        WHEN m.saldo_resultante <= 0 THEN 'AGOTADO'
                        WHEN p.stock_minimo IS NOT NULL AND m.saldo_resultante <= p.stock_minimo THEN 'BAJO_STOCK'
                        ELSE 'DISPONIBLE'
                    END AS estado
                FROM inventario.movimiento AS m
                LEFT JOIN inventario.motivo_movimiento AS mm ON mm.id = m.motivo_id
                JOIN inventario.producto AS p ON p.id = m.producto_id
                WHERE m.clave_idempotencia = :clave_idempotencia
                """
                ),
                {"clave_idempotencia": clave_idempotencia},
            )
            .mappings()
            .first()
        )
        return self._a_registro(fila) if fila is not None else None

    def _buscar_por_id(self, movimiento_id: int) -> MovimientoRegistrado:
        fila = (
            self._session.execute(
                text(
                    """
                SELECT
                    m.id, m.producto_id, m.tipo, mm.codigo AS motivo_codigo,
                    m.cantidad, m.saldo_resultante, m.costo_unitario,
                    m.costo_promedio_resultante, m.proveedor_id, m.observacion,
                    m.registrado_por, m.ocurrido_en,
                    CASE
                        WHEN p.descontinuado THEN 'DESCONTINUADO'
                        WHEN m.saldo_resultante <= 0 THEN 'AGOTADO'
                        WHEN p.stock_minimo IS NOT NULL AND m.saldo_resultante <= p.stock_minimo THEN 'BAJO_STOCK'
                        ELSE 'DISPONIBLE'
                    END AS estado
                FROM inventario.movimiento AS m
                LEFT JOIN inventario.motivo_movimiento AS mm ON mm.id = m.motivo_id
                JOIN inventario.producto AS p ON p.id = m.producto_id
                WHERE m.id = :movimiento_id
                """
                ),
                {"movimiento_id": movimiento_id},
            )
            .mappings()
            .one()
        )
        return self._a_registro(fila)

    @staticmethod
    def _es_clave_duplicada(error: IntegrityError) -> bool:
        diag = getattr(error.orig, "diag", None)
        return getattr(diag, "constraint_name", None) == "movimiento_clave_uk"

    def listar_motivos(
        self,
        tipo: TipoMovimiento | None = None,
    ) -> list[MotivoMovimiento]:
        filas = (
            self._session.execute(
                text(
                    """
                    SELECT id, codigo, nombre, aplica_a
                    FROM inventario.motivo_movimiento
                    WHERE activo = TRUE
                    AND (
                        CAST(:tipo AS TEXT) IS NULL
                        OR aplica_a = :tipo
                    )
                    ORDER BY nombre, codigo
                    """
                ),
                {"tipo": tipo.value if tipo is not None else None},
            )
            .mappings()
            .all()
        )

        return [
            MotivoMovimiento(
                id=fila["id"],
                codigo=fila["codigo"],
                nombre=fila["nombre"],
                aplica_a=TipoMovimiento(fila["aplica_a"]),
            )
            for fila in filas
        ]

    @staticmethod
    def _a_registro(fila: RowMapping) -> MovimientoRegistrado:
        movimiento = Movimiento(
            id=fila["id"],
            producto_id=fila["producto_id"],
            tipo=TipoMovimiento(fila["tipo"]),
            motivo_codigo=fila["motivo_codigo"] or "",
            cantidad=Decimal(fila["cantidad"]),
            saldo_resultante=Decimal(fila["saldo_resultante"]),
            costo_unitario=(
                Decimal(fila["costo_unitario"])
                if fila["costo_unitario"] is not None
                else None
            ),
            costo_promedio_resultante=Decimal(fila["costo_promedio_resultante"]),
            proveedor_id=fila["proveedor_id"],
            observacion=fila["observacion"],
            registrado_por=fila["registrado_por"],
            ocurrido_en=fila["ocurrido_en"],
        )
        return MovimientoRegistrado(
            movimiento=movimiento,
            saldo=movimiento.saldo_resultante,
            estado=fila["estado"],
        )