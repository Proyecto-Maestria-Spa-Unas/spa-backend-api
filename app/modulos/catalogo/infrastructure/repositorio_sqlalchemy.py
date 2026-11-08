"""Adaptador SQLAlchemy para las consultas del catálogo."""

from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import text
from sqlalchemy.engine import RowMapping
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.compartido.errores import (
    CategoriaDuplicada,
    CodigoDuplicado,
    NoImplementado,
    RecursoNoExiste,
    VersionConflicto,
)
from app.modulos.catalogo.domain.modelo import (
    Categoria,
    EstadoInventario,
    Producto,
    UnidadMedida,
)


class CatalogoRepositorySQL:
    def __init__(self, session: Session) -> None:
        self._session = session

    def listar_categorias(self, solo_activas: bool) -> list[Categoria]:
        filas = self._session.execute(
            text(
                """
                SELECT id, nombre, descripcion, orden, activa
                FROM inventario.categoria
                WHERE :incluir_inactivas OR activa
                ORDER BY orden, nombre
                """
            ),
            {"incluir_inactivas": not solo_activas},
        ).mappings()
        return [Categoria(**fila) for fila in filas]

    def listar_unidades(self) -> list[UnidadMedida]:
        filas = self._session.execute(
            text(
                """
                SELECT id, codigo, nombre, magnitud, admite_decimales
                FROM inventario.unidad_medida
                ORDER BY nombre
                """
            )
        ).mappings()
        return [UnidadMedida(**fila) for fila in filas]

    @staticmethod
    def _es_unicidad_duplicada(error: IntegrityError) -> bool:
        return getattr(error.orig, "sqlstate", None) == "23505"

    def crear_categoria(self, datos: dict[str, object]) -> Categoria:
        try:
            fila = (
                self._session.execute(
                    text(
                        """
                        INSERT INTO inventario.categoria (nombre, descripcion, orden)
                        VALUES (:nombre, :descripcion, :orden)
                        RETURNING id, nombre, descripcion, orden, activa
                        """
                    ),
                    datos,
                )
                .mappings()
                .one()
            )
        except IntegrityError as error:
            if self._es_unicidad_duplicada(error):
                raise CategoriaDuplicada() from error
            raise
        return Categoria(**fila)

    def actualizar_categoria(self, categoria_id: int, datos: dict[str, object]) -> Categoria:
        if not datos:
            fila = self._session.execute(
                text(
                    """
                    SELECT id, nombre, descripcion, orden, activa
                    FROM inventario.categoria WHERE id = :id
                    """
                ),
                {"id": categoria_id},
            ).mappings().first()
            if fila is None:
                raise RecursoNoExiste("Categoría no encontrada")
            return Categoria(**fila)

        campos = {
            campo: valor for campo, valor in datos.items() if campo in {"nombre", "descripcion", "orden", "activa"}
        }
        # SQL identifiers are interpolated only after filtering through this allowlist.
        asignaciones = ", ".join(f"{campo} = :{campo}" for campo in campos)
        try:
            fila = (
                self._session.execute(
                    text(
                        f"UPDATE inventario.categoria SET {asignaciones} "  # noqa: S608
                        "WHERE id = :id "
                        "RETURNING id, nombre, descripcion, orden, activa"
                    ),
                    {**campos, "id": categoria_id},
                )
                .mappings()
                .first()
            )
        except IntegrityError as error:
            if self._es_unicidad_duplicada(error):
                raise CategoriaDuplicada() from error
            raise
        if fila is None:
            raise RecursoNoExiste("Categoría no encontrada")
        return Categoria(**fila)

    def crear_producto(
        self,
        datos: dict[str, object],
        cantidad_inicial: Decimal | None,
        registrado_por: UUID,
    ) -> Producto:
        try:
            fila = (
                self._session.execute(
                    text(
                        """
                        INSERT INTO inventario.producto (
                            codigo, nombre, descripcion, categoria_id,
                            unidad_medida_id, stock_minimo
                        )
                        VALUES (
                            :codigo, :nombre, :descripcion, :categoria_id,
                            :unidad_medida_id, :stock_minimo
                        )
                        RETURNING id
                        """
                    ),
                    datos,
                )
                .mappings()
                .one()
            )
            producto_id = fila["id"]
            if cantidad_inicial is not None:
                movimiento_disponible = self._session.execute(
                    text("SELECT to_regclass('inventario.movimiento') IS NOT NULL")
                ).scalar_one()
                if not movimiento_disponible:
                    raise NoImplementado("El saldo inicial requiere la tabla de movimientos (migración D7)")
                motivo_id = self._session.execute(
                    text(
                        """
                        SELECT id
                        FROM inventario.motivo_movimiento
                        WHERE codigo = 'SALDO_INICIAL' AND activo
                        """
                    )
                ).scalar_one_or_none()
                if motivo_id is None:
                    raise NoImplementado("El motivo SALDO_INICIAL no está configurado en la base de datos")
                self._session.execute(
                    text(
                        """
                        INSERT INTO inventario.movimiento (
                            producto_id, tipo, motivo_id, cantidad,
                            clave_idempotencia, registrado_por
                        )
                        VALUES (
                            :producto_id, 'ENTRADA', :motivo_id, :cantidad,
                            :clave_idempotencia, :registrado_por
                        )
                        """
                    ),
                    {
                        "producto_id": producto_id,
                        "motivo_id": motivo_id,
                        "cantidad": cantidad_inicial,
                        "clave_idempotencia": uuid4(),
                        "registrado_por": registrado_por,
                    },
                )
        except IntegrityError as error:
            self._session.rollback()
            if self._es_unicidad_duplicada(error):
                raise CodigoDuplicado("El código del producto ya está registrado") from error
            if getattr(error.orig, "sqlstate", None) == "23503":
                raise RecursoNoExiste("La categoría o unidad de medida no existe") from error
            raise
        producto = self.obtener_producto(producto_id)
        if producto is None:
            raise RecursoNoExiste("El producto creado no quedó disponible")
        return producto

    def actualizar_producto(self, producto_id: UUID, version: int, datos: dict[str, object]) -> Producto:
        campos = {
            campo: valor
            for campo, valor in datos.items()
            if campo in {"nombre", "descripcion", "categoria_id", "unidad_medida_id"}
        }
        if not campos:
            producto = self.obtener_producto(producto_id)
            if producto is None:
                raise RecursoNoExiste("Producto no encontrado")
            if producto.version != version:
                raise VersionConflicto()
            return producto
        # SQL identifiers are interpolated only after filtering through this allowlist.
        asignaciones = ", ".join(f"{campo} = :{campo}" for campo in campos)
        try:
            fila = (
                self._session.execute(
                    text(
                        f"UPDATE inventario.producto SET {asignaciones} "  # noqa: S608
                        "WHERE id = :id AND version = :version "
                        "RETURNING id, codigo, nombre, descripcion, categoria_id, "
                        "unidad_medida_id, stock_actual, stock_minimo, descontinuado, "
                        "version, creado_en, actualizado_en"
                    ),
                    {**campos, "id": producto_id, "version": version},
                )
                .mappings()
                .first()
            )
        except IntegrityError as error:
            if getattr(error.orig, "sqlstate", None) == "23503":
                raise RecursoNoExiste("La categoría o unidad de medida no existe") from error
            raise
        if fila is not None:
            return self._producto_desde_fila(fila)
        if self.obtener_producto(producto_id) is None:
            raise RecursoNoExiste("Producto no encontrado")
        raise VersionConflicto()

    def cambiar_producto(self, producto_id: UUID, asignacion: str, valor: object) -> Producto:
        permitidas = {"stock_minimo", "descontinuado"}
        if asignacion not in permitidas:
            raise ValueError("Campo de catálogo no permitido")
        # SQL identifier was checked against `permitidas` above.
        fila = (
            self._session.execute(
                text(
                    f"UPDATE inventario.producto SET {asignacion} = :valor "  # noqa: S608
                    "WHERE id = :id "
                    "RETURNING id, codigo, nombre, descripcion, categoria_id, "
                    "unidad_medida_id, stock_actual, stock_minimo, descontinuado, "
                    "version, creado_en, actualizado_en"
                ),
                {"id": producto_id, "valor": valor},
            )
            .mappings()
            .first()
        )
        if fila is None:
            raise RecursoNoExiste("Producto no encontrado")
        return self._producto_desde_fila(fila)

    @staticmethod
    def _producto_desde_fila(fila: RowMapping) -> Producto:
        return Producto(
            id=fila["id"],
            codigo=fila["codigo"],
            nombre=fila["nombre"],
            descripcion=fila["descripcion"],
            categoria_id=fila["categoria_id"],
            unidad_medida_id=fila["unidad_medida_id"],
            stock_actual=Decimal(fila["stock_actual"]),
            stock_minimo=(Decimal(fila["stock_minimo"]) if fila["stock_minimo"] is not None else None),
            descontinuado=fila["descontinuado"],
            version=fila["version"],
            creado_en=fila["creado_en"],
            actualizado_en=fila["actualizado_en"],
        )

    def obtener_producto(self, producto_id: UUID) -> Producto | None:
        consulta = text(
            """
            SELECT
                id,
                codigo,
                nombre,
                descripcion,
                categoria_id,
                unidad_medida_id,
                stock_actual,
                stock_minimo,
                descontinuado,
                version,
                creado_en,
                actualizado_en
            FROM inventario.producto
            WHERE id = :producto_id
            """
        )

        fila = (
            self._session.execute(
                consulta,
                {"producto_id": producto_id},
            )
            .mappings()
            .first()
        )

        if fila is None:
            return None

        return self._producto_desde_fila(fila)

    def listar_productos(
        self,
        categoria_id: int | None,
        estado: EstadoInventario | None,
        q: str | None,
        incluir_descontinuados: bool,
        offset: int,
        limite: int,
    ) -> tuple[list[Producto], int]:
        parametros = {
            "categoria_id": categoria_id,
            "estado": estado.value if estado is not None else None,
            "q": f"%{q.strip()}%" if q and q.strip() else None,
            "incluir_descontinuados": incluir_descontinuados,
        }

        consulta_total = text(
            """
            SELECT COUNT(*)
            FROM inventario.producto
            WHERE (
                CAST(:categoria_id AS INTEGER) IS NULL
                OR categoria_id = :categoria_id
            )
            AND (
                CAST(:estado AS TEXT) IS NULL
                OR estado = :estado
            )
            AND (
                CAST(:q AS TEXT) IS NULL
                OR codigo::text ILIKE :q
                OR nombre ILIKE :q
            )
            AND (
                :incluir_descontinuados
                OR descontinuado = FALSE
            )
            """
        )

        total = self._session.execute(
            consulta_total,
            parametros,
        ).scalar_one()

        consulta_productos = text(
            """
            SELECT
                id,
                codigo,
                nombre,
                descripcion,
                categoria_id,
                unidad_medida_id,
                stock_actual,
                stock_minimo,
                descontinuado,
                version,
                creado_en,
                actualizado_en
            FROM inventario.producto
            WHERE (
                CAST(:categoria_id AS INTEGER) IS NULL
                OR categoria_id = :categoria_id
            )
            AND (
                CAST(:estado AS TEXT) IS NULL
                OR estado = :estado
            )
            AND (
                CAST(:q AS TEXT) IS NULL
                OR codigo::text ILIKE :q
                OR nombre ILIKE :q
            )
            AND (
                :incluir_descontinuados
                OR descontinuado = FALSE
            )
            ORDER BY nombre, codigo
            LIMIT :limite
            OFFSET :offset
            """
        )

        parametros_consulta = {
            **parametros,
            "limite": limite,
            "offset": offset,
        }

        filas = (
            self._session.execute(
                consulta_productos,
                parametros_consulta,
            )
            .mappings()
            .all()
        )

        productos = [self._producto_desde_fila(fila) for fila in filas]
        return productos, total
