"""Adaptador SQLAlchemy para la persistencia de proveedores."""

from uuid import UUID, uuid4

from sqlalchemy import text
from sqlalchemy.engine import RowMapping
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.compartido.errores import ProveedorDuplicado, RecursoNoExiste
from app.modulos.catalogo.domain.modelo import Proveedor


class ProveedoresSQL:
    """Implementación SQLAlchemy del repositorio de proveedores."""

    def __init__(self, session: Session) -> None:
        self._session = session

    @staticmethod
    def _proveedor_desde_fila(fila: RowMapping) -> Proveedor:
        return Proveedor(**fila)

    def listar(self, incluir_inactivos: bool = False) -> list[Proveedor]:
        filas = self._session.execute(
            text(
                """
                SELECT
                    id,
                    nit,
                    nombre,
                    telefono,
                    correo,
                    direccion,
                    ST_Y(ubicacion::geometry) AS latitud,
                    ST_X(ubicacion::geometry) AS longitud,
                    activo
                FROM inventario.proveedor
                WHERE :incluir_inactivos OR activo
                ORDER BY nombre
                """
            ),
            {"incluir_inactivos": incluir_inactivos},
        ).mappings()

        return [self._proveedor_desde_fila(fila) for fila in filas]

    def obtener(self, proveedor_id: UUID) -> Proveedor:
        fila = (
            self._session.execute(
                text(
                    """
                    SELECT
                        id,
                        nit,
                        nombre,
                        telefono,
                        correo,
                        direccion,
                        ST_Y(ubicacion::geometry) AS latitud,
                        ST_X(ubicacion::geometry) AS longitud,
                        activo
                    FROM inventario.proveedor
                    WHERE id = :id
                    """
                ),
                {"id": proveedor_id},
            )
            .mappings()
            .first()
        )

        if fila is None:
            raise RecursoNoExiste("Proveedor no encontrado")

        return self._proveedor_desde_fila(fila)

    def crear(self, datos: dict[str, object]) -> Proveedor:
        ubicacion = datos.get("ubicacion")
        coordenadas = ubicacion if isinstance(ubicacion, dict) else {}

        parametros = {
            "id": uuid4(),
            "nit": datos["nit"],
            "nombre": datos["nombre"],
            "telefono": datos.get("telefono"),
            "correo": datos.get("correo"),
            "direccion": datos.get("direccion"),
            "latitud": coordenadas.get("latitud"),
            "longitud": coordenadas.get("longitud"),
        }

        try:
            fila = (
                self._session.execute(
                    text(
                        """
                        INSERT INTO inventario.proveedor (
                            id, nit, nombre, telefono, correo, direccion, ubicacion
                        )
                        VALUES (
                            :id, :nit, :nombre, :telefono, :correo, :direccion,
                            CASE
                                WHEN CAST(:latitud AS double precision) IS NULL
                                    OR CAST(:longitud AS double precision) IS NULL THEN NULL
                                ELSE ST_SetSRID(
                                    ST_MakePoint(:longitud, :latitud), 4326
                                )::geography
                            END
                        )
                        RETURNING
                            id, nit, nombre, telefono, correo, direccion,
                            ST_Y(ubicacion::geometry) AS latitud,
                            ST_X(ubicacion::geometry) AS longitud,
                            activo
                        """
                    ),
                    parametros,
                )
                .mappings()
                .one()
            )
        except IntegrityError as error:
            self._session.rollback()
            if getattr(error.orig, "sqlstate", None) == "23505":
                raise ProveedorDuplicado() from error
            raise

        return self._proveedor_desde_fila(fila)

    def actualizar(self, proveedor_id: UUID, cambios: dict[str, object]) -> Proveedor:
        campos_permitidos = {"nombre", "telefono", "correo", "direccion", "activo"}
        campos = {campo: valor for campo, valor in cambios.items() if campo in campos_permitidos}

        asignaciones = [f"{campo} = :{campo}" for campo in campos]

        parametros: dict[str, object] = {"id": proveedor_id, **campos}

        if "ubicacion" in cambios:
            ubicacion = cambios["ubicacion"]

            if isinstance(ubicacion, dict):
                parametros["latitud"] = ubicacion.get("latitud")
                parametros["longitud"] = ubicacion.get("longitud")
            else:
                parametros["latitud"] = None
                parametros["longitud"] = None

            asignaciones.append(
                """
                ubicacion = CASE
                    WHEN CAST(:latitud AS double precision) IS NULL
                        OR CAST(:longitud AS double precision) IS NULL THEN NULL
                    ELSE ST_SetSRID(
                    ST_MakePoint(:longitud, :latitud), 4326
                    )::geography
                END
                """
            )

        if not asignaciones:
            return self.obtener(proveedor_id)

        try:
            fila = (
                self._session.execute(
                    text(
                        f"""
                        UPDATE inventario.proveedor
                        SET {", ".join(asignaciones)}
                        WHERE id = :id
                        RETURNING
                            id, nit, nombre, telefono, correo, direccion,
                            ST_Y(ubicacion::geometry) AS latitud,
                            ST_X(ubicacion::geometry) AS longitud,
                            activo
                        """  # noqa: S608
                    ),
                    parametros,
                )
                .mappings()
                .first()
            )
        except IntegrityError as error:
            self._session.rollback()
            if getattr(error.orig, "sqlstate", None) == "23505":
                raise ProveedorDuplicado() from error
            raise

        if fila is None:
            raise RecursoNoExiste("Proveedor no encontrado")

        return self._proveedor_desde_fila(fila)
