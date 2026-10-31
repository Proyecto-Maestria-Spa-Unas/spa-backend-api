# S1 · Identidad

**Responsable:** ivonnelizethmoreno-cloud · **Revisa:** equipo-backend · **Contrato:** `docs/openapi/identidad-v1.yaml`

Autenticación, emisión del JWT, usuarios, roles y permisos (HU-01, HU-09 · RF-01, RF-13 · RNF-07).

## Endpoints (9)

| Método | Ruta | Permiso | Entrega · responsable |
|---|---|---|---|
| POST | `/auth/login` | Público | Entrega 1 · B5 |
| POST | `/auth/recuperar` | Público · **Estefa44445 (X3)** | Entrega 2 |
| GET | `/auth/me` | Autenticado | Entrega 1 |
| GET | `/usuarios` | usuario.gestionar | Entrega 1 |
| POST | `/usuarios` | usuario.gestionar | Entrega 1 |
| GET | `/usuarios/{id}` | usuario.gestionar | Entrega 1 |
| PATCH | `/usuarios/{id}` | usuario.gestionar | Entrega 1 |
| PATCH | `/usuarios/{id}/estado` | usuario.gestionar | Entrega 1 |
| GET | `/roles` | usuario.gestionar | Entrega 1 |

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

Las fechas exactas están en cada issue (etiqueta `plan-entregas`).

* **B2:** revisar y completar los 4 contratos y obtener la aprobación de frontend.
* **B5:** `/auth/login` y `/auth/me` con Supabase Auth. **B6:** usuarios y roles.
* **X3 (Estefa44445):** `/auth/recuperar` con `resetPasswordForEmail` de Supabase Auth y su pantalla.

## Definición de terminado

Ver la plantilla de PR. En resumen: contrato sin cambios no aprobados, pruebas unitarias e integración, cobertura ≥ 80 %, casos de error con su `code`, import-linter en verde y URL Preview enlazada en el PR.
