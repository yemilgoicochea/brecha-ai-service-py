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

**Tecnología:** pytest + FastAPI TestClient + unittest.mock

Los servicios externos (Supabase, Pub/Sub) se mockean — los tests son unitarios/integración sobre la lógica de la API sin necesidad de conexiones reales.

| Archivo | Descripción |
|---------|-------------|
| `test_api.py` | Health check, categorías, validación Pydantic del título, autenticación del endpoint classify, errores de Supabase y Pub/Sub |
| `test_auth.py` | Registro (éxito, email duplicado, validaciones), login (éxito, usuario inexistente, contraseña incorrecta), endpoint `/me`, logout |
| `test_classify_async.py` | Flujo completo async: submit → `query_id`, polling de estado (pending/completed), clasificaciones en respuesta, historial, retry |
| `test_admin.py` | Sectores (listar, toggle activo/inactivo), indicadores de brecha (listar, filtros, crear, actualizar, borrado lógico), niveles de gobierno |

```bash
# Ejecutar todos los tests
pytest tests/ -v

# Con reporte de cobertura
pytest tests/ -v --cov=app --cov-report=term-missing
```
