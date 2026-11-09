"""Adaptador SQLAlchemy de MovimientoRepository.

Errores de la base que este adaptador traduce a errores de dominio (app.compartido.errores):
- CHECK de saldo o mensaje del trigger por stock → StockInsuficiente (409)
- UNIQUE de clave_idempotencia → devolver el movimiento existente (reintento seguro)
- UNIQUE de movimiento_anulado_id → MovimientoYaAnulado (409)
"""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.engine import RowMapping
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.compartido.errores import DatosInvalidos, MovimientoYaAnulado, RecursoNoExiste
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

    def listar(
        self,
        producto_id: UUID | None,
        tipo: TipoMovimiento | None,
        usuario_id: UUID | None,
        desde: datetime | None,
        hasta: datetime | None,
        offset: int,
        limite: int,
    ) -> tuple[list[Movimiento], int]:
        parametros = {
            "producto_id": producto_id,
            "tipo": tipo.value if tipo is not None else None,
            "usuario_id": usuario_id,
            "desde": desde,
            "hasta": hasta,
        }
        total = self._session.execute(
            text(
                """
                SELECT count(*)
                FROM inventario.movimiento AS m
                WHERE (CAST(:producto_id AS UUID) IS NULL OR m.producto_id = :producto_id)
                  AND (CAST(:tipo AS TEXT) IS NULL OR m.tipo = :tipo)
                  AND (CAST(:usuario_id AS UUID) IS NULL OR m.registrado_por = :usuario_id)
                  AND (CAST(:desde AS TIMESTAMPTZ) IS NULL OR m.ocurrido_en >= :desde)
                  AND (CAST(:hasta AS TIMESTAMPTZ) IS NULL OR m.ocurrido_en <= :hasta)
                """
            ),
            parametros,
        ).scalar_one()
        filas = (
            self._session.execute(
                text(
                    """
                    SELECT
                        m.id, m.producto_id, m.tipo, COALESCE(mm.codigo, 'ANULACION') AS motivo_codigo,
                        m.cantidad, m.saldo_resultante, m.costo_unitario,
                        m.costo_promedio_resultante, m.proveedor_id, m.observacion,
                        m.registrado_por, m.ocurrido_en, m.movimiento_anulado_id,
                        (
                            SELECT anulacion.id
                            FROM inventario.movimiento AS anulacion
                            WHERE anulacion.movimiento_anulado_id = m.id
                        ) AS anulado_por_id,
                        CASE
                            WHEN p.descontinuado THEN 'DESCONTINUADO'
                            WHEN m.saldo_resultante <= 0 THEN 'AGOTADO'
                            WHEN p.stock_minimo IS NOT NULL AND m.saldo_resultante <= p.stock_minimo THEN 'BAJO_STOCK'
                            ELSE 'DISPONIBLE'
                        END AS estado
                    FROM inventario.movimiento AS m
                    LEFT JOIN inventario.motivo_movimiento AS mm ON mm.id = m.motivo_id
                    JOIN inventario.producto AS p ON p.id = m.producto_id
                    WHERE (CAST(:producto_id AS UUID) IS NULL OR m.producto_id = :producto_id)
                      AND (CAST(:tipo AS TEXT) IS NULL OR m.tipo = :tipo)
                      AND (CAST(:usuario_id AS UUID) IS NULL OR m.registrado_por = :usuario_id)
                      AND (CAST(:desde AS TIMESTAMPTZ) IS NULL OR m.ocurrido_en >= :desde)
                      AND (CAST(:hasta AS TIMESTAMPTZ) IS NULL OR m.ocurrido_en <= :hasta)
                    ORDER BY m.ocurrido_en DESC, m.id DESC
                    LIMIT :limite OFFSET :offset
                    """
                ),
                {**parametros, "limite": limite, "offset": offset},
            )
            .mappings()
            .all()
        )
        return [self._a_movimiento(fila) for fila in filas], int(total)

    def obtener(self, movimiento_id: int, usuario_id: UUID | None = None) -> Movimiento | None:
        fila = (
            self._session.execute(
                text(
                    """
                    SELECT
                        m.id, m.producto_id, m.tipo, COALESCE(mm.codigo, 'ANULACION') AS motivo_codigo,
                        m.cantidad, m.saldo_resultante, m.costo_unitario,
                        m.costo_promedio_resultante, m.proveedor_id, m.observacion,
                        m.registrado_por, m.ocurrido_en, m.movimiento_anulado_id,
                        (
                            SELECT anulacion.id
                            FROM inventario.movimiento AS anulacion
                            WHERE anulacion.movimiento_anulado_id = m.id
                        ) AS anulado_por_id,
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
                      AND (CAST(:usuario_id AS UUID) IS NULL OR m.registrado_por = :usuario_id)
                    """
                ),
                {"movimiento_id": movimiento_id, "usuario_id": usuario_id},
            )
            .mappings()
            .first()
        )
        return self._a_movimiento(fila) if fila is not None else None

    def anular(
        self,
        movimiento_id: int,
        motivo: str,
        registrado_por: UUID,
        clave_idempotencia: UUID,
    ) -> MovimientoRegistrado:
        self._bloquear_clave(clave_idempotencia)
        existente = self._buscar_por_clave(clave_idempotencia)
        if existente is not None:
            return existente
        producto_id = self._session.execute(
            text("SELECT producto_id FROM inventario.movimiento WHERE id = :movimiento_id"),
            {"movimiento_id": movimiento_id},
        ).scalar_one_or_none()
        if producto_id is None:
            raise RecursoNoExiste("Movimiento no encontrado")
        try:
            with self._session.begin_nested():
                fila = (
                    self._session.execute(
                        text(
                            """
                            INSERT INTO inventario.movimiento (
                                producto_id, tipo, motivo_id, cantidad, observacion,
                                registrado_por, movimiento_anulado_id, clave_idempotencia
                            ) VALUES (
                                :producto_id, 'ANULACION', NULL, 1, :observacion,
                                :registrado_por, :movimiento_anulado_id, :clave_idempotencia
                            )
                            RETURNING id
                            """
                        ),
                        {
                            "producto_id": producto_id,
                            "observacion": motivo,
                            "registrado_por": registrado_por,
                            "movimiento_anulado_id": movimiento_id,
                            "clave_idempotencia": clave_idempotencia,
                        },
                    )
                    .mappings()
                    .one()
                )
        except IntegrityError as error:
            if self._constraint_name(error) == "movimiento_anulado_uk":
                raise MovimientoYaAnulado() from error
            if self._es_clave_duplicada(error):
                existente = self._buscar_por_clave(clave_idempotencia)
                if existente is not None:
                    return existente
            if getattr(error.orig, "sqlstate", None) == "23503":
                raise RecursoNoExiste("El movimiento indicado no existe") from error
            raise
        return self._buscar_por_id(int(fila["id"]))

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
                    m.id, m.producto_id, m.tipo, COALESCE(mm.codigo, 'ANULACION') AS motivo_codigo,
                    m.cantidad, m.saldo_resultante, m.costo_unitario,
                    m.costo_promedio_resultante, m.proveedor_id, m.observacion,
                    m.registrado_por, m.ocurrido_en, m.movimiento_anulado_id,
                    (
                        SELECT anulacion.id
                        FROM inventario.movimiento AS anulacion
                        WHERE anulacion.movimiento_anulado_id = m.id
                    ) AS anulado_por_id,
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
                    m.id, m.producto_id, m.tipo, COALESCE(mm.codigo, 'ANULACION') AS motivo_codigo,
                    m.cantidad, m.saldo_resultante, m.costo_unitario,
                    m.costo_promedio_resultante, m.proveedor_id, m.observacion,
                    m.registrado_por, m.ocurrido_en, m.movimiento_anulado_id,
                    (
                        SELECT anulacion.id
                        FROM inventario.movimiento AS anulacion
                        WHERE anulacion.movimiento_anulado_id = m.id
                    ) AS anulado_por_id,
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
        return MovimientoRepositorySQL._constraint_name(error) == "movimiento_clave_uk"

    @staticmethod
    def _constraint_name(error: IntegrityError) -> str | None:
        diag = getattr(error.orig, "diag", None)
        return getattr(diag, "constraint_name", None)

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
    def _a_movimiento(fila: RowMapping) -> Movimiento:
        return Movimiento(
            id=fila["id"],
            producto_id=fila["producto_id"],
            tipo=TipoMovimiento(fila["tipo"]),
            motivo_codigo=fila["motivo_codigo"] or "",
            cantidad=Decimal(fila["cantidad"]),
            saldo_resultante=Decimal(fila["saldo_resultante"]),
            costo_unitario=(Decimal(fila["costo_unitario"]) if fila["costo_unitario"] is not None else None),
            costo_promedio_resultante=Decimal(fila["costo_promedio_resultante"]),
            proveedor_id=fila["proveedor_id"],
            observacion=fila["observacion"],
            registrado_por=fila["registrado_por"],
            ocurrido_en=fila["ocurrido_en"],
            movimiento_anulado_id=fila["movimiento_anulado_id"],
            anulado_por_id=fila["anulado_por_id"],
        )

    @classmethod
    def _a_registro(cls, fila: RowMapping) -> MovimientoRegistrado:
        movimiento = cls._a_movimiento(fila)
        return MovimientoRegistrado(
            movimiento=movimiento,
            saldo=movimiento.saldo_resultante,
            estado=fila["estado"],
        )
