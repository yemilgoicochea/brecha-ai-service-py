# Brecha AI Service

API REST en FastAPI para clasificar proyectos públicos de Invierte.pe según indicadores de brecha del SNPMGI (Perú). La clasificación es **asíncrona**: el API publica en Pub/Sub y el worker `brecha-ai-worker` procesa con Vertex AI (Gemini).

## Arquitectura

```
Cliente
  │
  ▼
POST /api/v1/classify
  │  → guarda query en Supabase (status: pending)
  │  → publica mensaje en Pub/Sub
  │  ← retorna query_id (202 Accepted)
  │
  ▼
GET /api/v1/query/{query_id}   ← cliente hace polling
  │  ← retorna status + clasificaciones cuando completa
```

## Prerequisitos

- Python 3.11+
- Docker
- Google Cloud Project con Pub/Sub habilitado
- Proyecto Supabase con schema DDL aplicado

## Configuración local

```bash
# 1. Crear entorno virtual
python -m venv venv
.\venv\Scripts\activate        # Windows
source venv/bin/activate       # Linux/Mac

# 2. Instalar dependencias
pip install -r requirements.txt

# 3. Configurar variables de entorno
cp .env.example .env
# Editar .env con tus credenciales
```

## Variables de entorno

| Variable | Default | Descripción |
|---|---|---|
| `ENVIRONMENT` | `development` | Entorno |
| `PORT` | `8080` | Puerto del servidor |
| `LOG_LEVEL` | `INFO` | Nivel de logs |
| `ALLOWED_ORIGINS` | `*` | CORS origins permitidos |
| `GCP_PROJECT_ID` | — | ID del proyecto GCP (requerido) |
| `PUBSUB_TOPIC_ID` | `brecha-classification-topic` | Topic Pub/Sub |
| `SUPABASE_URL` | — | URL del proyecto Supabase (requerido) |
| `SUPABASE_KEY` | — | Service role key de Supabase (requerido) |
| `JWT_SECRET` | — | Clave para firmar tokens JWT (requerido) |
| `JWT_ALGORITHM` | `HS256` | Algoritmo JWT |
| `JWT_EXPIRATION_HOURS` | `24` | Expiración del token en horas |

> La clasificación con Gemini es responsabilidad de `brecha-ai-worker`. Este servicio no usa `GEMINI_API_KEY`.

## Ejecutar

```bash
# Local
uvicorn app.main:app --reload --host 0.0.0.0 --port 8080

# Docker
docker build -t brecha-ai-service-py:latest .
docker run -d --rm -p 8080:8080 --env-file .env brecha-ai-service-py:latest
```

Acceder a la documentación: http://localhost:8080/docs

## Endpoints

### Clasificación (async)

| Método | Ruta | Descripción |
|--------|------|-------------|
| `POST` | `/api/v1/classify` | Envía proyecto a clasificar → retorna `query_id` (202) |
| `GET` | `/api/v1/query/{query_id}` | Consulta estado y resultados |
| `POST` | `/api/v1/query/{query_id}/retry` | Reintenta clasificación (solo si no tiene resultados) |
| `GET` | `/api/v1/history` | Historial de consultas del usuario autenticado |
| `GET` | `/api/v1/categories` | Lista indicadores de brecha disponibles |

### Autenticación

| Método | Ruta | Descripción |
|--------|------|-------------|
| `POST` | `/api/v1/auth/login` | Iniciar sesión → retorna JWT |
| `POST` | `/api/v1/auth/register` | Registrar usuario |

### Admin

| Método | Ruta | Descripción |
|--------|------|-------------|
| `GET` | `/api/v1/admin/sectors` | Listar sectores |
| `GET` | `/api/v1/admin/gaps` | Listar indicadores de brecha |

### Health

| Método | Ruta | Descripción |
|--------|------|-------------|
| `GET` | `/health` | Health check |

**Ejemplo classify:**
```bash
curl -X POST http://localhost:8080/api/v1/classify \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"title": "Mejoramiento del servicio de agua potable en el distrito de San Juan"}'
```

```json
{
  "query_id": "7de618b4-b9d6-431c-b2e7-f95be099f948",
  "status": "pending",
  "message": "Classification queued. Use query_id to check status."
}
```

## Estructura del proyecto

```
brecha-ai-service-py/
├── app/
│   ├── main.py                      # FastAPI app
│   ├── api/
│   │   └── routers/
│   │       ├── classifier.py        # Endpoints de clasificación
│   │       ├── auth.py              # Endpoints de autenticación
│   │       ├── sectors.py           # Admin: sectores
│   │       └── gaps.py              # Admin: indicadores de brecha
│   ├── core/
│   │   ├── config.py                # Configuración (pydantic-settings)
│   │   ├── security.py              # JWT y autenticación
│   │   └── logging_config.py        # Setup de logs
│   ├── models/
│   │   └── schemas.py               # Modelos Pydantic
│   └── services/
│       ├── pubsub_service.py        # Publicar en Pub/Sub
│       ├── supabase_service.py      # Persistencia en Supabase
│       └── auth_service.py          # Lógica de autenticación
├── tests/
├── .github/
│   └── workflows/
│       ├── tests.yml                # CI
│       └── build-and-deploy.yml     # CD a Cloud Run
├── Dockerfile
├── requirements.txt
├── .env.example
└── README.md
```

## Despliegue (Cloud Run)

El deploy se realiza automáticamente via GitHub Actions al hacer push a `main` o `dev`.

Secrets configurados en GCP Secret Manager: `SUPABASE_URL`, `SUPABASE_KEY`, `JWT_SECRET`.
Credenciales GCP en GitHub Actions secret: `GCP_SA_KEY`.

Ver [dev-documentation.md](../dev-documentation.md) para roles IAM requeridos.

## Tests

Este proyecto tiene **dos tipos de pruebas independientes**, cada una con su propio reporte HTML:

| Tipo | Herramienta | Propósito | Reporte HTML |
|------|-------------|-----------|--------------|
| Cobertura de código | pytest + pytest-cov | Qué líneas se ejecutaron durante los tests | `htmlcov/index.html` |
| Rendimiento / carga | Locust | Latencia, RPS, errores bajo usuarios concurrentes | `reports/*.html` |

---

## 1. Tests de cobertura (pytest)

**Tecnología:** pytest + FastAPI TestClient + unittest.mock

Los servicios externos (Supabase, Pub/Sub) se mockean — los tests son unitarios/integración sobre la lógica de la API sin necesidad de conexiones reales.

| Archivo | Descripción |
|---------|-------------|
| `test_api.py` | Health check, categorías, validación Pydantic del título, autenticación del endpoint classify, errores de Supabase y Pub/Sub |
| `test_auth.py` | Registro (éxito, email duplicado, validaciones), login (éxito, usuario inexistente, contraseña incorrecta), endpoint `/me`, logout |
| `test_classify_async.py` | Flujo completo async: submit → `query_id`, polling de estado (pending/completed), clasificaciones en respuesta, historial, retry |
| `test_admin.py` | Sectores (listar, toggle activo/inactivo), indicadores de brecha (listar, filtros, crear, actualizar, borrado lógico), niveles de gobierno |

### Cobertura alcanzada (referencia)

| Módulo | Cobertura |
|--------|-----------|
| `core/security.py` | 100% |
| `core/config.py` | 100% |
| `routers/auth.py` | 92% |
| `routers/classifier.py` | 72% |
| `routers/gaps.py` | 72% |
| `routers/sectors.py` | 65% |
| **Total** | **~70%** |

### Comandos

```bash
# 1. Activar entorno virtual
.\venv\Scripts\activate        # Windows
source venv/bin/activate       # Linux/Mac

# 2. Ejecutar todos los tests
pytest tests/ -v

# 3. Reporte de cobertura en terminal
pytest tests/ -v --cov=app --cov-report=term-missing

# 4. Reporte HTML interactivo → htmlcov/index.html
pytest tests/ --cov=app --cov-report=html
start htmlcov\index.html       # Windows — abre en el navegador
open htmlcov/index.html        # Linux/Mac
```

> El reporte HTML muestra qué líneas exactas no están cubiertas (rojo = no ejecutado, verde = ejecutado), archivo por archivo. No mide rendimiento.

---

## 2. Tests de rendimiento (Locust)

**Tecnología:** [Locust](https://locust.io/) — simula usuarios concurrentes reales contra el servicio levantado.

Mide: tiempo de respuesta (p50/p95/p99), RPS, tasa de errores, comportamiento bajo carga.

**Requisito previo:** el servicio debe estar corriendo y debe existir un usuario de prueba en la base de datos. Editar `TEST_USER_EMAIL` y `TEST_USER_PASSWORD` en `locustfile.py` antes de ejecutar.

El flujo simulado por cada usuario virtual:
1. Login → obtiene JWT
2. `POST /api/v1/classify` → recibe 202 + `query_id`
3. Polling `GET /api/v1/query/{query_id}` hasta `completed`
4. Ocasionalmente: consulta historial, health check, validación con título vacío

### Comandos

```bash
# Instalar Locust (solo una vez)
pip install locust

# UI interactiva — abre http://localhost:8089 en el navegador
# (permite configurar usuarios y duración desde la interfaz)
locust

# Headless — validación rápida (2 usuarios, 3 min) → reports/validacion.html
locust --headless --users 2 --spawn-rate 1 --run-time 3m --html=reports/validacion.html

# Headless — carga baja (5 usuarios, 5 min) → reports/carga_baja.html
locust --headless --users 5 --spawn-rate 1 --run-time 5m --html=reports/carga_baja.html

# Headless — carga media (10 usuarios, 5 min) → reports/carga_media.html
locust --headless --users 10 --spawn-rate 2 --run-time 5m --html=reports/carga_media.html
```

> Los reportes HTML de Locust se guardan en `reports/`. La carpeta ya está en `.gitignore`.
