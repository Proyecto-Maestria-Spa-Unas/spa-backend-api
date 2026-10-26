# S1 · Identidad

**Responsable:** ivonnelizethmoreno-cloud · **Revisa:** equipo-backend · **Contrato:** `docs/openapi/identidad-v1.yaml`

Autenticación, emisión del JWT, usuarios, roles y permisos (HU-01, HU-09 · RF-01, RF-13 · RNF-07).

## Endpoints (8)

| Método | Ruta | Permiso | Sprint |
|---|---|---|---|
| POST | `/auth/login` | Público | 2 |
| GET | `/auth/me` | Autenticado | 2 |
| GET | `/usuarios` | usuario.gestionar | 2 |
| POST | `/usuarios` | usuario.gestionar | 2 |
| GET | `/usuarios/{id}` | usuario.gestionar | 2 |
| PATCH | `/usuarios/{id}` | usuario.gestionar | 2 |
| PATCH | `/usuarios/{id}/estado` | usuario.gestionar | 2 |
| GET | `/roles` | usuario.gestionar | 2 |

## Dónde va cada cosa

| Archivo | Qué implementar |
|---|---|
| `domain/modelo.py` | Ya tiene `Usuario`, `Rol`, `CodigoRol`. Agregar reglas: usuario inactivo no inicia sesión |
| `application/puertos.py` | `ProveedorIdentidad` (Supabase Auth) y `UsuarioRepository` (esquema `seguridad`) |
| `application/*.py` | Casos de uso: `IniciarSesion`, `CrearUsuario`, `CambiarEstadoUsuario`... |
| `infrastructure/supabase_auth.py` | Login y alta de cuentas con httpx contra Supabase Auth. Único archivo que lee `SUPABASE_SECRET_KEY` |
| `infrastructure/repositorio_sqlalchemy.py` | `seguridad.perfil`, `rol`, `rol_permiso` |
| `api/router.py` | Reemplazar cada `raise NoImplementado()` por el caso de uso |

`POST /auth/login` debe terminar con `app.compartido.seguridad.emitir_token(usuario_id, rol, permisos)`.

## Tareas

* **Sprint 1 · B2:** revisar y completar el borrador de los 4 contratos en `docs/openapi/` (ejemplos, descripciones) y obtener la aprobación de equipo-frontend en el PR de contrato.
* **Sprint 2:** los 8 endpoints. Desde aquí todos los endpoints de la API exigen JWT real.

## Definición de terminado

Ver la plantilla de PR. En resumen: contrato sin cambios no aprobados, pruebas unitarias e integración, cobertura ≥ 80 %, casos de error con su `code`, import-linter en verde y URL Preview enlazada en el PR.
