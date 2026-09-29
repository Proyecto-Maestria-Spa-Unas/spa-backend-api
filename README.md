# Backend Spa de Uñas - FastAPI

![CI](https://github.com/Proyecto-Maestria-Spa-Unas/spa-backend-api/actions/workflows/ci.yml/badge.svg?branch=develop)

Backend desarrollado con FastAPI para la gestión y control interno del inventario de un spa de uñas: autenticación, control de acceso por roles, productos, entradas y salidas, historial de movimientos y alertas de bajo stock. Este proyecto sigue una arquitectura hexagonal (puertos y adaptadores), modular y escalable, preparada para entornos de desarrollo y producción.

## 🚀 Tecnologías Principales

* FastAPI
* Uvicorn
* SQLAlchemy
* Pydantic Settings
* PyJWT (JWT)
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

* 📄 Documentación Swagger: http://127.0.0.1:8000/docs
* 📘 Documentación Redoc: http://127.0.0.1:8000/redoc
* 💚 Estado del servicio: http://127.0.0.1:8000/api/v1/health

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
Implementación de JWT para autenticación y autorización.

### 🔹 SQLAlchemy
ORM que permite interactuar con bases de datos relacionales usando modelos en Python.

### 🔹 psycopg
Driver de PostgreSQL usado por SQLAlchemy para conectarse a Supabase.

### 🔹 Herramientas de desarrollo (requirements-dev.txt)
* **pytest / pytest-cov / httpx**: pruebas automatizadas y cobertura.
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

Este archivo contiene las variables necesarias sin datos sensibles, por ejemplo:

```
# Entorno
APP_ENV=development

# DB (Supabase: Project Settings → Database → Connection string)
DB_URL=postgresql+psycopg://user:password@localhost:5432/spa

# jwt
JWT_SECRET=your_secret_key
JWT_ALGORITHM=HS256
JWT_EXPIRES_MINUTES=30

# CORS
CORS_ORIGINS=["http://localhost:5173"]
```

Luego creas tu archivo real:

```
.env
```

⚠️ El archivo `.env` no debe subirse al repositorio (ya está incluido en el `.gitignore`).

## 📁 Organización del proyecto y patrones

El código se organiza por capas siguiendo arquitectura hexagonal. Detalle en `docs/ARQUITECTURA.md`.

| Carpeta | Uso |
|---|---|
| `app/domain` | Entidades y reglas de negocio puras (estados de inventario, validación de stock, RN-01 a RN-14). No depende de FastAPI ni de SQLAlchemy. |
| `app/application` | Casos de uso (registrar producto, registrar entrada/salida, descontinuar, consultar alertas). |
| `app/application/ports` | Interfaces que los casos de uso necesitan: repositorios, generador de tokens, hasher de contraseñas. |
| `app/infrastructure/db` | Adaptadores SQLAlchemy que implementan los puertos contra PostgreSQL/Supabase. |
| `app/infrastructure/security` | JWT (PyJWT), hashing de contraseñas y control de acceso por rol. |
| `app/api/v1` | Routers de FastAPI y esquemas Pydantic de entrada/salida. |
| `app/core` | Configuración (`config.py`), dependencias compartidas y logging. |
| `tests` | Pruebas unitarias y de integración. |
| `main.py` | Punto de entrada para `uvicorn main:app`. |

⚠️ El esquema de base de datos se administra en el repositorio `spa-database`. Este backend no crea ni modifica tablas.

## 🧪 Pruebas y calidad

Los mismos comandos que ejecuta la integración continua:

```
ruff check .
ruff format --check .
mypy app
pytest --cov=app --cov-fail-under=80
```

Para corregir el formato automáticamente:

```
ruff format .
```

## 🐳 Docker

```
docker build -t spa-backend-api .
docker run --env-file .env -p 8000:8000 spa-backend-api
```

La imagen se ejecuta con un usuario sin privilegios y expone el puerto 8000.

## 🔀 Flujo de trabajo

1. Crear la rama desde `develop`: `git checkout -b feature/HU-07-registrar-salida`.
2. Hacer commits con Conventional Commits y firma: `git commit -s -m "feat(movimientos): registrar salida (HU-07)"`.
3. Abrir un Pull Request hacia `develop`.
4. El PR solo se puede fusionar cuando pasan los checks `politica / pr`, `calidad / pipeline`, `seguridad / scan` (y `qa-gate / qa` cuando QA esté activo) y lo aprueba un integrante del equipo responsable.

## 🌿 Cómo contribuir

### 1️⃣ Clonar el repositorio (solo la primera vez)

Use **Git Bash** en Windows o la terminal en Linux/Mac:

```
git config --global core.autocrlf input
git clone https://github.com/Proyecto-Maestria-Spa-Unas/spa-backend-api.git
cd spa-backend-api
git switch develop
```

### 2️⃣ Crear la rama de su tarea

Nunca se trabaja directamente sobre `main` ni `develop`: GitHub rechaza esos push. Cada tarea tiene su rama, creada desde `develop` actualizada:

```
git switch develop
git pull
git switch -c feature/B1-docker-compose
```

Formato obligatorio: **`tipo/ID-descripcion-corta`**. El `ID` es el de la tarea del sprint en mayúscula (D1, B2, F3, Q1…) y la descripción va en minúsculas, con guiones y sin espacios ni tildes.

| Tipo | Úselo para |
|---|---|
| `feature/` | Funcionalidad nueva |
| `fix/` | Corrección de un defecto |
| `docs/` | Documentación |
| `test/` | Pruebas |
| `refactor/` | Mejora interna sin cambio funcional |
| `chore/` · `ci/` | Mantenimiento y automatización |

### 3️⃣ Guardar y subir los cambios

```
git add .
git commit -s -m "build(docker): entorno local con docker compose (B1)"
git push -u origin feature/B1-docker-compose
```

El mensaje sigue **Conventional Commits**: `tipo(alcance): descripción (ID)`. La opción `-s` firma el commit.

### 4️⃣ Abrir el Pull Request

```
gh pr create --base develop --fill
```

O desde GitHub con el botón **Compare & pull request**. En la descripción escriba `Closes Proyecto-Maestria-Spa-Unas/spa-backend-api#<número de la tarea>`. El PR se fusiona cuando los checks obligatorios están en verde.

### 5️⃣ Mantener su rama al día

Si `develop` avanzó mientras usted trabajaba:

```
git switch develop
git pull
git switch -
git rebase develop
git push --force-with-lease
```

`--force-with-lease` solo se usa sobre **su propia rama**, nunca sobre `main` ni `develop`.

### ❌ Qué no hacer

* No subir archivos `.env`, contraseñas ni llaves: el escaneo de seguridad bloqueará el PR.
* No mezclar varias tareas en una misma rama: una rama, una tarea, un PR.
