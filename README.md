# Backend Spa de Uñas - FastAPI

Backend desarrollado con FastAPI para la gestión y control interno del inventario de un spa de uñas: autenticación, control de acceso por roles, productos, entradas y salidas, historial de movimientos y alertas de bajo stock. Este proyecto sigue una arquitectura hexagonal (puertos y adaptadores), modular y escalable, preparada para entornos de desarrollo y producción.

## 🚀 Tecnologías Principales

* FastAPI
* Uvicorn
* SQLAlchemy
* Pydantic Settings
* PyJWT (JWT, ADR-0004)
* Python-dotenv
* Psycopg (driver PostgreSQL)
* PostgreSQL + PostGIS (Supabase)

## ⚙️ Configuración del Entorno

### 1️⃣ Clonar el repositorio

```
git clone https://github.com/Proyecto-Maestria-Spa-Unas/spa-backend-api.git
cd spa-backend-api
git checkout develop
```

### 2️⃣ Crear entorno virtual (venv)

#### 🐧 Linux / Mac

```
python3 -m venv venv
source venv/bin/activate
```

#### 🪟 Windows (PowerShell)

```
python -m venv venv
venv\Scripts\Activate.ps1
```

Si da error de políticas:

```
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

#### 🪟 Windows (CMD)

```
python -m venv venv
venv\Scripts\activate.bat
```

### 3️⃣ Instalar dependencias

Con el entorno virtual activado:

#### 🐧 Linux / Mac

```
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

#### 🪟 Windows

```
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

✅ El comando es el mismo en ambos sistemas si el entorno está activado correctamente.

* `requirements.txt` → dependencias de ejecución (las que se instalan en producción).
* `requirements-dev.txt` → herramientas de desarrollo y calidad (pruebas, lint, tipos, auditoría).

Instalar otras dependencias:

```
pip install nombre_dependencia
```

Guardar cambios de dependencias en requirements.txt (solo las de ejecución, sin fijar herramientas de desarrollo):

```
pip freeze > requirements.txt
```

⚠️ Revise el diff de `requirements.txt` antes de hacer commit: `pip freeze` incluye todo lo instalado en el venv. Las herramientas de desarrollo van en `requirements-dev.txt`.

## ▶️ Ejecutar el Backend

Desde la raíz del proyecto:

```
python -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

Acceder a:

* 📄 Documentación Swagger: http://127.0.0.1:8000/api/v1/docs
* 📘 Contrato vivo: http://127.0.0.1:8000/api/v1/openapi.json
* 💚 Estado del servicio: http://127.0.0.1:8000/api/v1/health
* 🗄️ Conexión con la base: http://127.0.0.1:8000/api/v1/health/ready

Mientras un endpoint no esté implementado responde `501` con `code: NO_IMPLEMENTADO`. Todos exigen su permiso desde ya: sin token responden `401` y sin el permiso `403`.

## 📦 Dependencias Principales

### 🔹 FastAPI
Framework web moderno y rápido para construir APIs con Python.

### 🔹 Uvicorn
Servidor ASGI que ejecuta la aplicación FastAPI.

### 🔹 python-dotenv
Permite cargar variables de entorno desde un archivo `.env`.

### 🔹 pydantic-settings
Gestión estructurada y tipada de configuraciones usando Pydantic.

### 🔹 PyJWT
Emisión y verificación de JWT (HS256) para autenticación y autorización (ADR-0004).

### 🔹 SQLAlchemy
ORM que permite interactuar con bases de datos relacionales usando modelos en Python.

### 🔹 psycopg
Driver de PostgreSQL usado por SQLAlchemy para conectarse a Supabase.

### 🔹 Herramientas de desarrollo (requirements-dev.txt)
* **pytest / pytest-cov / httpx**: pruebas automatizadas y cobertura.
* **import-linter**: verifica que los 4 servicios no se importen entre sí y que se respeten las capas.
* **PyYAML**: exporta los contratos OpenAPI por servicio.
* **ruff**: linter y formateador de código.
* **mypy**: verificación estática de tipos.
* **pip-audit**: detección de dependencias con vulnerabilidades conocidas.

## 🔐 Variables de Entorno

El proyecto utiliza variables de entorno para configuración sensible.

Debes:

1. Crear un archivo `.env` en la raíz del proyecto.
2. Copiar el contenido de `.env.example`.
3. Ajustar los valores según tu entorno.

### 📌 Convención estándar

```
.env.example
```

Este archivo ya está en el repositorio con todas las variables y sus valores para desarrollo local:

```
cp .env.example .env
```

Luego creas tu archivo real:

```
.env
```

⚠️ El archivo `.env` no debe subirse al repositorio (ya está incluido en el `.gitignore`).

## 📁 Organización del proyecto y patrones

Monolito modular con **4 servicios de dominio** (ADR-0009). Cada servicio vive en su carpeta con sus 4 capas hexagonales y en el Sprint 4 se extrae a su propio microservicio en EKS sin cambiar rutas. Detalle en `docs/ARQUITECTURA.md`.

| Carpeta | Uso | Responsable |
|---|---|---|
| `app/compartido/` | Configuración, conexión a la base, seguridad (JWT y `requiere(permiso)`), errores problem+json, paginación, salud | Plataforma (cambios por PR revisado) |
| `app/modulos/identidad/` | **S1** · login, recuperación de contraseña, usuarios, roles · 9 endpoints | ivonnelizethmoreno-cloud (recuperación: Estefa44445) |
| `app/modulos/catalogo/` | **S2** · productos, categorías, unidades, stock mínimo, proveedores georreferenciados · 14 endpoints | Damx0611 (proveedores: Gleidy725) |
| `app/modulos/movimientos/` | **S3** · entradas, salidas, historial, anulación · 6 endpoints | Damx0611 (motivos: Gleidy725) |
| `app/modulos/analitica/` | **S4** · alertas, tablero, kardex valorizado, consumo, cobertura, mapa de proveedores, exportación · 8 endpoints | ivonnelizethmoreno-cloud (alertas, mapa y exportación: Estefa44445) |
| `docs/openapi/` | Contrato de cada servicio (se genera desde el código) | ivonnelizethmoreno-cloud; aprueba equipo-frontend |
| `tests/contrato/` | Seguridad y existencia de los 37 endpoints | Todos |
| `tests/unit/<servicio>/` | Dominio y casos de uso, sin base | Dueño del servicio |
| `tests/integration/<servicio>/` | Contra PostGIS (`docker compose up -d db`) | Dueño del servicio |
| `docker-compose.yml`, `docker/` | Entorno local: PostGIS con el esquema de `spa-database` + API | Plataforma |

Cada servicio tiene su propio `README.md` dentro de su carpeta con los endpoints, las tareas por sprint y lo que debe entregar.

⚠️ El esquema de base de datos es propiedad de **S0 · Datos** (`spa-database`). Este backend no crea ni modifica tablas.

## 🧪 Pruebas y calidad

Los mismos comandos que ejecuta la integración continua:

```
ruff check .
ruff format --check .
mypy .
pytest --cov --cov-fail-under=80
python scripts/exportar_contratos.py --check
```

Para corregir el formato automáticamente:

```
ruff format .
```

Las pruebas incluyen tres guardianes que no se deben desactivar:

* `tests/contrato/`: cada endpoint existe, exige su permiso y responde errores en problem+json.
* `tests/test_arquitectura.py`: ningún servicio importa a otro y el dominio no depende de frameworks.
* `tests/test_contratos.py`: `docs/openapi/*.yaml` coincide con el código. Si cambia un esquema o una ruta, regenere con `python scripts/exportar_contratos.py` y abra el cambio como **PR de contrato**, que aprueba equipo-frontend.

## 🐳 Docker

### Entorno local completo (recomendado)

Clone `spa-database` al lado de este repositorio (misma carpeta padre) **en la rama `develop`**: `main` solo tiene la migración base hasta la primera release. Luego ejecute:

```
cd ../spa-database && git switch develop && git pull && cd ../spa-backend-api
docker compose up -d --build
```

Estructura esperada:

```
Proyectos/
├── spa-backend-api/
└── spa-database/
```

* Base PostGIS en `localhost:54322` con **las mismas migraciones** que el pipeline aplica en Supabase.
* API en http://localhost:8000/api/v1/docs.

Solo la base (para ejecutar la API con `uvicorn --reload` desde el venv):

```
docker compose up -d db
python -m uvicorn main:app --reload
```

Cuando Mike publique migraciones nuevas, recree la base local:

```
docker compose down -v
docker compose up -d db
```

#### Verificar que el entorno quedó bien

```
docker compose ps
curl -s -o /dev/null -w "health/ready: %{http_code}\n" http://localhost:8000/api/v1/health/ready
docker compose logs db 2>&1 | grep -E "Migración|Seed|ERROR|Base local lista"
```

* `docker compose ps`: `spa-unas-api-1` y `spa-unas-db-1` en estado `healthy`.
* `health/ready: 200` (si responde `503`, la API no alcanza la base).
* El registro de `db` lista cada migración de `spa-database/supabase/migrations`, luego `Seed` y termina en `✓ Base local lista con el esquema de spa-database`, sin líneas `ERROR`.

#### Requisitos en Windows

* **Docker Desktop con WSL 2.** Windows 11 Home no tiene Hyper-V, así que el motor de Docker corre sobre WSL 2. Si `wsl` no se reconoce, instálelo desde PowerShell como administrador con `wsl --install --no-distribution` y reinicie el equipo.
* `docker version` debe mostrar las secciones **Client** y **Server**. Si solo muestra Client y un error `500 Internal Server Error ... dockerDesktopLinuxEngine`, cierre Docker Desktop (Quit), ejecute `wsl --shutdown` en PowerShell, abra Docker Desktop de nuevo y espere a "Engine running".
* Si comandos de Windows como `wsl` o `systeminfo` no se reconocen aunque existan en `C:\Windows\System32`, revise que esa carpeta esté en la variable `Path` del sistema.

#### Diferencia conocida con la migración base

La imagen `postgis/postgis` instala `postgis` (y `fuzzystrmatch`, `postgis_topology`, `postgis_tiger_geocoder`) en el esquema `public` antes de aplicar las migraciones. Por eso, en la base local `postgis` queda en `public`, aunque la migración base la pide en `extensions` (`CREATE EXTENSION IF NOT EXISTS ... WITH SCHEMA extensions` no la mueve si ya existe). `citext` y `pgcrypto` sí quedan en `extensions`. Verificado el 01-nov-2026 con:

```
docker compose exec db psql -U postgres -tAc "select extname || ' en ' || extnamespace::regnamespace from pg_extension order by 1"
```

Las migraciones que usen tipos o funciones de PostGIS (D12) deben funcionar en ambos casos; compare con el resultado de la misma consulta en staging antes de fusionarlas.

### Imagen sola

```
docker build -t spa-backend-api .
docker run --env-file .env -p 8000:8000 spa-backend-api
```

La imagen se ejecuta con un usuario sin privilegios, expone el puerto 8000 y trae `HEALTHCHECK` sobre `/api/v1/health`. Es la imagen que se ejecuta en Kubernetes en la Entrega 2 (DV5 y DV7).

## 🔀 Flujo de trabajo

1. Crear la rama desde `develop`: `git checkout -b feature/HU-07-registrar-salida`.
1. Implementar solo dentro de la carpeta de su servicio. Si necesita algo de `app/compartido/`, propóngalo en un PR aparte.
2. Hacer commits con Conventional Commits y firma: `git commit -s -m "feat(movimientos): registrar salida (HU-07)"`.
3. Abrir un Pull Request hacia `develop` y completar la plantilla (Definición de terminado). Vercel publica una URL Preview del PR para que frontend y QA la prueben.
4. El PR solo se puede fusionar cuando pasan los checks `politica / pr`, `calidad / pipeline`, `seguridad / scan` (y `qa-gate / qa` cuando QA esté activo) y lo aprueba un integrante del equipo responsable.
